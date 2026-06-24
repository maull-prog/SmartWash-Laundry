import requests
from config import Config

def kirim_notifikasi_siap(no_hp, nama_pelanggan, kode_transaksi):
    """
    Mengirim notifikasi WhatsApp via Fonnte API bahwa cucian sudah siap diambil.
    Jika FONNTE_TOKEN tidak diset di config, fungsi ini akan di-skip.
    """
    token = getattr(Config, 'FONNTE_TOKEN', '').strip()
    
    if not token:
        # Jika token belum diisi, skip proses tanpa error (safe default)
        print("[WARNING] [WA] Fonnte Token kosong. Notifikasi WA ke {} di-skip.".format(no_hp))
        return False
        
    if not no_hp:
        print("[WARNING] [WA] Nomor HP pelanggan kosong. Notifikasi WA di-skip.")
        return False
        
    # Pastikan nomor HP diawali dengan kode negara (default 62 untuk Indonesia)
    # Jika diawali 0, ganti dengan 62
    no_hp = str(no_hp).strip()
    if no_hp.startswith('0'):
        no_hp = '62' + no_hp[1:]
        
    pesan = (
        f"Halo *{nama_pelanggan}*,\n\n"
        f"Cucian Anda dengan nomor nota *{kode_transaksi}* sudah selesai dan siap untuk diambil! 🧺✨\n\n"
        f"Terima kasih telah mempercayakan pakaian Anda kepada *Smart Wash Laundry*.\n\n"
        f"--- \n"
        f"Pesan ini dikirim otomatis oleh sistem."
    )
    
    url = "https://api.fonnte.com/send"
    headers = {
        'Authorization': token
    }
    data = {
        'target': no_hp,
        'message': pesan,
        'typing': False,
        'delay': '2'
    }
    
    try:
        response = requests.post(url, headers=headers, data=data)
        result = response.json()
        if result.get('status'):
            print(f"[SUCCESS] [WA] Sukses kirim ke {no_hp}: {kode_transaksi}")
            return True
        else:
            print(f"[ERROR] [WA] Gagal kirim ke {no_hp}: {result.get('reason')}")
            return False
    except Exception as e:
        print(f"[ERROR] [WA] Error request API: {e}")
        return False
