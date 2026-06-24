"""
Smart Wash Laundry — Entry Point
=================================
Jalankan aplikasi dengan perintah:
    python run.py

Atau dengan Flask CLI:
    set FLASK_APP=run.py
    flask run --port=5000
"""

import sys
import os

# Tambahkan folder backend ke sys.path agar semua import Python bisa ditemukan
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from app import create_app

app = create_app()

if __name__ == '__main__':
    app.run(debug=True, port=5000)
