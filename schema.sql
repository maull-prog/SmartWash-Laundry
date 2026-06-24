-- ============================================
-- Smart Wash Laundry — Database Schema
-- ============================================

CREATE DATABASE IF NOT EXISTS smartwash_db;
USE smartwash_db;

-- ------------------------------------------
-- Tabel pengguna (Owner & Kasir)
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS pengguna (
  id_pengguna INT PRIMARY KEY AUTO_INCREMENT,
  username VARCHAR(50) UNIQUE NOT NULL,
  password VARCHAR(255) NOT NULL,
  nama_lengkap VARCHAR(100) NOT NULL,
  no_hp VARCHAR(20),
  role ENUM('owner', 'kasir') DEFAULT 'kasir',
  aktif TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Seed pengguna
-- Password: owner01 → bcrypt hash
-- Password: kasir01 → bcrypt hash
-- Password: kasir02 → bcrypt hash
-- Password: kasir03 → bcrypt hash
INSERT INTO pengguna (username, password, nama_lengkap, role, aktif) VALUES
('budi', '$2b$12$ezR3am3ef3WKgGsokKIzMuott9azQlBlROLJV8VHPxkLErw6PJ3We', 'Bpk. Budi', 'owner', 1),
('rina_kasir', '$2b$12$xvC7liYt0FX8oycx6IYXie2n2SxY.ff6AOmwGnsWlQyoD5NyfAn2O', 'Rina Amelia', 'kasir', 1),
('dhimas_kasir', '$2b$12$YdQ3xpoX/2v0G8xRaduu0.Rf2pYiizgEfDmHVKDKIetFcL4ucJMb2', 'Dhimas Pratama', 'kasir', 1),
('siti_kasir', '$2b$12$63wGuiKoIe1IvpXNYrCSAuq3Fm/DZjAG.fShjkxLd/sqlZRIFrWLi', 'Siti Nurzalia', 'kasir', 1);

-- ------------------------------------------
-- Tabel pelanggan
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS pelanggan (
  id_pelanggan INT PRIMARY KEY AUTO_INCREMENT,
  nama VARCHAR(100) NOT NULL,
  no_hp VARCHAR(15),
  alamat TEXT,
  level_member ENUM('reguler', 'VIP') DEFAULT 'reguler',
  poin_loyalitas INT DEFAULT 0,
  total_transaksi INT DEFAULT 0,
  tgl_daftar DATE DEFAULT (CURRENT_DATE)
);

-- ------------------------------------------
-- Tabel layanan
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS layanan (
  id_layanan INT PRIMARY KEY AUTO_INCREMENT,
  nama_layanan VARCHAR(100) NOT NULL,
  kategori ENUM('Layanan', 'Add-on') DEFAULT 'Layanan',
  harga_per_kg DECIMAL(10,2) DEFAULT 0,
  harga_satuan DECIMAL(10,2) DEFAULT 0,
  estimasi_hari INT DEFAULT 2,
  deskripsi TEXT,
  aktif TINYINT(1) DEFAULT 1
);

INSERT INTO layanan (nama_layanan, kategori, harga_per_kg, estimasi_hari, aktif) VALUES
('Cuci Komplit', 'Layanan', 8000, 2, 1),
('Cuci Kering', 'Layanan', 6000, 2, 1),
('Setrika Saja', 'Layanan', 5000, 1, 1),
('Cuci Kilat (1 Hari)', 'Layanan', 12000, 1, 0);

INSERT INTO layanan (nama_layanan, kategori, harga_satuan, aktif) VALUES
('Pewangi Ekstra', 'Add-on', 3000, 1);

-- ------------------------------------------
-- Tabel promo
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS promo (
  id_promo INT PRIMARY KEY AUTO_INCREMENT,
  nama_promo VARCHAR(100) NOT NULL,
  syarat_min_kg DECIMAL(5,2) DEFAULT 0,
  nominal_potongan DECIMAL(10,2) DEFAULT 0,
  aktif TINYINT(1) DEFAULT 1,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

INSERT INTO promo (nama_promo, syarat_min_kg, nominal_potongan, aktif) VALUES
('Diskon Mahasiswa', 5, 5000, 1),
('Diskon Awal Bulan', 10, 15000, 0);

-- ------------------------------------------
-- Tabel transaksi
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS transaksi (
  id_transaksi INT PRIMARY KEY AUTO_INCREMENT,
  kode_transaksi VARCHAR(20) UNIQUE NOT NULL,
  id_pelanggan INT,
  id_kasir INT NOT NULL,
  id_promo INT NULL,
  tgl_masuk DATETIME DEFAULT CURRENT_TIMESTAMP,
  tgl_estimasi_selesai DATE,
  berat_kg DECIMAL(5,2) DEFAULT 0,
  total_harga DECIMAL(10,2) DEFAULT 0,
  diskon DECIMAL(10,2) DEFAULT 0,
  status_bayar ENUM('belum', 'lunas') DEFAULT 'belum',
  status_cucian ENUM('antrian', 'sedang_dicuci', 'siap_diambil', 'selesai') DEFAULT 'antrian',
  keterangan TEXT,
  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
  FOREIGN KEY (id_pelanggan) REFERENCES pelanggan(id_pelanggan),
  FOREIGN KEY (id_kasir) REFERENCES pengguna(id_pengguna),
  FOREIGN KEY (id_promo) REFERENCES promo(id_promo)
);

-- ------------------------------------------
-- Tabel detail_transaksi
-- ------------------------------------------
CREATE TABLE IF NOT EXISTS detail_transaksi (
  id_detail INT PRIMARY KEY AUTO_INCREMENT,
  id_transaksi INT NOT NULL,
  id_layanan INT NOT NULL,
  berat_kg DECIMAL(5,2) DEFAULT 0,
  qty INT DEFAULT 1,
  harga_saat_transaksi DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL,
  catatan TEXT,
  FOREIGN KEY (id_transaksi) REFERENCES transaksi(id_transaksi) ON DELETE CASCADE,
  FOREIGN KEY (id_layanan) REFERENCES layanan(id_layanan)
);
