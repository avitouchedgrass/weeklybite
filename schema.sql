-- WeeklyBite database schema
-- MySQL 8.0+ / MariaDB 10.5+
--
-- Usage:
--   mysql -u root -p < schema.sql
--
-- This script only creates the empty structure. Run `python seed_db.py`
-- afterwards to load the demo user, ingredients and 24 starter recipes.

CREATE DATABASE IF NOT EXISTS weeklybite
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

USE weeklybite;

-- ---------------------------------------------------------------------------
-- Users and health profiles
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    username        VARCHAR(50)     NOT NULL,
    email           VARCHAR(120)    NOT NULL,
    password_hash   VARCHAR(128)    NOT NULL,
    salt            VARCHAR(64)     NOT NULL,
    full_name       VARCHAR(100)    NOT NULL DEFAULT '',
    age             INT             NOT NULL DEFAULT 24,
    height_cm       DECIMAL(5, 1)   NOT NULL DEFAULT 170.0,
    weight_kg       DECIMAL(5, 1)   NOT NULL DEFAULT 65.0,
    gender          VARCHAR(20)     NOT NULL DEFAULT 'male',
    fitness_goal    VARCHAR(20)     NOT NULL DEFAULT 'maintain',
    dietary_pref    VARCHAR(20)     NOT NULL DEFAULT 'all',
    cuisine_pref    VARCHAR(20)     NOT NULL DEFAULT 'all',
    weekly_budget   DECIMAL(10, 2)  NOT NULL DEFAULT 2000.00,
    activity_level  VARCHAR(20)     NOT NULL DEFAULT 'light',
    water_glasses   INT             NOT NULL DEFAULT 0,
    habits_json     JSON            NULL,
    created_at      TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_users_username (username),
    UNIQUE KEY uq_users_email (email)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------------
-- Ingredient catalogue (nutrition and cost are stored per unit)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS ingredients (
    id                  INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    name                VARCHAR(100)    NOT NULL,
    unit                VARCHAR(30)     NOT NULL,
    calories_per_unit   DECIMAL(8, 2)   NOT NULL DEFAULT 0.00,
    protein_per_unit    DECIMAL(8, 2)   NOT NULL DEFAULT 0.00,
    carbs_per_unit      DECIMAL(8, 2)   NOT NULL DEFAULT 0.00,
    fat_per_unit        DECIMAL(8, 2)   NOT NULL DEFAULT 0.00,
    unit_cost           DECIMAL(8, 2)   NOT NULL DEFAULT 0.00,
    category            VARCHAR(50)     NOT NULL,
    created_at          TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_ingredients_name (name),
    KEY idx_ingredients_category (category)
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------------
-- Recipes. user_id = NULL marks a shared recipe; otherwise it is a
-- user-created custom recipe.
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS meals (
    id                INT UNSIGNED    NOT NULL AUTO_INCREMENT,
    user_id           INT UNSIGNED    NULL,
    name              VARCHAR(120)    NOT NULL,
    meal_type         VARCHAR(20)     NOT NULL,
    dietary_category  VARCHAR(20)     NOT NULL DEFAULT 'vegetarian',
    cuisine_type      VARCHAR(20)     NOT NULL DEFAULT 'indian',
    description       TEXT            NULL,
    prep_time_mins    INT             NOT NULL DEFAULT 20,
    image_url         VARCHAR(500)    NOT NULL DEFAULT '',
    allergens         VARCHAR(255)    NOT NULL DEFAULT '',
    instructions      TEXT            NULL,
    created_at        TIMESTAMP       NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    KEY idx_meals_type (meal_type),
    KEY idx_meals_user (user_id),
    CONSTRAINT fk_meals_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------------
-- Recipe line items: how much of each ingredient a recipe needs
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS meal_ingredients (
    id             INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    meal_id        INT UNSIGNED   NOT NULL,
    ingredient_id  INT UNSIGNED   NOT NULL,
    quantity       DECIMAL(8, 2)  NOT NULL DEFAULT 1.00,
    PRIMARY KEY (id),
    UNIQUE KEY uq_meal_ingredient (meal_id, ingredient_id),
    KEY idx_meal_ingredients_ingredient (ingredient_id),
    CONSTRAINT fk_meal_ingredients_meal
        FOREIGN KEY (meal_id) REFERENCES meals (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_meal_ingredients_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------------
-- One saved meal slot per user, week and day
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS weekly_plans (
    id          INT UNSIGNED   NOT NULL AUTO_INCREMENT,
    user_id     INT UNSIGNED   NOT NULL,
    week_start  DATE           NOT NULL,
    day_name    VARCHAR(12)    NOT NULL,
    meal_type   VARCHAR(12)    NOT NULL,
    meal_id     INT UNSIGNED   NOT NULL,
    PRIMARY KEY (id),
    UNIQUE KEY uq_weekly_slot (user_id, week_start, day_name, meal_type),
    KEY idx_weekly_plans_meal (meal_id),
    CONSTRAINT fk_weekly_plans_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_weekly_plans_meal
        FOREIGN KEY (meal_id) REFERENCES meals (id)
        ON DELETE CASCADE
) ENGINE = InnoDB;

-- ---------------------------------------------------------------------------
-- Ingredients a user already owns; these are deducted from the grocery list
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS user_pantry (
    id             INT UNSIGNED  NOT NULL AUTO_INCREMENT,
    user_id        INT UNSIGNED  NOT NULL,
    ingredient_id  INT UNSIGNED  NOT NULL,
    added_at       TIMESTAMP     NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (id),
    UNIQUE KEY uq_pantry_item (user_id, ingredient_id),
    KEY idx_user_pantry_ingredient (ingredient_id),
    CONSTRAINT fk_user_pantry_user
        FOREIGN KEY (user_id) REFERENCES users (id)
        ON DELETE CASCADE,
    CONSTRAINT fk_user_pantry_ingredient
        FOREIGN KEY (ingredient_id) REFERENCES ingredients (id)
        ON DELETE CASCADE
) ENGINE = InnoDB;
