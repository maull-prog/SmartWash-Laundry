import pymysql
from config import Config
import os

try:
    print("Mencoba koneksi ke TiDB untuk inisialisasi tabel...")
    conn = pymysql.connect(
        host=Config.MYSQL_HOST,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        port=Config.MYSQL_PORT,
        ssl={"ssl_mode": "VERIFY_IDENTITY"},
        client_flag=pymysql.constants.CLIENT.MULTI_STATEMENTS
    )
    
    cur = conn.cursor()
    
    # Path ke file schema.sql
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
    
    with open(schema_path, 'r', encoding='utf-8') as f:
        sql = f.read()
        
    print("Mengeksekusi schema.sql...")
    # Eksekusi semua script SQL secara berurutan
    for statement in sql.split(';'):
        if statement.strip():
            # Jika ini adalah INSERT, kita abaikan error duplicate entry
            try:
                cur.execute(statement)
            except pymysql.err.IntegrityError:
                pass  # Abaikan duplikat seed data
            except pymysql.err.OperationalError as oe:
                # Abaikan warning table already exists (1050)
                if oe.args[0] == 1050:
                    pass
                else:
                    raise oe
            except pymysql.err.InternalError as ie:
                if ie.args[0] == 1050:
                    pass
                else:
                    raise ie
                    
    conn.commit()
    print("[SUCCESS] Seluruh tabel berhasil dibuat/diperbarui di TiDB Cloud!")
    
    # Cek tabel
    cur.execute("SHOW TABLES;")
    tables = cur.fetchall()
    print("Tabel yang aktif saat ini:")
    for t in tables:
        print("-", t[0])
        
    conn.close()
except Exception as e:
    print("[FAILED] GAGAL menjalankan skrip:")
    print(e)
