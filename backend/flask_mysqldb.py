import pymysql
import pymysql.cursors
from flask import g

class MySQL:
    """
    Drop-in pure Python replacement untuk flask_mysqldb.
    Ini menghilangkan ketergantungan pada mysqlclient (C-extension) 
    yang selalu gagal di-build saat deploy ke Vercel Serverless.
    """
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.init_app(app)

    def init_app(self, app):
        @app.teardown_appcontext
        def teardown_db(exception):
            db = getattr(g, '_database', None)
            if db is not None:
                db.close()

    @property
    def connection(self):
        from config import Config
        db = getattr(g, '_database', None)
        if db is None:
            # Buat koneksi baru untuk konteks request ini
            ssl_args = None
            if hasattr(Config, 'MYSQL_EXTRA_ARGS') and 'ssl' in Config.MYSQL_EXTRA_ARGS:
                ssl_args = Config.MYSQL_EXTRA_ARGS['ssl']
                
            db = g._database = pymysql.connect(
                host=Config.MYSQL_HOST,
                user=Config.MYSQL_USER,
                password=Config.MYSQL_PASSWORD,
                database=Config.MYSQL_DB,
                port=getattr(Config, 'MYSQL_PORT', 3306),
                ssl=ssl_args,
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False  # Biarkan aplikasi yang melakukan commit (sama seperti flask_mysqldb)
            )
        return db
