-- Create Database
CREATE DATABASE IF NOT EXISTS newsapp_db;
USE newsapp_db;

-- 1. users table
CREATE TABLE IF NOT EXISTS users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL, -- To store hashed passwords
    role ENUM('user', 'admin') DEFAULT 'user',
    plan ENUM('free', 'paid') DEFAULT 'free'
);

-- Insert a default Admin user (password: adminpass)
-- Hashing is required in the application logic, but for a quick setup:
-- We'll rely on the app.py to insert the first hashed admin user.

-- 2. saved_articles table
CREATE TABLE IF NOT EXISTS saved_articles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title TEXT NOT NULL,
    url VARCHAR(500) NOT NULL,
    source VARCHAR(100),
    published_at DATETIME,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    UNIQUE KEY unique_article_per_user (user_id, url(255))
);

-- 3. search_tracking table
CREATE TABLE IF NOT EXISTS search_tracking (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    topic VARCHAR(255) NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    articles_shown INT NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 4. api_warnings table
CREATE TABLE IF NOT EXISTS api_warnings (
    id INT AUTO_INCREMENT PRIMARY KEY,
    warning_message TEXT NOT NULL,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
);