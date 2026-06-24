from flask import Blueprint, render_template, request, redirect, url_for, flash
import bcrypt
import secrets
import string
from app import mysql, owner_required

owner_karyawan_bp = Blueprint('owner_karyawan', __name__)


@owner_karyawan_bp.route('/owner/karyawan')
@owner_required
def karyawan_list():
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM pengguna WHERE role = 'kasir' ORDER BY id_pengguna")
    karyawan = cur.fetchall()
    cur.close()
    return render_template('owner/karyawan.html',
                           page_title='Kelola Karyawan',
                           karyawan=karyawan)


@owner_karyawan_bp.route('/owner/karyawan/tambah', methods=['GET', 'POST'])
@owner_required
def karyawan_tambah():
    if request.method == 'POST':
        nama = request.form.get('nama_lengkap', '').strip()
        username = request.form.get('username', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        password = request.form.get('password', '').strip()
        aktif = 1 if request.form.get('aktif') else 0

        if not nama or not username or not password:
            flash('Nama, username, dan password wajib diisi.', 'error')
            return render_template('owner/karyawan_form.html', page_title='Tambah Karyawan', mode='tambah')

        # Cek username unik
        cur = mysql.connection.cursor()
        cur.execute("SELECT id_pengguna FROM pengguna WHERE username = %s", (username,))
        if cur.fetchone():
            flash('Username sudah digunakan. Pilih username lain.', 'error')
            cur.close()
            return render_template('owner/karyawan_form.html', page_title='Tambah Karyawan', mode='tambah')

        # Hash password
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        cur.execute("""
            INSERT INTO pengguna (username, password, nama_lengkap, no_hp, role, aktif)
            VALUES (%s, %s, %s, %s, 'kasir', %s)
        """, (username, hashed, nama, no_hp, aktif))
        mysql.connection.commit()
        cur.close()

        flash('Karyawan berhasil ditambahkan!', 'success')
        return redirect(url_for('owner_karyawan.karyawan_list'))

    return render_template('owner/karyawan_form.html', page_title='Tambah Karyawan', mode='tambah')


@owner_karyawan_bp.route('/owner/karyawan/edit/<int:id>', methods=['GET', 'POST'])
@owner_required
def karyawan_edit(id):
    cur = mysql.connection.cursor()

    if request.method == 'POST':
        nama = request.form.get('nama_lengkap', '').strip()
        username = request.form.get('username', '').strip()
        no_hp = request.form.get('no_hp', '').strip()
        password = request.form.get('password', '').strip()
        aktif = 1 if request.form.get('aktif') else 0

        if not nama or not username:
            flash('Nama dan username wajib diisi.', 'error')
            cur.execute("SELECT * FROM pengguna WHERE id_pengguna = %s", (id,))
            karyawan = cur.fetchone()
            cur.close()
            return render_template('owner/karyawan_form.html', page_title='Edit Karyawan', mode='edit', karyawan=karyawan)

        # Cek username unik (kecuali diri sendiri)
        cur.execute("SELECT id_pengguna FROM pengguna WHERE username = %s AND id_pengguna != %s", (username, id))
        if cur.fetchone():
            flash('Username sudah digunakan. Pilih username lain.', 'error')
            cur.close()
            return redirect(url_for('owner_karyawan.karyawan_edit', id=id))

        if password:
            hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            cur.execute("""
                UPDATE pengguna SET nama_lengkap=%s, username=%s, no_hp=%s, password=%s, aktif=%s
                WHERE id_pengguna=%s
            """, (nama, username, no_hp, hashed, aktif, id))
        else:
            cur.execute("""
                UPDATE pengguna SET nama_lengkap=%s, username=%s, no_hp=%s, aktif=%s
                WHERE id_pengguna=%s
            """, (nama, username, no_hp, aktif, id))

        mysql.connection.commit()
        cur.close()

        flash('Data karyawan berhasil diperbarui!', 'success')
        return redirect(url_for('owner_karyawan.karyawan_list'))

    cur.execute("SELECT * FROM pengguna WHERE id_pengguna = %s AND role = 'kasir'", (id,))
    karyawan = cur.fetchone()
    cur.close()

    if not karyawan:
        flash('Karyawan tidak ditemukan.', 'error')
        return redirect(url_for('owner_karyawan.karyawan_list'))

    return render_template('owner/karyawan_form.html', page_title='Edit Karyawan', mode='edit', karyawan=karyawan)


@owner_karyawan_bp.route('/owner/karyawan/reset_password/<int:id>', methods=['POST'])
@owner_required
def karyawan_reset_password(id):
    # Generate password acak 8 karakter
    chars = string.ascii_letters + string.digits
    new_password = ''.join(secrets.choice(chars) for _ in range(8))

    hashed = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    cur = mysql.connection.cursor()
    cur.execute("UPDATE pengguna SET password = %s WHERE id_pengguna = %s AND role = 'kasir'", (hashed, id))
    mysql.connection.commit()
    cur.close()

    flash(f'Password berhasil direset. Password baru: {new_password} (catat sekarang, tidak akan ditampilkan lagi!)', 'success')
    return redirect(url_for('owner_karyawan.karyawan_list'))


@owner_karyawan_bp.route('/owner/karyawan/hapus/<int:id>', methods=['POST'])
@owner_required
def karyawan_hapus(id):
    cur = mysql.connection.cursor()

    # Cek apakah karyawan punya transaksi
    cur.execute("SELECT COUNT(*) AS cnt FROM transaksi WHERE id_kasir = %s", (id,))
    count = cur.fetchone()['cnt']

    if count > 0:
        flash('Karyawan tidak dapat dihapus karena memiliki riwayat transaksi. Nonaktifkan saja.', 'error')
    else:
        cur.execute("DELETE FROM pengguna WHERE id_pengguna = %s AND role = 'kasir'", (id,))
        mysql.connection.commit()
        flash('Karyawan berhasil dihapus.', 'success')

    cur.close()
    return redirect(url_for('owner_karyawan.karyawan_list'))


@owner_karyawan_bp.route('/owner/karyawan/toggle_aktif/<int:id>', methods=['POST'])
@owner_required
def karyawan_toggle_aktif(id):
    cur = mysql.connection.cursor()
    cur.execute("SELECT aktif FROM pengguna WHERE id_pengguna = %s AND role = 'kasir'", (id,))
    karyawan = cur.fetchone()

    if not karyawan:
        flash('Karyawan tidak ditemukan.', 'error')
    else:
        new_status = 0 if karyawan['aktif'] else 1
        cur.execute("UPDATE pengguna SET aktif = %s WHERE id_pengguna = %s", (new_status, id))
        mysql.connection.commit()
        status_text = 'diaktifkan' if new_status else 'dinonaktifkan'
        flash(f'Karyawan berhasil {status_text}.', 'success')

    cur.close()
    return redirect(url_for('owner_karyawan.karyawan_list'))
