import os
import pymysql
pymysql.install_as_MySQLdb()

from flask import Flask, redirect, url_for, session, render_template, flash
from flask_mysqldb import MySQL
from functools import wraps
from config import Config

mysql = MySQL()

# Absolute path ke root proyek (satu level di atas folder backend/)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def login_required(f):
    """Decorator: semua role harus login."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id_pengguna' not in session:
            flash('Silakan login terlebih dahulu.', 'error')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def owner_required(f):
    """Decorator: khusus role owner."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'id_pengguna' not in session:
            flash('Silakan login terlebih dahulu.', 'error')
            return redirect(url_for('auth.login'))
        if session.get('role') != 'owner':
            flash('Akses ditolak. Halaman ini khusus Pemilik Toko.', 'error')
            return redirect(url_for('transaksi.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def create_app():
    app = Flask(
        __name__,
        template_folder=os.path.join(BASE_DIR, 'frontend', 'templates'),
        static_folder=os.path.join(BASE_DIR, 'frontend', 'static'),
    )
    app.config.from_object(Config)

    # Init ekstensi
    mysql.init_app(app)

    # Register blueprints
    from routes.auth import auth_bp
    from routes.transaksi import transaksi_bp
    from routes.laporan import laporan_bp
    from routes.owner_layanan import owner_layanan_bp
    from routes.owner_karyawan import owner_karyawan_bp
    from routes.owner_promo import owner_promo_bp
    from routes.pelanggan import pelanggan_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(transaksi_bp)
    app.register_blueprint(laporan_bp)
    app.register_blueprint(owner_layanan_bp)
    app.register_blueprint(owner_karyawan_bp)
    app.register_blueprint(owner_promo_bp)
    app.register_blueprint(pelanggan_bp)

    # Default route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        return render_template('base.html', page_title='404 - Tidak Ditemukan'), 404

    @app.errorhandler(500)
    def server_error(e):
        return render_template('base.html', page_title='500 - Kesalahan Server'), 500

    # Endpoint untuk Vercel Cron Jobs
    @app.route('/api/cron_laporan', methods=['GET', 'POST'])
    def vercel_cron_laporan():
        # Endpoint ini akan di-hit otomatis oleh Vercel sesuai jadwal di vercel.json
        # Atau bisa dikunjungi manual untuk testing
        from services.scheduler import kirim_laporan_harian
        kirim_laporan_harian(app)
        return {"status": "success", "message": "Laporan harian berhasil dikirim."}, 200

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(debug=True, port=5000)
