from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import bcrypt
from app import mysql

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    # Jika sudah login, redirect ke dashboard sesuai role
    if 'id_pengguna' in session:
        if session.get('role') == 'owner':
            return redirect(url_for('owner_layanan.dashboard_owner'))
        return redirect(url_for('transaksi.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()

        if not username or not password:
            flash('Username dan password wajib diisi.', 'error')
            return render_template('login.html')

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM pengguna WHERE username = %s", (username,))
        user = cur.fetchone()
        cur.close()

        if user is None:
            flash('Username atau password salah.', 'error')
            return render_template('login.html')

        # Cek password bcrypt
        if not bcrypt.checkpw(password.encode('utf-8'), user['password'].encode('utf-8')):
            flash('Username atau password salah.', 'error')
            return render_template('login.html')

        # Cek status aktif
        if not user['aktif']:
            flash('Akun tidak aktif. Hubungi pemilik toko.', 'error')
            return render_template('login.html')

        # Set session
        session['id_pengguna'] = user['id_pengguna']
        session['username'] = user['username']
        session['nama'] = user['nama_lengkap']
        session['role'] = user['role']

        if user['role'] == 'owner':
            return redirect(url_for('owner_layanan.dashboard_owner'))
        else:
            return redirect(url_for('transaksi.dashboard'))

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash('Anda telah berhasil logout.', 'success')
    return redirect(url_for('auth.login'))
