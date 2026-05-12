CREATE DATABASE absensi_qr;

USE absensi_qr;

CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    nama VARCHAR(100),
    username VARCHAR(100),
    password VARCHAR(100),
    role VARCHAR(20),
    qr_code VARCHAR(255)
);

INSERT INTO users(nama, username, password, role)
VALUES('Admin', 'admin', 'admin123', 'admin');