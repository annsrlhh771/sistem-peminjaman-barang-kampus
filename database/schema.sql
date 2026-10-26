-- =====================================================================
-- Project   : Sistem Peminjaman Barang Kampus
-- Nama      : Annasrulloh
-- DBMS      : PostgreSQL
-- Deskripsi : Struktur database untuk mengelola pengguna, barang,
--             peminjaman, dan pengembalian barang kampus.
--
-- Daftar tabel (7 tabel):
--   1. peran               : master peran pengguna (admin / peminjam)
--   2. pengguna            : akun pengguna (login & register)
--   3. kategori_barang     : master kategori barang
--   4. barang              : data barang (CRUD, status barang)
--   5. peminjaman          : header pengajuan peminjaman
--   6. detail_peminjaman   : barang yang dipinjam pada tiap peminjaman
--   7. pengembalian        : pencatatan pengembalian barang
--
-- Relasi:
--   peran (1) ---- (N) pengguna                   -> 1:N
--   kategori_barang (1) ---- (N) barang           -> 1:N
--   pengguna (1) ---- (N) peminjaman              -> 1:N
--   peminjaman (N) ---- (N) barang                -> N:N
--        (dipecah oleh tabel detail_peminjaman)
--   detail_peminjaman (1) ---- (1) pengembalian   -> 1:1
-- =====================================================================

-- Bersihkan objek lama agar script dapat dijalankan berulang kali
DROP TABLE IF EXISTS pengembalian       CASCADE;
DROP TABLE IF EXISTS detail_peminjaman  CASCADE;
DROP TABLE IF EXISTS peminjaman         CASCADE;
DROP TABLE IF EXISTS barang             CASCADE;
DROP TABLE IF EXISTS kategori_barang    CASCADE;
DROP TABLE IF EXISTS pengguna           CASCADE;
DROP TABLE IF EXISTS peran              CASCADE;

DROP TYPE IF EXISTS status_barang_enum;
DROP TYPE IF EXISTS status_peminjaman_enum;
DROP TYPE IF EXISTS kondisi_barang_enum;

-- ---------------------------------------------------------------------
-- TIPE ENUM
-- ---------------------------------------------------------------------
-- Status barang (fungsi updateStatusBarang, cekKetersediaanBarang)
CREATE TYPE status_barang_enum AS ENUM ('tersedia', 'dipinjam', 'perbaikan');

-- Status pengajuan (fungsi ajukanPeminjaman, setujuiPeminjaman, tolakPeminjaman)
CREATE TYPE status_peminjaman_enum AS ENUM
    ('diajukan', 'disetujui', 'ditolak', 'dipinjam', 'selesai');

-- Kondisi barang saat dikembalikan (fungsi prosesPengembalian)
CREATE TYPE kondisi_barang_enum AS ENUM ('baik', 'rusak_ringan', 'rusak_berat', 'hilang');

-- ---------------------------------------------------------------------
-- 1. TABEL peran
-- ---------------------------------------------------------------------
CREATE TABLE peran (
    id_peran    SERIAL       PRIMARY KEY,
    nama_peran  VARCHAR(30)  NOT NULL UNIQUE,   -- contoh: admin, peminjam
    deskripsi   VARCHAR(150)
);

-- ---------------------------------------------------------------------
-- 2. TABEL pengguna  (loginPengguna, registerPengguna, getDataPengguna)
-- ---------------------------------------------------------------------
CREATE TABLE pengguna (
    id_pengguna   SERIAL        PRIMARY KEY,
    id_peran      INT           NOT NULL,
    nama_lengkap  VARCHAR(100)  NOT NULL,
    nim_nip       VARCHAR(30)   NOT NULL UNIQUE,   -- NIM mahasiswa / NIP dosen & staf
    email         VARCHAR(100)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,          -- simpan hash, bukan password asli
    no_telepon    VARCHAR(20),
    created_at    TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_pengguna_peran
        FOREIGN KEY (id_peran) REFERENCES peran (id_peran)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- 3. TABEL kategori_barang
-- ---------------------------------------------------------------------
CREATE TABLE kategori_barang (
    id_kategori    SERIAL       PRIMARY KEY,
    nama_kategori  VARCHAR(80)  NOT NULL UNIQUE,   -- contoh: Elektronik, Alat Lab, Multimedia
    deskripsi      VARCHAR(150)
);

-- ---------------------------------------------------------------------
-- 4. TABEL barang  (getDataBarang, tambah/edit/hapusDataBarang,
--                   cekKetersediaanBarang, updateStatusBarang)
-- ---------------------------------------------------------------------
CREATE TABLE barang (
    id_barang      SERIAL              PRIMARY KEY,
    id_kategori    INT                 NOT NULL,
    kode_barang    VARCHAR(30)         NOT NULL UNIQUE,
    nama_barang    VARCHAR(100)        NOT NULL,
    deskripsi      TEXT,
    lokasi_simpan  VARCHAR(100),
    status         status_barang_enum  NOT NULL DEFAULT 'tersedia',
    created_at     TIMESTAMP           NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_barang_kategori
        FOREIGN KEY (id_kategori) REFERENCES kategori_barang (id_kategori)
        ON UPDATE CASCADE ON DELETE RESTRICT
);

-- ---------------------------------------------------------------------
-- 5. TABEL peminjaman  (ajukanPeminjaman, getDataPeminjaman,
--                       setujuiPeminjaman, tolakPeminjaman)
-- ---------------------------------------------------------------------
CREATE TABLE peminjaman (
    id_peminjaman       SERIAL                  PRIMARY KEY,
    id_pengguna         INT                     NOT NULL,   -- peminjam
    id_admin            INT,                                -- admin yang menyetujui/menolak
    tanggal_pengajuan   TIMESTAMP               NOT NULL DEFAULT CURRENT_TIMESTAMP,
    tanggal_pinjam      DATE                    NOT NULL,
    tanggal_kembali_rencana DATE                NOT NULL,
    keperluan           VARCHAR(255)            NOT NULL,
    status              status_peminjaman_enum  NOT NULL DEFAULT 'diajukan',
    catatan_admin       VARCHAR(255),                       -- alasan penolakan / catatan persetujuan
    tanggal_diproses    TIMESTAMP,

    CONSTRAINT fk_peminjaman_pengguna
        FOREIGN KEY (id_pengguna) REFERENCES pengguna (id_pengguna)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    CONSTRAINT fk_peminjaman_admin
        FOREIGN KEY (id_admin) REFERENCES pengguna (id_pengguna)
        ON UPDATE CASCADE ON DELETE SET NULL,
    CONSTRAINT chk_tanggal_peminjaman
        CHECK (tanggal_kembali_rencana >= tanggal_pinjam)
);

-- ---------------------------------------------------------------------
-- 6. TABEL detail_peminjaman
--    Tabel penghubung relasi N:N antara peminjaman dan barang
--    (satu peminjaman bisa berisi banyak barang, satu barang bisa
--     dipinjam berkali-kali pada peminjaman yang berbeda)
-- ---------------------------------------------------------------------
CREATE TABLE detail_peminjaman (
    id_detail      SERIAL  PRIMARY KEY,
    id_peminjaman  INT     NOT NULL,
    id_barang      INT     NOT NULL,

    CONSTRAINT fk_detail_peminjaman
        FOREIGN KEY (id_peminjaman) REFERENCES peminjaman (id_peminjaman)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_detail_barang
        FOREIGN KEY (id_barang) REFERENCES barang (id_barang)
        ON UPDATE CASCADE ON DELETE RESTRICT,
    -- satu barang tidak boleh muncul dua kali dalam satu peminjaman
    CONSTRAINT uq_detail_peminjaman_barang
        UNIQUE (id_peminjaman, id_barang)
);

-- ---------------------------------------------------------------------
-- 7. TABEL pengembalian  (prosesPengembalian, getRiwayatPeminjaman)
--    Relasi 1:1 dengan detail_peminjaman: setiap barang yang dipinjam
--    hanya memiliki satu catatan pengembalian (UNIQUE pada FK).
-- ---------------------------------------------------------------------
CREATE TABLE pengembalian (
    id_pengembalian       SERIAL               PRIMARY KEY,
    id_detail             INT                  NOT NULL UNIQUE,   -- UNIQUE => relasi 1:1
    id_admin              INT,                                    -- admin yang mencatat
    tanggal_dikembalikan  TIMESTAMP            NOT NULL DEFAULT CURRENT_TIMESTAMP,
    kondisi               kondisi_barang_enum  NOT NULL DEFAULT 'baik',
    catatan               VARCHAR(255),

    CONSTRAINT fk_pengembalian_detail
        FOREIGN KEY (id_detail) REFERENCES detail_peminjaman (id_detail)
        ON UPDATE CASCADE ON DELETE CASCADE,
    CONSTRAINT fk_pengembalian_admin
        FOREIGN KEY (id_admin) REFERENCES pengguna (id_pengguna)
        ON UPDATE CASCADE ON DELETE SET NULL
);

-- ---------------------------------------------------------------------
-- INDEX (mempercepat pencarian yang sering dipakai)
-- ---------------------------------------------------------------------
CREATE INDEX idx_pengguna_peran         ON pengguna (id_peran);
CREATE INDEX idx_barang_kategori        ON barang (id_kategori);
CREATE INDEX idx_barang_status          ON barang (status);
CREATE INDEX idx_peminjaman_pengguna    ON peminjaman (id_pengguna);
CREATE INDEX idx_peminjaman_status      ON peminjaman (status);
CREATE INDEX idx_detail_peminjaman      ON detail_peminjaman (id_peminjaman);
CREATE INDEX idx_detail_barang          ON detail_peminjaman (id_barang);

-- ---------------------------------------------------------------------
-- DATA AWAL (opsional, untuk pengujian)
-- ---------------------------------------------------------------------
INSERT INTO peran (nama_peran, deskripsi) VALUES
    ('admin',   'Mengelola data barang dan memproses peminjaman'),
    ('peminjam','Mahasiswa, dosen, atau staf yang meminjam barang');

INSERT INTO kategori_barang (nama_kategori, deskripsi) VALUES
    ('Elektronik', 'Proyektor, laptop, kamera, dan sejenisnya'),
    ('Alat Laboratorium', 'Peralatan praktikum'),
    ('Perlengkapan Acara', 'Sound system, kursi, meja, dan sejenisnya');