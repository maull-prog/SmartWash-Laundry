import sys
import os

# Tambahkan path root dan backend agar imports Python berjalan mulus di Vercel
current_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, current_dir)
sys.path.insert(0, os.path.join(current_dir, 'backend'))

from backend.app import create_app

app = create_app()

# Vercel Serverless Function akan mencari variabel 'app'
