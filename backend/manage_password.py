import bcrypt
import MySQLdb
import getpass

def get_db_connection():
    try:
        # Sesuaikan dengan konfigurasi database Anda
        return MySQLdb.connect(host="localhost", user="root", passwd="", db="smartwash_db")
    except MySQLdb.Error as e:
        print(f"\n❌ Gagal terhubung ke database: {e}")
        print("Pastikan MySQL (XAMPP/WAMP) sudah menyala dan database 'smartwash_db' sudah ada.")
        return None

def hash_password(password):
    """Menghasilkan hash bcrypt yang aman dan valid."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def list_users(cur):
    """Menampilkan daftar semua pengguna."""
    cur.execute("SELECT id_pengguna, username, nama_lengkap, role, aktif FROM pengguna")
    users = cur.fetchall()
    
    print("\n" + "="*50)
    print(f"{'ID':<5} | {'USERNAME':<15} | {'ROLE':<10} | {'STATUS'}")
    print("="*50)
    
    if not users:
        print("Belum ada data pengguna.")
        return
        
    for u in users:
        status = "Aktif" if u[4] else "Non-Aktif"
        print(f"{u[0]:<5} | {u[1]:<15} | {u[3]:<10} | {status}")
    print("="*50)

def reset_password(db, cur):
    """Fungsi interaktif untuk mengubah password pengguna."""
    print("\n--- RESET PASSWORD PENGGUNA ---")
    username = input("Masukkan username yang ingin direset passwordnya: ").strip()
    
    # Cek apakah user ada
    cur.execute("SELECT id_pengguna, nama_lengkap, role FROM pengguna WHERE username = %s", (username,))
    user = cur.fetchone()
    
    if not user:
        print(f"❌ Error: Username '{username}' tidak ditemukan di database!")
        return

    print(f"✅ Ditemukan pengguna: {user[1]} (Role: {user[2]})")
    
    # Meminta password baru dengan getpass agar tidak terlihat saat diketik
    new_password = getpass.getpass("Masukkan password baru: ").strip()
    confirm_password = getpass.getpass("Konfirmasi password baru: ").strip()
    
    if not new_password:
        print("❌ Error: Password tidak boleh kosong!")
        return
        
    if new_password != confirm_password:
        print("❌ Error: Password konfirmasi tidak cocok!")
        return
        
    try:
        # Enkripsi password
        hashed = hash_password(new_password)
        
        # Simpan ke database
        cur.execute("UPDATE pengguna SET password = %s WHERE username = %s", (hashed, username))
        db.commit()
        print(f"\n✅ SUKSES! Password untuk akun '{username}' berhasil diperbarui.")
        print("Sekarang Anda bisa menggunakan password baru tersebut untuk login di aplikasi web.")
        
    except Exception as e:
        db.rollback()
        print(f"\n❌ Terjadi kesalahan saat menyimpan: {e}")

def main():
    print("========================================")
    print("  SMART WASH LAUNDRY - PASSWORD MANAGER ")
    print("========================================")
    
    db = get_db_connection()
    if not db:
        return
        
    cur = db.cursor()
    
    while True:
        print("\nPilih Menu:")
        print("1. Lihat Daftar Pengguna")
        print("2. Reset / Ubah Password")
        print("3. Keluar")
        
        pilihan = input("Masukkan pilihan (1/2/3): ").strip()
        
        if pilihan == '1':
            list_users(cur)
        elif pilihan == '2':
            reset_password(db, cur)
        elif pilihan == '3':
            print("Keluar dari program. Terima kasih!")
            break
        else:
            print("❌ Pilihan tidak valid!")

    cur.close()
    db.close()

if __name__ == "__main__":
    main()
