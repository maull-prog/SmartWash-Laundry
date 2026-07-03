from flask import Blueprint, render_template, request, redirect, url_for, session, flash, jsonify, make_response
from app import mysql, login_required
from datetime import datetime, timedelta
from services.whatsapp import kirim_notifikasi_siap

transaksi_bp = Blueprint('transaksi', __name__)


@transaksi_bp.route('/dashboard')
@login_required
def dashboard():
    cur = mysql.connection.cursor()

    # Hitung status cucian hari ini
    cur.execute("""
        SELECT status_cucian, COUNT(*) as total 
        FROM transaksi 
        WHERE status_cucian != 'selesai'
        GROUP BY status_cucian
    """)
    status_rows = cur.fetchall()
    status_counts = {'antrian': 0, 'sedang_dicuci': 0, 'siap_diambil': 0}
    for row in status_rows:
        status_counts[row['status_cucian']] = row['total']

    # Cucian aktif (belum selesai)
    cur.execute("""
        SELECT t.id_transaksi, t.kode_transaksi, t.status_cucian, t.berat_kg,
               p.nama AS nama_pelanggan,
               GROUP_CONCAT(l.nama_layanan SEPARATOR ', ') AS layanan_list
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        LEFT JOIN detail_transaksi dt ON t.id_transaksi = dt.id_transaksi
        LEFT JOIN layanan l ON dt.id_layanan = l.id_layanan
        WHERE t.status_cucian != 'selesai'
        GROUP BY t.id_transaksi, t.kode_transaksi, t.status_cucian, t.berat_kg, p.nama, t.tgl_masuk
        ORDER BY t.tgl_masuk DESC
    """)
    cucian_aktif = cur.fetchall()
    cur.close()

    return render_template('dashboard.html',
                           page_title='Dashboard',
                           status_counts=status_counts,
                           cucian_aktif=cucian_aktif)


@transaksi_bp.route('/transaksi/baru')
@login_required
def transaksi_baru():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM layanan WHERE aktif = 1 ORDER BY kategori, id_layanan")
    layanan_list = cur.fetchall()

    cur.execute("SELECT * FROM promo WHERE aktif = 1 ORDER BY nominal_potongan DESC")
    promo_list = cur.fetchall()
    cur.close()

    return render_template('transaksi_baru.html',
                           page_title='Transaksi Baru',
                           layanan_list=layanan_list,
                           promo_list=promo_list)


@transaksi_bp.route('/transaksi/cek_pelanggan')
@login_required
def cek_pelanggan():
    """AJAX: cek apakah pelanggan sudah terdaftar dan VIP."""
    nama = request.args.get('nama', '').strip()
    no_hp = request.args.get('no_hp', '').strip()
    if not nama:
        return jsonify({'found': False})

    cur = mysql.connection.cursor()
    if no_hp:
        cur.execute("SELECT * FROM pelanggan WHERE nama = %s AND no_hp = %s", (nama, no_hp))
    else:
        cur.execute("SELECT * FROM pelanggan WHERE nama = %s", (nama,))
    pelanggan = cur.fetchone()
    cur.close()

    if pelanggan:
        return jsonify({
            'found': True,
            'id_pelanggan': pelanggan['id_pelanggan'],
            'level_member': pelanggan['level_member'],
            'total_transaksi': pelanggan['total_transaksi'],
            'poin_loyalitas': pelanggan['poin_loyalitas']
        })
    return jsonify({'found': False})


@transaksi_bp.route('/transaksi/cari_pelanggan')
@login_required
def cari_pelanggan():
    """AJAX autocomplete: cari pelanggan berdasarkan awalan nama."""
    q = request.args.get('q', '').strip()

    cur = mysql.connection.cursor()
    if len(q) < 1:
        # Jika kosong, tampilkan 8 pelanggan terbanyak transaksinya (sering laundry)
        cur.execute("""
            SELECT id_pelanggan, nama, no_hp, alamat, poin_loyalitas, level_member, total_transaksi
            FROM pelanggan
            ORDER BY total_transaksi DESC, nama ASC
            LIMIT 8
        """)
    else:
        cur.execute("""
            SELECT id_pelanggan, nama, no_hp, alamat, poin_loyalitas, level_member, total_transaksi
            FROM pelanggan
            WHERE LOWER(nama) LIKE LOWER(%s)
            ORDER BY total_transaksi DESC, nama ASC
            LIMIT 8
        """, (f'{q}%',))
    results = cur.fetchall()
    cur.close()

    return jsonify([{
        'id_pelanggan': r['id_pelanggan'],
        'nama': r['nama'],
        'no_hp': r['no_hp'] or '',
        'alamat': r['alamat'] or '',
        'poin_loyalitas': int(r['poin_loyalitas'] or 0),
        'level_member': (r['level_member'] or 'reguler').lower(),
        'total_transaksi': int(r['total_transaksi'] or 0),
    } for r in results])


@transaksi_bp.route('/transaksi/simpan', methods=['POST'])
@login_required
def simpan_transaksi():
    nama_pelanggan = request.form.get('nama_pelanggan', '').strip()
    no_hp = request.form.get('no_hp', '').strip()
    alamat = request.form.get('alamat', '').strip()
    berat_kg = request.form.get('berat_kg', '0')
    layanan_ids = request.form.getlist('layanan_ids[]')
    keterangan = request.form.get('keterangan', '').strip()
    status_bayar = request.form.get('status_bayar', 'belum').strip()
    id_promo_input = request.form.get('id_promo', '').strip()
    tukar_poin_input = request.form.get('tukar_poin', '0')

    try:
        tukar_poin = int(tukar_poin_input)
    except ValueError:
        tukar_poin = 0

    # Validasi server-side
    if not nama_pelanggan:
        flash('Nama pelanggan wajib diisi.', 'error')
        return redirect(url_for('transaksi.transaksi_baru'))

    try:
        berat_kg = float(berat_kg)
    except ValueError:
        berat_kg = 0

    if berat_kg <= 0:
        flash('Berat pakaian harus lebih dari 0 kg.', 'error')
        return redirect(url_for('transaksi.transaksi_baru'))

    if not layanan_ids:
        flash('Minimal pilih 1 layanan.', 'error')
        return redirect(url_for('transaksi.transaksi_baru'))

    cur = mysql.connection.cursor()

    try:
        # 1. Cari atau buat pelanggan
        if no_hp:
            cur.execute("SELECT id_pelanggan, level_member, poin_loyalitas FROM pelanggan WHERE nama = %s AND no_hp = %s", (nama_pelanggan, no_hp))
        else:
            cur.execute("SELECT id_pelanggan, level_member, poin_loyalitas FROM pelanggan WHERE nama = %s", (nama_pelanggan,))
        pelanggan = cur.fetchone()

        if pelanggan:
            id_pelanggan = pelanggan['id_pelanggan']
            level_member = pelanggan['level_member']
            poin_sekarang = pelanggan['poin_loyalitas']
        else:
            cur.execute("INSERT INTO pelanggan (nama, no_hp, alamat, poin_loyalitas) VALUES (%s, %s, %s, 0)",
                        (nama_pelanggan, no_hp, alamat))
            mysql.connection.commit()
            id_pelanggan = cur.lastrowid
            level_member = 'reguler'
            poin_sekarang = 0

        # 2. Generate kode transaksi: TRX-MMDD + 2 digit urut
        now = datetime.now()
        prefix = now.strftime("TRX-%m%d")
        cur.execute("""
            SELECT COUNT(*) as cnt FROM transaksi 
            WHERE kode_transaksi LIKE %s AND DATE(tgl_masuk) = CURDATE()
        """, (prefix + '%',))
        cnt = cur.fetchone()['cnt']
        kode_transaksi = f"{prefix}{cnt + 1:02d}"

        # 3. Ambil data layanan yang dipilih & hitung subtotal
        total_harga = 0
        detail_list = []
        estimasi_max = 0

        for lid in layanan_ids:
            cur.execute("SELECT * FROM layanan WHERE id_layanan = %s AND aktif = 1", (lid,))
            lay = cur.fetchone()
            if not lay:
                continue

            if lay['kategori'] == 'Layanan':
                harga = float(lay['harga_per_kg'])
                subtotal = harga * berat_kg
                detail_berat = berat_kg
            else:
                harga = float(lay['harga_satuan'])
                subtotal = harga * 1
                detail_berat = 0

            total_harga += subtotal
            if lay['estimasi_hari'] and lay['estimasi_hari'] > estimasi_max:
                estimasi_max = lay['estimasi_hari']

            detail_list.append({
                'id_layanan': lay['id_layanan'],
                'berat_kg': detail_berat,
                'qty': 1,
                'harga_saat_transaksi': harga,
                'subtotal': subtotal
            })

        # 4. Cek promo manual
        diskon_promo = 0
        id_promo = None
        if id_promo_input:
            cur.execute("SELECT * FROM promo WHERE aktif = 1 AND id_promo = %s", (id_promo_input,))
            promo = cur.fetchone()
            if promo and berat_kg >= float(promo['syarat_min_kg']):
                diskon_promo = float(promo['nominal_potongan'])
                id_promo = promo['id_promo']
            elif promo:
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({'success': False, 'message': f'Berat kurang dari syarat minimum promo {promo["nama_promo"]}'}), 400
                flash(f'Berat kurang dari syarat minimum promo {promo["nama_promo"]}', 'error')
                return redirect(url_for('transaksi.transaksi_baru'))

        # 5. Tukar Poin (1 Poin = Rp 1000)
        diskon_poin = 0
        if tukar_poin > 0:
            if tukar_poin > poin_sekarang:
                if request.headers.get('Accept') == 'application/json':
                    return jsonify({'success': False, 'message': 'Poin tidak cukup!'}), 400
                flash('Poin tidak cukup!', 'error')
                return redirect(url_for('transaksi.transaksi_baru'))
            diskon_poin = tukar_poin * 1000

        # 6. Diskon VIP 10%
        diskon_vip = 0
        if level_member and level_member.lower() == 'vip':
            diskon_vip = total_harga * 0.10
        
        diskon = diskon_promo + diskon_poin + diskon_vip
        total_bayar = max(total_harga - diskon, 0)
        
        # 6b. Poin didapat (1 Poin per Rp 10.000)
        poin_didapat = 0
        if level_member and level_member.lower() == 'vip':
            poin_didapat = int(total_bayar // 10000)

        tgl_estimasi = (now + timedelta(days=estimasi_max)).date() if estimasi_max > 0 else (now + timedelta(days=2)).date()

        # 6. INSERT transaksi
        cur.execute("""
            INSERT INTO transaksi 
            (kode_transaksi, id_pelanggan, id_kasir, id_promo, tgl_masuk, tgl_estimasi_selesai,
             berat_kg, total_harga, diskon, status_bayar, status_cucian, keterangan)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 'antrian', %s)
        """, (kode_transaksi, id_pelanggan, session['id_pengguna'], id_promo,
              now, tgl_estimasi, berat_kg, total_bayar, diskon, status_bayar, keterangan))
        id_transaksi = cur.lastrowid

        # 7. INSERT detail transaksi
        for d in detail_list:
            cur.execute("""
                INSERT INTO detail_transaksi 
                (id_transaksi, id_layanan, berat_kg, qty, harga_saat_transaksi, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_transaksi, d['id_layanan'], d['berat_kg'], d['qty'],
                  d['harga_saat_transaksi'], d['subtotal']))

        # 8. Update total_transaksi & Poin pelanggan
        cur.execute("""
            UPDATE pelanggan 
            SET total_transaksi = total_transaksi + 1,
                poin_loyalitas = poin_loyalitas - %s + %s
            WHERE id_pelanggan = %s
        """, (tukar_poin, poin_didapat, id_pelanggan))

        mysql.connection.commit()
        
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': True, 'id_transaksi': id_transaksi, 'message': f'Transaksi {kode_transaksi} berhasil disimpan!'})
            
        flash(f'Transaksi {kode_transaksi} berhasil disimpan!', 'success')
        return redirect(url_for('transaksi.dashboard'))

    except Exception as e:
        mysql.connection.rollback()
        if request.headers.get('Accept') == 'application/json':
            return jsonify({'success': False, 'message': str(e)}), 400
            
        flash(f'Gagal menyimpan transaksi: {str(e)}', 'error')
        return redirect(url_for('transaksi.transaksi_baru'))
    finally:
        cur.close()


@transaksi_bp.route('/transaksi/update_status/<int:id>', methods=['POST'])
@login_required
def update_status(id):
    """AJAX: Update status cucian ke tahap berikutnya."""
    status_order = ['antrian', 'sedang_dicuci', 'siap_diambil', 'selesai']

    cur = mysql.connection.cursor()
    cur.execute("SELECT status_cucian FROM transaksi WHERE id_transaksi = %s", (id,))
    trx = cur.fetchone()

    if not trx:
        return jsonify({'success': False, 'message': 'Transaksi tidak ditemukan'}), 404

    current = trx['status_cucian']
    idx = status_order.index(current)

    if idx >= len(status_order) - 1:
        return jsonify({'success': False, 'message': 'Status sudah selesai'}), 400

    new_status = status_order[idx + 1]

    # Jika status menjadi selesai, otomatis set status_bayar = lunas
    if new_status == 'selesai':
        cur.execute("UPDATE transaksi SET status_cucian = %s, status_bayar = 'lunas' WHERE id_transaksi = %s",
                    (new_status, id))
    else:
        cur.execute("UPDATE transaksi SET status_cucian = %s WHERE id_transaksi = %s",
                    (new_status, id))

    # Jika status menjadi siap_diambil, kirim notifikasi WA
    if new_status == 'siap_diambil':
        cur.execute("""
            SELECT t.kode_transaksi, t.total_harga, p.nama, p.no_hp 
            FROM transaksi t
            JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
            WHERE t.id_transaksi = %s
        """, (id,))
        trx_info = cur.fetchone()
        if trx_info and trx_info['no_hp']:
            kirim_notifikasi_siap(trx_info['no_hp'], trx_info['nama'], trx_info['kode_transaksi'], trx_info['total_harga'])

    mysql.connection.commit()
    cur.close()

    return jsonify({'success': True, 'new_status': new_status})


@transaksi_bp.route('/transaksi/riwayat')
@login_required
def riwayat_transaksi():
    q = request.args.get('q', '').strip()
    cur = mysql.connection.cursor()

    if q:
        search = f'%{q}%'
        cur.execute("""
            SELECT t.*, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan
            FROM transaksi t
            LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
            WHERE (t.kode_transaksi LIKE %s OR p.nama LIKE %s)
            ORDER BY t.tgl_masuk DESC
        """, (search, search))
    else:
        cur.execute("""
            SELECT t.*, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan
            FROM transaksi t
            LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
            ORDER BY t.tgl_masuk DESC
            LIMIT 100
        """)

    transaksi_list = cur.fetchall()
    cur.close()

    return render_template('riwayat_transaksi.html',
                           page_title='Riwayat Transaksi',
                           transaksi_list=transaksi_list,
                           q=q)


@transaksi_bp.route('/transaksi/search')
@login_required
def search_transaksi():
    """AJAX search endpoint."""
    q = request.args.get('q', '').strip()
    cur = mysql.connection.cursor()

    if q:
        search = f'%{q}%'
        cur.execute("""
            SELECT t.id_transaksi, t.kode_transaksi, t.tgl_masuk, t.status_cucian,
                   t.total_harga, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan
            FROM transaksi t
            LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
            WHERE (t.kode_transaksi LIKE %s OR p.nama LIKE %s)
            ORDER BY t.tgl_masuk DESC
            LIMIT 50
        """, (search, search))
    else:
        cur.execute("""
            SELECT t.id_transaksi, t.kode_transaksi, t.tgl_masuk, t.status_cucian,
                   t.total_harga, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan
            FROM transaksi t
            LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
            ORDER BY t.tgl_masuk DESC
            LIMIT 50
        """)

    rows = cur.fetchall()
    cur.close()

    result = []
    for r in rows:
        result.append({
            'id_transaksi': r['id_transaksi'],
            'kode_transaksi': r['kode_transaksi'],
            'tgl_masuk': r['tgl_masuk'].strftime('%d %B %Y') if r['tgl_masuk'] else '',
            'nama_pelanggan': r['nama_pelanggan'] or '-',
            'no_hp_pelanggan': r['no_hp_pelanggan'] or '-',
            'status_cucian': r['status_cucian'],
            'total_harga': float(r['total_harga']) if r['total_harga'] else 0
        })

    return jsonify(result)


@transaksi_bp.route('/transaksi/detail/<int:id>')
@login_required
def detail_transaksi(id):
    """AJAX: detail transaksi untuk modal."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT t.*, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan, p.alamat,
               pg.nama_lengkap AS nama_kasir, pr.nama_promo
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        LEFT JOIN pengguna pg ON t.id_kasir = pg.id_pengguna
        LEFT JOIN promo pr ON t.id_promo = pr.id_promo
        WHERE t.id_transaksi = %s
    """, (id,))
    trx = cur.fetchone()

    if not trx:
        return jsonify({'error': 'Transaksi tidak ditemukan'}), 404

    cur.execute("""
        SELECT dt.*, l.nama_layanan, l.kategori
        FROM detail_transaksi dt
        LEFT JOIN layanan l ON dt.id_layanan = l.id_layanan
        WHERE dt.id_transaksi = %s
    """, (id,))
    details = cur.fetchall()
    cur.close()

    detail_items = []
    for d in details:
        detail_items.append({
            'nama_layanan': d['nama_layanan'],
            'kategori': d['kategori'],
            'berat_kg': float(d['berat_kg']) if d['berat_kg'] else 0,
            'qty': d['qty'],
            'harga_saat_transaksi': float(d['harga_saat_transaksi']),
            'subtotal': float(d['subtotal'])
        })

    return jsonify({
        'kode_transaksi': trx['kode_transaksi'],
        'tgl_masuk': trx['tgl_masuk'].strftime('%d %B %Y, %H:%M') if trx['tgl_masuk'] else '',
        'tgl_estimasi_selesai': trx['tgl_estimasi_selesai'].strftime('%d %B %Y') if trx['tgl_estimasi_selesai'] else '-',
        'nama_pelanggan': trx['nama_pelanggan'] or '-',
        'no_hp_pelanggan': trx['no_hp_pelanggan'] or '-',
        'alamat': trx['alamat'] or '-',
        'nama_kasir': trx['nama_kasir'] or '-',
        'nama_promo': trx['nama_promo'] or '-',
        'berat_kg': float(trx['berat_kg']) if trx['berat_kg'] else 0,
        'total_harga': float(trx['total_harga']) if trx['total_harga'] else 0,
        'diskon': float(trx['diskon']) if trx['diskon'] else 0,
        'status_bayar': trx['status_bayar'],
        'status_cucian': trx['status_cucian'],
        'keterangan': trx['keterangan'] or '-',
        'details': detail_items
    })


@transaksi_bp.route('/transaksi/invoice/<int:id>')
@login_required
def invoice_transaksi(id):
    """Mendapatkan data invoice untuk dicetak."""
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT t.*, p.nama AS nama_pelanggan, p.no_hp AS no_hp_pelanggan,
               pg.nama_lengkap AS nama_kasir
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        LEFT JOIN pengguna pg ON t.id_kasir = pg.id_pengguna
        WHERE t.id_transaksi = %s
    """, (id,))
    trx = cur.fetchone()

    if not trx:
        return jsonify({'error': 'Transaksi tidak ditemukan'}), 404

    cur.execute("""
        SELECT dt.*, l.nama_layanan, l.kategori
        FROM detail_transaksi dt
        LEFT JOIN layanan l ON dt.id_layanan = l.id_layanan
        WHERE dt.id_transaksi = %s
    """, (id,))
    details = cur.fetchall()
    cur.close()

    detail_items = []
    for d in details:
        detail_items.append({
            'nama_layanan': d['nama_layanan'],
            'kategori': d['kategori'],
            'berat_kg': float(d['berat_kg']) if d['berat_kg'] else 0,
            'qty': d['qty'],
            'harga_saat_transaksi': float(d['harga_saat_transaksi']),
            'subtotal': float(d['subtotal'])
        })

    return jsonify({
        'kode_transaksi': trx['kode_transaksi'],
        'tgl_masuk': trx['tgl_masuk'].strftime('%d/%m/%Y'),
        'nama_pelanggan': trx['nama_pelanggan'] or '-',
        'nama_kasir': trx['nama_kasir'] or '-',
        'subtotal': float(trx['total_harga']) + float(trx['diskon'] or 0),
        'diskon': float(trx['diskon']) if trx['diskon'] else 0,
        'total_harga': float(trx['total_harga']),
        'status_bayar': trx['status_bayar'],
        'details': detail_items
    })


@transaksi_bp.route('/transaksi/struk/<int:id>')
@login_required
def cetak_struk(id):
    import io
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import mm

    cur = mysql.connection.cursor()
    
    # Ambil data transaksi
    cur.execute("""
        SELECT t.*, p.nama AS nama_pelanggan, p.no_hp
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        WHERE t.id_transaksi = %s
    """, (id,))
    trx = cur.fetchone()

    if not trx:
        cur.close()
        return "Transaksi tidak ditemukan", 404

    # Ambil detail layanan
    cur.execute("""
        SELECT dt.*, l.nama_layanan
        FROM detail_transaksi dt
        JOIN layanan l ON dt.id_layanan = l.id_layanan
        WHERE dt.id_transaksi = %s
    """, (id,))
    details = cur.fetchall()
    cur.close()

    # Setup ukuran kertas thermal (80mm width, panjang dinamis)
    panjang_kertas = 100 + (len(details) * 15) + 60
    
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=(80*mm, panjang_kertas*mm))
    
    # Koordinat awal (dari bawah)
    y = panjang_kertas * mm - 15*mm
    x_center = 40 * mm
    x_left = 5 * mm
    x_right = 75 * mm
    
    c.setFont("Helvetica-Bold", 14)
    c.drawCentredString(x_center, y, "SMART WASH LAUNDRY")
    y -= 6*mm
    c.setFont("Helvetica", 9)
    c.drawCentredString(x_center, y, "Jalan, Blotongan No.3, Salatiga")
    y -= 10*mm
    
    c.setDash(2, 2)
    c.line(x_left, y, x_right, y)
    c.setDash()
    y -= 8*mm
    
    c.setFont("Helvetica", 9)
    c.drawString(x_left, y, f"Nota: {trx['kode_transaksi']}")
    y -= 5*mm
    c.drawString(x_left, y, f"Tgl: {trx['tgl_masuk'].strftime('%d %b %Y %H:%M')}")
    y -= 5*mm
    c.drawString(x_left, y, f"Plg: {trx['nama_pelanggan'] or '-'}")
    y -= 8*mm
    
    c.setDash(2, 2)
    c.line(x_left, y, x_right, y)
    c.setDash()
    y -= 8*mm
    
    # Detail Transaksi
    c.setFont("Helvetica-Bold", 9)
    for dt in details:
        c.drawString(x_left, y, dt['nama_layanan'][:20])
        y -= 5*mm
        c.setFont("Helvetica", 9)
        qty_str = f"{dt['berat_kg']}Kg" if dt['berat_kg'] > 0 else f"{dt['qty']}x"
        c.drawString(x_left + 5*mm, y, f"{qty_str} @ {int(dt['harga_saat_transaksi'])}")
        c.drawRightString(x_right, y, f"{int(dt['subtotal'])}")
        y -= 6*mm
        c.setFont("Helvetica-Bold", 9)
        
    y -= 2*mm
    c.setDash(2, 2)
    c.line(x_left, y, x_right, y)
    c.setDash()
    y -= 8*mm
    
    # Total
    c.setFont("Helvetica", 9)
    c.drawString(x_left, y, "Diskon:")
    c.drawRightString(x_right, y, f"- {int(trx['diskon'])}")
    y -= 6*mm
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(x_left, y, "TOTAL:")
    c.drawRightString(x_right, y, f"Rp {int(trx['total_harga'])}")
    y -= 6*mm
    
    c.setFont("Helvetica", 9)
    c.drawString(x_left, y, "Status:")
    c.drawRightString(x_right, y, "Lunas" if trx['status_bayar'] == 'lunas' else "Belum Lunas")
    y -= 10*mm
    
    c.setDash(2, 2)
    c.line(x_left, y, x_right, y)
    c.setDash()
    y -= 8*mm
    
    c.setFont("Helvetica", 8)
    c.drawCentredString(x_center, y, "Terima Kasih")
    y -= 4*mm
    c.drawCentredString(x_center, y, "Cucian bersih, wangi, dan rapi!")
    
    c.save()
    buffer.seek(0)
    
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'inline; filename=struk_{trx["kode_transaksi"]}.pdf'
    return response
