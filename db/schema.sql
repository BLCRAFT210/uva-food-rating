CREATE TABLE IF NOT EXISTS Location (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(255) NOT NULL
);

CREATE TABLE IF NOT EXISTS Accommodations (
    accomm_id INT AUTO_INCREMENT PRIMARY KEY,
    vegan BOOLEAN,
    gluten_free BOOLEAN,
    nuts BOOLEAN,
    dairy BOOLEAN,
    seafood BOOLEAN
);

CREATE TABLE IF NOT EXISTS `User` (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    admin BOOLEAN DEFAULT FALSE,
    profile_picture TEXT
);

CREATE TABLE IF NOT EXISTS Friends (
    user_id INT,
    friend_user_id INT,
    PRIMARY KEY (user_id, friend_user_id),
    FOREIGN KEY (user_id) REFERENCES `User`(user_id) ON DELETE CASCADE,
    FOREIGN KEY (friend_user_id) REFERENCES `User`(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Dish (
    dish_id INT AUTO_INCREMENT PRIMARY KEY,
    dish_name VARCHAR(255) NOT NULL,
    accomm_id INT,
    location_id INT,
    FOREIGN KEY (accomm_id) REFERENCES Accommodations(accomm_id) ON DELETE SET NULL,
    FOREIGN KEY (location_id) REFERENCES Location(location_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS Rating (
    rating_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT,
    score INT CHECK (score >= 0 AND score <= 100),
    date_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    description TEXT,
    dish_id INT,
    FOREIGN KEY (user_id) REFERENCES `User`(user_id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id) REFERENCES Dish(dish_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Rating_Images (
    rating_id INT,
    image VARCHAR(255) NOT NULL,
    PRIMARY KEY (rating_id, image),
    FOREIGN KEY (rating_id) REFERENCES Rating(rating_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Rating_Tags (
    rating_id INT,
    tag VARCHAR(255) NOT NULL,
    PRIMARY KEY (rating_id, tag),
    FOREIGN KEY (rating_id) REFERENCES Rating(rating_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS RatingReview (
    rating_id INT,
    user_id INT,
    thumbs_up_down BOOLEAN NOT NULL,
    PRIMARY KEY (rating_id, user_id),
    FOREIGN KEY (rating_id) REFERENCES Rating(rating_id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES `User`(user_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS Favorites (
    user_id INT,
    dish_id INT,
    PRIMARY KEY (user_id, dish_id),
    FOREIGN KEY (user_id) REFERENCES `User`(user_id) ON DELETE CASCADE,
    FOREIGN KEY (dish_id) REFERENCES Dish(dish_id) ON DELETE CASCADE
);

CREATE INDEX idx_rating_dish_datetime ON Rating (dish_id, date_time);
CREATE INDEX idx_favorites_user_dish ON Favorites (user_id, dish_id);
CREATE INDEX idx_friends_user_friend ON Friends (user_id, friend_user_id);

DROP TRIGGER IF EXISTS before_ratingreview_insert;
DELIMITER //
CREATE TRIGGER before_ratingreview_insert
BEFORE INSERT ON RatingReview
FOR EACH ROW
BEGIN
    IF EXISTS (
        SELECT 1
        FROM Rating
        WHERE rating_id = NEW.rating_id AND user_id = NEW.user_id
    ) THEN
        SIGNAL SQLSTATE '45000'
        SET MESSAGE_TEXT = 'Error: You cannot review (thumbs up/down) your own rating.';
    END IF;
END; //
DELIMITER ;
