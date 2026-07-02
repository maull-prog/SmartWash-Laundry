import pymysql
from config import Config

try:
    print("Mencoba koneksi ke TiDB dengan PyMySQL...")
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        ssl={"ssl_mode": "VERIFY_IDENTITY"}
    )
    print("[SUCCESS] BERHASIL terhubung ke TiDB Cloud dengan PyMySQL!")
    
    cur = conn.cursor()
    cur.execute("SHOW TABLES;")
    tables = cur.fetchall()
    print("Tabel yang ditemukan di database:")
    for t in tables:
        print("-", t[0])
        
    conn.close()
except Exception as e:
    print("[FAILED] GAGAL terhubung:")
    print(e)
