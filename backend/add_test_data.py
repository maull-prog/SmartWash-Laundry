import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

import pymysql
from config import Config
from datetime import date, datetime

def main():
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
    
    # 1. Tambah Pelanggan VIP
    nama_vip = "Bapak Sultan VIP"
    no_hp_vip = "089999999999"
    cur.execute("INSERT INTO pelanggan (nama, no_hp, alamat, level_member, poin_loyalitas, total_transaksi, tgl_daftar) VALUES (%s, %s, %s, 'VIP', 5000, 0, %s)",
                (nama_vip, no_hp_vip, "Jl. Sultan Agung No. 1", date.today()))
    id_vip = cur.lastrowid
    
    # 2. Tambah Pelanggan Reguler
    nama_reguler = "Mas Joko Reguler"
    no_hp_reguler = "087777777777"
    cur.execute("INSERT INTO pelanggan (nama, no_hp, alamat, level_member, poin_loyalitas, total_transaksi, tgl_daftar) VALUES (%s, %s, %s, 'reguler', 0, 0, %s)",
                (nama_reguler, no_hp_reguler, "Jl. Biasa Saja No. 2", date.today()))
    id_reguler = cur.lastrowid
    
    # 3. Ambil id_kasir
    cur.execute("SELECT id_pengguna FROM pengguna WHERE role = 'kasir' LIMIT 1")
    kasir = cur.fetchone()
    if not kasir:
        print("Tidak ada kasir!")
        return
    id_kasir = kasir['id_pengguna']
    
    # 4. Buat transaksi untuk VIP
    now = datetime.now()
    kode_trx_vip = f"TRX-{now.strftime('%m%d')}88"
    cur.execute("""
        INSERT INTO transaksi 
        (kode_transaksi, id_pelanggan, id_kasir, tgl_masuk, tgl_estimasi_selesai, berat_kg, total_harga, diskon, status_bayar, status_cucian)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'belum', 'antrian')
    """, (kode_trx_vip, id_vip, id_kasir, now, now, 5.0, 45000, 4500))
    id_trx_vip = cur.lastrowid
    
    # 5. Buat transaksi untuk Reguler
    kode_trx_reguler = f"TRX-{now.strftime('%m%d')}89"
    cur.execute("""
        INSERT INTO transaksi 
        (kode_transaksi, id_pelanggan, id_kasir, tgl_masuk, tgl_estimasi_selesai, berat_kg, total_harga, diskon, status_bayar, status_cucian)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'belum', 'antrian')
    """, (kode_trx_reguler, id_reguler, id_kasir, now, now, 3.0, 30000, 0))
    id_trx_reguler = cur.lastrowid
    
    # Update count transaksi
    cur.execute("UPDATE pelanggan SET total_transaksi = 1 WHERE id_pelanggan IN (%s, %s)", (id_vip, id_reguler))
    
    conn.commit()
    conn.close()
    print("Berhasil menambahkan pelanggan VIP (Bapak Sultan VIP), Reguler (Mas Joko Reguler) dan transaksi mereka!")

if __name__ == '__main__':
    main()
