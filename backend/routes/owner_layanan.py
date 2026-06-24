from flask import Blueprint, render_template, request, redirect, url_for, flash
from app import mysql, owner_required

owner_layanan_bp = Blueprint('owner_layanan', __name__)


@owner_layanan_bp.route('/owner/dashboard')
@owner_required
def dashboard_owner():
    cur = mysql.connection.cursor()

    # Total Pendapatan Bulan Ini
    cur.execute("""
        SELECT COALESCE(SUM(total_harga), 0) AS omzet 
        FROM transaksi 
        WHERE status_bayar = 'lunas' 
          AND MONTH(tgl_masuk) = MONTH(CURDATE()) 
          AND YEAR(tgl_masuk) = YEAR(CURDATE())
    """)
    omzet_bulan_ini = cur.fetchone()['omzet']

    # Jumlah Transaksi
    cur.execute("SELECT COUNT(*) AS total FROM transaksi")
    jumlah_transaksi = cur.fetchone()['total']

    # Cucian Selesai
    cur.execute("SELECT COUNT(*) AS total FROM transaksi WHERE status_cucian = 'selesai'")
    cucian_selesai = cur.fetchone()['total']

    # Grafik Pendapatan 7 Hari Terakhir
    cur.execute("""
        SELECT DATE(tgl_masuk) AS tanggal, COALESCE(SUM(total_harga), 0) AS omzet
        FROM transaksi 
        WHERE DATE(tgl_masuk) >= DATE_SUB(CURDATE(), INTERVAL 6 DAY)
          AND status_bayar = 'lunas'
        GROUP BY DATE(tgl_masuk)
        ORDER BY tanggal
    """)
    chart_rows = cur.fetchall()

    from datetime import date, timedelta
    days_map = {0: 'Senin', 1: 'Selasa', 2: 'Rabu', 3: 'Kamis', 4: 'Jumat', 5: 'Sabtu', 6: 'Minggu'}
    chart_labels = []
    chart_data = []

    for i in range(6, -1, -1):
        d = date.today() - timedelta(days=i)
        day_name = days_map[d.weekday()]
        chart_labels.append(day_name)
        
        omzet = 0
        for r in chart_rows:
            if r['tanggal'] == d:
                omzet = float(r['omzet'])
                break
        chart_data.append(omzet)

    # Transaksi Terbaru (5 data terakhir)
    cur.execute("""
        SELECT t.id_transaksi, t.kode_transaksi, t.status_cucian, t.total_harga,
               p.nama AS nama_pelanggan,
               GROUP_CONCAT(l.nama_layanan SEPARATOR ', ') AS layanan_list
        FROM transaksi t
        LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
        LEFT JOIN detail_transaksi dt ON t.id_transaksi = dt.id_transaksi
        LEFT JOIN layanan l ON dt.id_layanan = l.id_layanan
        GROUP BY t.id_transaksi
        ORDER BY t.tgl_masuk DESC
        LIMIT 5
    """)
    transaksi_terbaru = cur.fetchall()

    cur.close()

    return render_template('owner/dashboard_owner.html',
                           page_title='Dashboard',
                           omzet_bulan_ini=omzet_bulan_ini,
                           jumlah_transaksi=jumlah_transaksi,
                           cucian_selesai=cucian_selesai,
                           chart_labels=chart_labels,
                           chart_data=chart_data,
                           transaksi_terbaru=transaksi_terbaru)


@owner_layanan_bp.route('/owner/layanan')
@owner_required
def layanan_list():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM layanan ORDER BY id_layanan")
    layanan = cur.fetchall()
    cur.close()
    return render_template('owner/layanan.html',
                           page_title='Kelola Layanan',
                           layanan=layanan)


@owner_layanan_bp.route('/owner/layanan/tambah', methods=['GET', 'POST'])
@owner_required
def layanan_tambah():
    if request.method == 'POST':
        nama = request.form.get('nama_layanan', '').strip()
        kategori = request.form.get('kategori', 'Layanan')
        harga_per_kg = request.form.get('harga_per_kg', '0')
        harga_satuan = request.form.get('harga_satuan', '0')
        estimasi_hari = request.form.get('estimasi_hari', '2')
        deskripsi = request.form.get('deskripsi', '').strip()
        aktif = 1 if request.form.get('aktif') else 0

        if not nama:
            flash('Nama layanan wajib diisi.', 'error')
            return render_template('owner/layanan_form.html', page_title='Tambah Layanan', mode='tambah')

        try:
            harga_per_kg = float(harga_per_kg) if harga_per_kg else 0
            harga_satuan = float(harga_satuan) if harga_satuan else 0
            estimasi_hari = int(estimasi_hari) if estimasi_hari else 2
        except ValueError:
            flash('Format harga tidak valid.', 'error')
            return render_template('owner/layanan_form.html', page_title='Tambah Layanan', mode='tambah')

        cur = mysql.connection.cursor()
        cur.execute("""
            INSERT INTO layanan (nama_layanan, kategori, harga_per_kg, harga_satuan, estimasi_hari, deskripsi, aktif)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (nama, kategori, harga_per_kg, harga_satuan, estimasi_hari, deskripsi, aktif))
        mysql.connection.commit()
        cur.close()

        flash('Layanan berhasil ditambahkan!', 'success')
        return redirect(url_for('owner_layanan.layanan_list'))

    return render_template('owner/layanan_form.html', page_title='Tambah Layanan', mode='tambah')


@owner_layanan_bp.route('/owner/layanan/edit/<int:id>', methods=['GET', 'POST'])
@owner_required
def layanan_edit(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form.get('nama_layanan', '').strip()
        kategori = request.form.get('kategori', 'Layanan')
        harga_per_kg = request.form.get('harga_per_kg', '0')
        harga_satuan = request.form.get('harga_satuan', '0')
        estimasi_hari = request.form.get('estimasi_hari', '2')
        deskripsi = request.form.get('deskripsi', '').strip()
        aktif = 1 if request.form.get('aktif') else 0

        if not nama:
            flash('Nama layanan wajib diisi.', 'error')
            cur.execute("SELECT * FROM layanan WHERE id_layanan = %s", (id,))
            layanan = cur.fetchone()
            cur.close()
            return render_template('owner/layanan_form.html', page_title='Edit Layanan', mode='edit', layanan=layanan)

        try:
            harga_per_kg = float(harga_per_kg) if harga_per_kg else 0
            harga_satuan = float(harga_satuan) if harga_satuan else 0
            estimasi_hari = int(estimasi_hari) if estimasi_hari else 2
        except ValueError:
            flash('Format harga tidak valid.', 'error')
            return redirect(url_for('owner_layanan.layanan_edit', id=id))

        cur.execute("""
            UPDATE layanan 
            SET nama_layanan=%s, kategori=%s, harga_per_kg=%s, harga_satuan=%s, 
                estimasi_hari=%s, deskripsi=%s, aktif=%s
            WHERE id_layanan=%s
        """, (nama, kategori, harga_per_kg, harga_satuan, estimasi_hari, deskripsi, aktif, id))
        mysql.connection.commit()
        cur.close()

        flash('Layanan berhasil diperbarui!', 'success')
        return redirect(url_for('owner_layanan.layanan_list'))

    cur.execute("SELECT * FROM layanan WHERE id_layanan = %s", (id,))
    layanan = cur.fetchone()
    cur.close()

    if not layanan:
        flash('Layanan tidak ditemukan.', 'error')
        return redirect(url_for('owner_layanan.layanan_list'))

    return render_template('owner/layanan_form.html', page_title='Edit Layanan', mode='edit', layanan=layanan)


@owner_layanan_bp.route('/owner/layanan/hapus/<int:id>', methods=['POST'])
@owner_required
def layanan_hapus(id):
    cur = mysql.connection.cursor()

    # Cek apakah layanan dipakai di detail_transaksi
    cur.execute("SELECT COUNT(*) AS cnt FROM detail_transaksi WHERE id_layanan = %s", (id,))
    count = cur.fetchone()['cnt']

    if count > 0:
        flash('Layanan tidak dapat dihapus karena masih digunakan di transaksi. Nonaktifkan saja.', 'error')
    else:
        cur.execute("DELETE FROM layanan WHERE id_layanan = %s", (id,))
        mysql.connection.commit()
        flash('Layanan berhasil dihapus.', 'success')

    cur.close()
    return redirect(url_for('owner_layanan.layanan_list'))
