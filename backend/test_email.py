"""
Tes pengiriman email laporan harian sekarang juga (tidak perlu tunggu jam 00:00).
Jalankan dari folder backend:
    python test_email.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(__file__))

from app import create_app, mail
from services.scheduler import kirim_laporan_harian

app = create_app()

print("Mengirim email laporan harian SEKARANG sebagai uji coba...")
kirim_laporan_harian(app, mail)
print("Selesai! Cek inbox / spam di pradikamaula01@gmail.com")
