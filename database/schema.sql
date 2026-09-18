-- StarNova database schema
-- Run this file after creating the `starnova` database in MySQL Workbench.

USE starnova;

-- Parent table: posts and applications both depend on users.
CREATE TABLE IF NOT EXISTS users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role ENUM('user', 'organizer') NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- A post belongs to one organizer (a user with the organizer role).
CREATE TABLE IF NOT EXISTS posts (
    id INT PRIMARY KEY AUTO_INCREMENT,
    organizer_id INT NOT NULL,
    title VARCHAR(200) NOT NULL,
    opportunity_type ENUM('audition', 'competition') NOT NULL,
    category ENUM('acting', 'music', 'dance') NOT NULL,
    event_date DATE NOT NULL,
    start_time TIME,
    end_time TIME,
    venue VARCHAR(255) NOT NULL,
    description TEXT,
    image_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_posts_organizer
        FOREIGN KEY (organizer_id) REFERENCES users(id),
    INDEX idx_posts_organizer_id (organizer_id),
    INDEX idx_posts_type_category_date (opportunity_type, category, event_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- An application connects one applicant to one opportunity post.
CREATE TABLE IF NOT EXISTS applications (
    id INT PRIMARY KEY AUTO_INCREMENT,
    post_id INT NOT NULL,
    applicant_id INT NOT NULL,
    experience TEXT,
    portfolio_url VARCHAR(500),
    status ENUM(
        'Pending',
        'Under Review',
        'Shortlisted',
        'Selected',
        'Rejected'
    ) NOT NULL DEFAULT 'Pending',
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    CONSTRAINT fk_applications_post
        FOREIGN KEY (post_id) REFERENCES posts(id),
    CONSTRAINT fk_applications_applicant
        FOREIGN KEY (applicant_id) REFERENCES users(id),
    CONSTRAINT uq_applications_post_applicant UNIQUE (post_id, applicant_id),
    INDEX idx_applications_applicant_id (applicant_id),
    INDEX idx_applications_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
