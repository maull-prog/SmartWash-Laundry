import os

class Config:
    SECRET_KEY = 'smartwash_secret_key_2026'
    MYSQL_HOST = 'gateway01.ap-southeast-1.prod.aws.tidbcloud.com'
    MYSQL_USER = '3AYSt1W5NovUdNQ.root'
    MYSQL_PASSWORD = 'o0awB1xhqMhMS8oK'
    MYSQL_DB = 'test'
    MYSQL_PORT = 4000
    MYSQL_CURSORCLASS = 'DictCursor'
    
    # SSL untuk TiDB menggunakan PyMySQL
    MYSQL_EXTRA_ARGS = {'ssl': {'ssl_mode': 'VERIFY_IDENTITY'}}
    
    # API WhatsApp Fonnte (kosongkan saat development)
    FONNTE_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJmb250bmUiLCJpYXQiOjE3NTM1NTE3MzAsImV4cCI6MjA2OTEyNzczMCwiYXVkIjoib25lIiwiZGF0YSI6eyJzZWxsZXJfaWQiOiI5NDM5OTExODUzIn19.W9y9gKj6w7z4h_c7R82rNn9n5w_5jBfC9R3p7z1q-z8'

    # ── Konfigurasi Email (Laporan Harian Otomatis Menggunakan Resend) ──
    # Isi dengan API Key dari akun Resend Anda
    RESEND_API_KEY = os.getenv('RESEND_API_KEY', '') # ← MASUKKAN API KEY RESEND DI SINI atau via Vercel Env
    MAIL_DEFAULT_SENDER = ('Smart Wash Laundry', 'onboarding@resend.dev')

    # Penerima laporan harian
    MAIL_RECEIVER = 'pradikamaula01@gmail.com'

    # Jam pengiriman laporan otomatis (WIB)
    # 0 = Tengah Malam (00:00 / jam 12 malam) → laporan hari yang baru berakhir
    LAPORAN_JAM   = 0
    LAPORAN_MENIT = 0
