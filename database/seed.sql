-- StarNova development seed data
-- Run schema.sql first. These password_hash values are deliberately fake,
-- non-secret placeholders. They cannot be used to authenticate a real password.

USE starnova;

INSERT INTO users (name, email, password_hash, role) VALUES
    ('Ananya Rao', 'ananya.rao@starnova.test',
     'DUMMY_HASH_NOT_FOR_AUTH_ANANYA_ORGANIZER', 'organizer'),
    ('Rahul Sharma', 'rahul.sharma@starnova.test',
     'DUMMY_HASH_NOT_FOR_AUTH_RAHUL_USER', 'user'),
    ('Meera Iyer', 'meera.iyer@starnova.test',
     'DUMMY_HASH_NOT_FOR_AUTH_MEERA_USER', 'user');

-- The organizer ID is looked up by email so this script does not assume ID 1.
SET @organizer_id = (
    SELECT id FROM users WHERE email = 'ananya.rao@starnova.test'
);

INSERT INTO posts (
    organizer_id, title, opportunity_type, category, event_date,
    start_time, end_time, venue, description, image_path
) VALUES
    (
        @organizer_id, 'City Lights Film: Supporting Actor Audition',
        'audition', 'acting', '2026-11-08', '10:00:00', '16:00:00',
        'Ravindra Bharathi, Saifabad, Hyderabad',
        'Audition for supporting roles in a student short film. Prepare one monologue.',
        NULL
    ),
    (
        @organizer_id, 'Monsoon Melodies Vocal Audition',
        'audition', 'music', '2026-11-15', '11:00:00', '15:00:00',
        'Salar Jung Museum Auditorium, Hyderabad',
        'Seeking singers for a live independent music showcase.',
        NULL
    ),
    (
        @organizer_id, 'Campus Rhythm Dance Competition',
        'competition', 'dance', '2026-12-02', '09:30:00', '18:00:00',
        'Gachibowli Indoor Stadium, Hyderabad',
        'Solo and group dance competition for college performers.',
        NULL
    ),
    (
        @organizer_id, 'Stagecraft Theatre Acting Competition',
        'competition', 'acting', '2026-12-10', '13:00:00', '19:00:00',
        'Lamakaan, Banjara Hills, Hyderabad',
        'Perform a five-minute scene for a panel of theatre mentors.',
        NULL
    );

-- Look up the inserted people and posts before creating valid applications.
SET @rahul_id = (
    SELECT id FROM users WHERE email = 'rahul.sharma@starnova.test'
);
SET @meera_id = (
    SELECT id FROM users WHERE email = 'meera.iyer@starnova.test'
);
SET @acting_audition_id = (
    SELECT id FROM posts
    WHERE title = 'City Lights Film: Supporting Actor Audition'
      AND organizer_id = @organizer_id
);
SET @music_audition_id = (
    SELECT id FROM posts
    WHERE title = 'Monsoon Melodies Vocal Audition'
      AND organizer_id = @organizer_id
);
SET @dance_competition_id = (
    SELECT id FROM posts
    WHERE title = 'Campus Rhythm Dance Competition'
      AND organizer_id = @organizer_id
);
SET @acting_competition_id = (
    SELECT id FROM posts
    WHERE title = 'Stagecraft Theatre Acting Competition'
      AND organizer_id = @organizer_id
);

INSERT INTO applications (
    post_id, applicant_id, experience, portfolio_url, status
) VALUES
    (
        @acting_audition_id, @rahul_id,
        'Member of the college drama club with two stage productions.',
        'https://portfolio.example.test/rahul-acting', 'Under Review'
    ),
    (
        @dance_competition_id, @rahul_id,
        'Two years of hip-hop and freestyle dance experience.',
        'https://portfolio.example.test/rahul-dance', 'Pending'
    ),
    (
        @music_audition_id, @meera_id,
        'Carnatic vocalist and lead singer in the college music club.',
        'https://portfolio.example.test/meera-music', 'Shortlisted'
    ),
    (
        @acting_competition_id, @meera_id,
        'Performed in three inter-college theatre festivals.',
        'https://portfolio.example.test/meera-theatre', 'Selected'
    );
