"""
Layanan Scheduler: Pengiriman Laporan Harian Otomatis via Email
Berjalan setiap hari pada jam yang dikonfigurasi di config.py
"""
import pymysql
import pymysql.cursors
from datetime import date, datetime
from flask import render_template
import resend
from config import Config


def ambil_data_laporan(app):
    """Mengambil data laporan hari ini dari TiDB."""
    with app.app_context():
        try:
            conn = pymysql.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                port=Config.MYSQL_PORT,
                ssl={"ssl_mode": "VERIFY_IDENTITY"},
                cursorclass=pymysql.cursors.DictCursor
            )
            cur = conn.cursor()
            hari_ini = date.today()

            # Total omzet hari ini (hanya yang lunas)
            cur.execute("""
                SELECT COALESCE(SUM(total_harga), 0) AS omzet
                FROM transaksi
                WHERE DATE(tgl_masuk) = %s AND status_bayar = 'lunas'
            """, (hari_ini,))
            omzet = float(cur.fetchone()['omzet'])

            # Total transaksi
            cur.execute("SELECT COUNT(*) AS total FROM transaksi WHERE DATE(tgl_masuk) = %s", (hari_ini,))
            total_trx = cur.fetchone()['total']

            cur.execute("SELECT COUNT(*) AS total FROM transaksi WHERE DATE(tgl_masuk) = %s AND status_bayar = 'lunas'", (hari_ini,))
            lunas = cur.fetchone()['total']

            cur.execute("SELECT COUNT(*) AS total FROM transaksi WHERE DATE(tgl_masuk) = %s AND status_bayar = 'belum'", (hari_ini,))
            belum = cur.fetchone()['total']

            # Layanan terlaris hari ini
            cur.execute("""
                SELECT l.nama_layanan, COUNT(dt.id_layanan) AS jumlah,
                       COALESCE(SUM(dt.subtotal), 0) AS total_omzet
                FROM detail_transaksi dt
                JOIN transaksi t ON dt.id_transaksi = t.id_transaksi
                JOIN layanan l ON dt.id_layanan = l.id_layanan
                WHERE DATE(t.tgl_masuk) = %s
                GROUP BY l.id_layanan, l.nama_layanan
                ORDER BY jumlah DESC
                LIMIT 5
            """, (hari_ini,))
            layanan_terlaris = cur.fetchall()

            # Daftar transaksi hari ini
            cur.execute("""
                SELECT t.kode_transaksi, t.total_harga, t.status_bayar,
                       p.nama AS nama_pelanggan,
                       GROUP_CONCAT(l.nama_layanan SEPARATOR ', ') AS layanan_list
                FROM transaksi t
                LEFT JOIN pelanggan p ON t.id_pelanggan = p.id_pelanggan
                LEFT JOIN detail_transaksi dt ON t.id_transaksi = dt.id_transaksi
                LEFT JOIN layanan l ON dt.id_layanan = l.id_layanan
                WHERE DATE(t.tgl_masuk) = %s
                GROUP BY t.id_transaksi, t.kode_transaksi, t.total_harga, t.status_bayar, p.nama
                ORDER BY t.tgl_masuk ASC
            """, (hari_ini,))
            transaksi_list = cur.fetchall()

            # Ambil nama owner
            cur.execute("SELECT nama_lengkap FROM pengguna WHERE role = 'owner' LIMIT 1")
            owner_row = cur.fetchone()
            nama_owner = owner_row['nama_lengkap'] if owner_row else 'Pemilik Toko'

            conn.close()
            return {
                'omzet_hari_ini': omzet,
                'total_transaksi': total_trx,
                'sudah_lunas': lunas,
                'belum_lunas': belum,
                'layanan_terlaris': layanan_terlaris,
                'transaksi_list': transaksi_list,
                'nama_owner': nama_owner,
                'tanggal': hari_ini.strftime('%A, %d %B %Y')
            }
        except Exception as e:
            print(f"[SCHEDULER] Gagal mengambil data laporan: {e}")
            return None


def kirim_laporan_harian(app):
    """Fungsi utama: render template email dan kirim ke MAIL_RECEIVER menggunakan Resend."""
    with app.app_context():
        receiver = getattr(Config, 'MAIL_RECEIVER', '').strip()
        resend_key = getattr(Config, 'RESEND_API_KEY', '').strip()
        sender = getattr(Config, 'MAIL_DEFAULT_SENDER', ('Smart Wash', 'onboarding@resend.dev'))

        if not receiver or not resend_key:
            print("[SCHEDULER] Resend API Key / Email Penerima belum dikonfigurasi. Laporan tidak dikirim.")
            return

        resend.api_key = resend_key
        print(f"[SCHEDULER] Menyiapkan laporan harian untuk {receiver}...")
        
        data = ambil_data_laporan(app)
        if data is None:
            print("[SCHEDULER] Data laporan gagal diambil. Email tidak dikirim.")
            return

        try:
            html_body = render_template('email_laporan.html', **data)
            
            params = {
                "from": f"{sender[0]} <{sender[1]}>",
                "to": [receiver],
                "subject": f"[Smart Wash] Laporan Harian - {data['tanggal']}",
                "html": html_body,
            }
            
            email_response = resend.Emails.send(params)
            print(f"[SCHEDULER] Laporan harian berhasil dikirim ke {receiver} (Resend ID: {email_response.get('id', 'unknown')})")
        except Exception as e:
            print(f"[SCHEDULER] Gagal mengirim email via Resend: {e}")
