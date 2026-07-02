import pymysql
from config import Config
from datetime import date, datetime, timedelta
import random

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

print("Menyiapkan data seed transaksi...")

# 1. Bersihkan data lama (kecuali data master)
cur.execute("DELETE FROM detail_transaksi")
cur.execute("DELETE FROM transaksi")
cur.execute("DELETE FROM pelanggan")
conn.commit()
print("Tabel transaksi dan pelanggan sudah dibersihkan.")

# 2. Seed Pelanggan
pelanggan_data = [
    ('Budi Santoso', '081234567890', 'Jl. Merdeka No. 1', 'VIP'),
    ('Siti Rahayu', '082345678901', 'Jl. Sudirman No. 5', 'reguler'),
    ('Ahmad Fauzi', '083456789012', 'Jl. Diponegoro No. 10', 'reguler'),
    ('Linda Wati', '084567890123', 'Jl. Gatot Subroto No. 15', 'VIP'),
    ('Deni Kusuma', '085678901234', 'Jl. Ahmad Yani No. 20', 'reguler'),
    ('Ratna Sari', '086789012345', 'Jl. Imam Bonjol No. 25', 'reguler'),
    ('Hendra Gunawan', '087890123456', 'Jl. Veteran No. 30', 'reguler'),
    ('Yuni Astuti', '088901234567', 'Jl. Pahlawan No. 35', 'VIP'),
]

for p in pelanggan_data:
    cur.execute("""
        INSERT INTO pelanggan (nama, no_hp, alamat, level_member, poin_loyalitas, total_transaksi, tgl_daftar)
        VALUES (%s, %s, %s, %s, 0, 0, %s)
    """, (p[0], p[1], p[2], p[3], date.today()))

conn.commit()
print(f"Berhasil menambahkan {len(pelanggan_data)} pelanggan.")

# Ambil ID pelanggan
cur.execute("SELECT id_pelanggan, nama FROM pelanggan")
pelanggan_list = cur.fetchall()

# Ambil ID kasir
cur.execute("SELECT id_pengguna FROM pengguna WHERE role = 'kasir'")
kasir_list = cur.fetchall()
kasir_ids = [k['id_pengguna'] for k in kasir_list]

# Ambil ID layanan
cur.execute("SELECT id_layanan, nama_layanan, harga_per_kg, harga_satuan, kategori FROM layanan WHERE aktif = 1")
layanan_list = cur.fetchall()

layanan_utama = [l for l in layanan_list if l['kategori'] == 'Layanan']
addon_list    = [l for l in layanan_list if l['kategori'] == 'Add-on']

# 3. Buat transaksi 7 hari terakhir
today = date.today()
transaksi_count = 0

skenario_harian = [
    # (hari_lalu, jumlah_transaksi_hari_itu)
    (6, 4), (5, 5), (4, 3), (3, 6), (2, 5), (1, 4), (0, 3)
]

for (hari_lalu, jumlah) in skenario_harian:
    tgl = today - timedelta(days=hari_lalu)
    
    for i in range(jumlah):
        transaksi_count += 1
        kode = f"TRX-{tgl.strftime('%y%m%d')}{i+1:02d}"
        
        pelanggan = random.choice(pelanggan_list)
        kasir_id  = random.choice(kasir_ids)
        berat     = round(random.uniform(2.0, 8.0), 1)
        
        # Pilih 1-2 layanan utama + optional addon
        layanan_dipilih = random.sample(layanan_utama, k=min(random.randint(1, 2), len(layanan_utama)))
        pakai_addon = random.random() > 0.5 and len(addon_list) > 0
        
        total_harga = 0
        details = []
        
        for l in layanan_dipilih:
            if l['harga_per_kg'] and float(l['harga_per_kg']) > 0:
                subtotal = float(l['harga_per_kg']) * berat
            else:
                subtotal = float(l['harga_satuan'])
            total_harga += subtotal
            details.append((l['id_layanan'], berat, 1, float(l['harga_per_kg']) or float(l['harga_satuan']), subtotal))
        
        if pakai_addon:
            addon = random.choice(addon_list)
            subtotal_addon = float(addon['harga_satuan'])
            total_harga += subtotal_addon
            details.append((addon['id_layanan'], 0, 1, float(addon['harga_satuan']), subtotal_addon))
        
        # Diskon VIP 10%
        diskon = 0
        if pelanggan_list[[p['id_pelanggan'] for p in pelanggan_list].index(pelanggan['id_pelanggan'])]:
            cur.execute("SELECT level_member FROM pelanggan WHERE id_pelanggan = %s", (pelanggan['id_pelanggan'],))
            pl = cur.fetchone()
            if pl and pl['level_member'] == 'VIP':
                diskon = total_harga * 0.1

        total_harga -= diskon
        
        # Status transaksi berdasarkan umur
        if hari_lalu == 0:
            status_cucian = random.choice(['antrian', 'sedang_dicuci'])
            status_bayar  = 'belum'
        elif hari_lalu == 1:
            status_cucian = random.choice(['sedang_dicuci', 'siap_diambil'])
            status_bayar  = random.choice(['belum', 'lunas'])
        else:
            status_cucian = 'selesai'
            status_bayar  = 'lunas'

        tgl_masuk           = datetime.combine(tgl, datetime.min.time()).replace(hour=random.randint(8, 17))
        tgl_estimasi_selesai = tgl + timedelta(days=2)

        cur.execute("""
            INSERT INTO transaksi 
              (kode_transaksi, id_pelanggan, id_kasir, tgl_masuk, tgl_estimasi_selesai,
               berat_kg, total_harga, diskon, status_bayar, status_cucian, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (kode, pelanggan['id_pelanggan'], kasir_id, tgl_masuk, tgl_estimasi_selesai,
              berat, total_harga, diskon, status_bayar, status_cucian, tgl_masuk))
        
        id_transaksi = cur.lastrowid

        for (id_l, brt, qty, harga_sat, sub) in details:
            cur.execute("""
                INSERT INTO detail_transaksi (id_transaksi, id_layanan, berat_kg, qty, harga_saat_transaksi, subtotal)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (id_transaksi, id_l, brt, qty, harga_sat, sub))

        # Update total_transaksi & poin pelanggan
        poin = int(total_harga // 10000)
        cur.execute("""
            UPDATE pelanggan 
            SET total_transaksi = total_transaksi + 1,
                poin_loyalitas  = poin_loyalitas + %s
            WHERE id_pelanggan = %s
        """, (poin, pelanggan['id_pelanggan']))

conn.commit()
print(f"[SUCCESS] Berhasil membuat {transaksi_count} transaksi dalam 7 hari terakhir!")

cur.execute("SELECT COUNT(*) AS total FROM transaksi")
print(f"Total transaksi di database: {cur.fetchone()['total']}")

cur.execute("SELECT COUNT(*) AS lunas FROM transaksi WHERE status_bayar = 'lunas'")
print(f"  - Lunas  : {cur.fetchone()['lunas']}")

cur.execute("SELECT COALESCE(SUM(total_harga),0) AS omzet FROM transaksi WHERE status_bayar='lunas'")
print(f"  - Total Omzet: Rp {cur.fetchone()['omzet']:,.0f}")

conn.close()
