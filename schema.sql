-- =============================================================
-- CampusTrack — Student Attendance & Academic Management System
-- schema.sql
-- Run:  mysql -u root -p < schema.sql
-- =============================================================

CREATE DATABASE IF NOT EXISTS campustrack_db
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE campustrack_db;

CREATE TABLE IF NOT EXISTS users (
    user_id    INT          NOT NULL AUTO_INCREMENT,
    username   VARCHAR(50)  NOT NULL,
    password   VARCHAR(255) NOT NULL,
    full_name  VARCHAR(100) NOT NULL,
    role       ENUM('admin','teacher') NOT NULL DEFAULT 'teacher',
    created_at DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id),
    UNIQUE KEY uq_username (username)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS students (
    student_id  INT          NOT NULL AUTO_INCREMENT,
    roll_number VARCHAR(20)  NOT NULL,
    full_name   VARCHAR(100) NOT NULL,
    email       VARCHAR(100),
    phone       VARCHAR(15),
    department  VARCHAR(100) NOT NULL,
    semester    TINYINT      NOT NULL,
    created_at  DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id),
    UNIQUE KEY uq_roll (roll_number),
    KEY idx_department (department),
    KEY idx_semester   (semester)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS subjects (
    subject_id   INT          NOT NULL AUTO_INCREMENT,
    subject_code VARCHAR(20)  NOT NULL,
    subject_name VARCHAR(100) NOT NULL,
    department   VARCHAR(100) NOT NULL,
    semester     TINYINT      NOT NULL,
    created_at   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (subject_id),
    UNIQUE KEY uq_subject_code (subject_code),
    KEY idx_sub_department (department),
    KEY idx_sub_semester   (semester)
) ENGINE=InnoDB;

CREATE TABLE IF NOT EXISTS attendance (
    attendance_id INT      NOT NULL AUTO_INCREMENT,
    student_id    INT      NOT NULL,
    subject_id    INT      NOT NULL,
    date          DATE     NOT NULL,
    status        ENUM('Present','Absent') NOT NULL,
    marked_by     INT,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (attendance_id),
    UNIQUE KEY uq_att (student_id, subject_id, date),
    KEY idx_att_date    (date),
    KEY idx_att_student (student_id),
    KEY idx_att_subject (subject_id),
    CONSTRAINT fk_att_student FOREIGN KEY (student_id)
        REFERENCES students (student_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_att_subject FOREIGN KEY (subject_id)
        REFERENCES subjects (subject_id) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT fk_att_user FOREIGN KEY (marked_by)
        REFERENCES users (user_id) ON DELETE SET NULL ON UPDATE CASCADE
) ENGINE=InnoDB;

-- Demo students
INSERT IGNORE INTO students (roll_number, full_name, email, phone, department, semester) VALUES
    ('CS2401','Aisha Khan',   'aisha@college.edu', '9000000001','Computer Science',1),
    ('CS2402','Rohan Sharma', 'rohan@college.edu', '9000000002','Computer Science',1),
    ('CS2403','Priya Mehta',  'priya@college.edu', '9000000003','Computer Science',1),
    ('CS2404','Arjun Singh',  'arjun@college.edu', '9000000004','Computer Science',2),
    ('IT2401','Nadia Ali',    'nadia@college.edu', '9000000005','Information Tech', 1),
    ('IT2402','Dev Patel',    'dev@college.edu',   '9000000006','Information Tech', 1);

-- Demo subjects
INSERT IGNORE INTO subjects (subject_code, subject_name, department, semester) VALUES
    ('CS101','Introduction to Programming','Computer Science',1),
    ('CS102','Mathematics for CS',         'Computer Science',1),
    ('CS201','Data Structures',            'Computer Science',2),
    ('IT101','Web Technologies',           'Information Tech', 1),
    ('IT102','Database Management',        'Information Tech', 1);
