import hashlib
import json
import os
import random
import secrets
from datetime import date, datetime
import pymysql
import pymysql.cursors
from dotenv import load_dotenv

load_dotenv()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = int(os.getenv("DB_PORT", 3306))
DB_USER = os.getenv("DB_USER", "root")
DB_PASSWORD = os.getenv("DB_PASSWORD", "1501")
DB_NAME = os.getenv("DB_NAME", "weeklybite")


def get_db():
    return pymysql.connect(
        host=DB_HOST,
        port=DB_PORT,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
    )


def hash_password(password: str, salt: str = None) -> tuple[str, str]:
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    return hashed.hex(), salt


def verify_password(password: str, salt: str, expected_hash: str) -> bool:
    hashed = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000).hex()
    return secrets.compare_digest(hashed, expected_hash)


# User authentication and profile
def authenticate_user(identifier: str, password: str):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT * FROM users WHERE username = %s OR email = %s LIMIT 1",
                (identifier.strip(), identifier.strip()),
            )
            user = cursor.fetchone()
            if not user:
                return None
            if verify_password(password, user["salt"], user["password_hash"]):
                return sanitize_user(user)
            return None
    finally:
        conn.close()


def register_user(username: str, email: str = "", password: str = "", full_name: str = ""):
    conn = get_db()
    u_clean = username.strip()
    e_clean = email.strip().lower() if email and email.strip() else f"{u_clean.lower()}@weeklybite.local"
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT id FROM users WHERE username = %s OR email = %s LIMIT 1",
                (u_clean, e_clean),
            )
            if cursor.fetchone():
                return False, "Username or email is already taken."

            pwd_hash, salt = hash_password(password)
            cursor.execute(
                """
                INSERT INTO users (username, email, password_hash, salt, full_name, age, height_cm, weight_kg, gender, fitness_goal, weekly_budget, activity_level, water_glasses, habits_json)
                VALUES (%s, %s, %s, %s, %s, 24, 170.0, 65.0, 'male', 'maintain', 2000.0, 'light', 0, '{"vitamins": false, "cooked": true, "exercise": false}')
            """,
                (u_clean, e_clean, pwd_hash, salt, full_name.strip()),
            )
            user_id = cursor.lastrowid
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return True, sanitize_user(cursor.fetchone())
    except Exception as e:
        return False, str(e)
    finally:
        conn.close()


def sanitize_user(user_dict: dict):
    if not user_dict:
        return None
    d = dict(user_dict)
    d.pop("password_hash", None)
    d.pop("salt", None)
    if isinstance(d.get("habits_json"), str):
        try:
            d["habits_json"] = json.loads(d["habits_json"])
        except Exception:
            d["habits_json"] = {}
    return d


def get_user_profile(user_id: int):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return sanitize_user(cursor.fetchone())
    finally:
        conn.close()


def update_user_profile(
    user_id: int,
    age: int,
    height: float,
    weight: float,
    gender: str,
    fitness_goal: str,
    activity: str,
    weekly_budget: float,
    dietary_pref: str = "all",
    cuisine_pref: str = "all",
):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                UPDATE users
                SET age = %s,
                    height_cm = %s,
                    weight_kg = %s,
                    gender = %s,
                    fitness_goal = %s,
                    activity_level = %s,
                    weekly_budget = %s,
                    dietary_pref = %s,
                    cuisine_pref = %s
                WHERE id = %s
            """,
                (
                    age,
                    height,
                    weight,
                    gender,
                    fitness_goal,
                    activity,
                    weekly_budget,
                    dietary_pref,
                    cuisine_pref,
                    user_id,
                ),
            )
            cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
            return sanitize_user(cursor.fetchone())
    finally:
        conn.close()


def update_water_intake(user_id: int, glasses: int):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            glasses = max(0, min(16, glasses))
            cursor.execute("UPDATE users SET water_glasses = %s WHERE id = %s", (glasses, user_id))
            return glasses
    finally:
        conn.close()


def update_user_habits(user_id: int, habits: dict):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE users SET habits_json = %s WHERE id = %s",
                (json.dumps(habits), user_id),
            )
            return habits
    finally:
        conn.close()


# Pantry inventory
def get_user_pantry(user_id: int):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute("SELECT ingredient_id FROM user_pantry WHERE user_id = %s", (user_id,))
            rows = cursor.fetchall()
            return [r["ingredient_id"] for r in rows]
    finally:
        conn.close()


def toggle_pantry_item(user_id: int, ingredient_id: int):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "SELECT 1 FROM user_pantry WHERE user_id = %s AND ingredient_id = %s",
                (user_id, ingredient_id),
            )
            if cursor.fetchone():
                cursor.execute(
                    "DELETE FROM user_pantry WHERE user_id = %s AND ingredient_id = %s",
                    (user_id, ingredient_id),
                )
                return False
            else:
                cursor.execute(
                    "INSERT INTO user_pantry (user_id, ingredient_id) VALUES (%s, %s)",
                    (user_id, ingredient_id),
                )
                return True
    finally:
        conn.close()


# Recipe and ingredient catalog
def load_catalog(user_id: int = None):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            if user_id:
                cursor.execute(
                    "SELECT * FROM meals WHERE user_id IS NULL OR user_id = %s ORDER BY name ASC",
                    (user_id,),
                )
            else:
                cursor.execute("SELECT * FROM meals WHERE user_id IS NULL ORDER BY name ASC")
            meals = cursor.fetchall()

            cursor.execute("SELECT * FROM ingredients ORDER BY category, name ASC")
            ingredients = cursor.fetchall()

            cursor.execute("SELECT meal_id, ingredient_id, quantity FROM meal_ingredients")
            links = cursor.fetchall()

            return meals, ingredients, links
    finally:
        conn.close()


def add_custom_meal(
    user_id: int,
    name: str,
    meal_type: str,
    dietary_category: str,
    cuisine_type: str,
    description: str,
    prep_time_mins: int,
    image_url: str,
    allergens: str,
    instructions: str,
    ingredient_quantities: list[tuple[int, float]],
):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO meals (user_id, name, meal_type, dietary_category, cuisine_type, description, prep_time_mins, image_url, allergens, instructions)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """,
                (
                    user_id,
                    name.strip(),
                    meal_type,
                    dietary_category,
                    cuisine_type,
                    description.strip(),
                    prep_time_mins,
                    image_url.strip() or "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80",
                    allergens.strip().lower(),
                    instructions.strip() or "Prepare ingredients according to your preferred cooking style and serve fresh.",
                ),
            )
            meal_id = cursor.lastrowid

            for ing_id, qty in ingredient_quantities:
                if qty > 0:
                    cursor.execute(
                        """
                        INSERT INTO meal_ingredients (meal_id, ingredient_id, quantity)
                        VALUES (%s, %s, %s)
                    """,
                        (meal_id, ing_id, qty),
                    )
            return meal_id
    finally:
        conn.close()


# Weekly plans
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEAL_TYPES = ["breakfast", "lunch", "dinner"]


def load_plan(user_id: int, week_start: str):
    plan = {d: {m: None for m in MEAL_TYPES} for d in DAYS}
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                """
                SELECT day_name, meal_type, meal_id
                FROM weekly_plans
                WHERE user_id = %s AND week_start = %s
            """,
                (user_id, week_start),
            )
            rows = cursor.fetchall()
            for row in rows:
                day_name = row["day_name"]
                meal_type = row["meal_type"]
                if day_name in plan and meal_type in plan[day_name]:
                    plan[day_name][meal_type] = row["meal_id"]
    finally:
        conn.close()
    return plan


def save_plan(user_id: int, plan: dict, week_start: str):
    conn = get_db()
    try:
        with conn.cursor() as cursor:
            cursor.execute(
                "DELETE FROM weekly_plans WHERE user_id = %s AND week_start = %s",
                (user_id, week_start),
            )

            for day in DAYS:
                for meal in MEAL_TYPES:
                    meal_id = plan.get(day, {}).get(meal)
                    if meal_id is not None:
                        cursor.execute(
                            """
                            INSERT INTO weekly_plans (user_id, week_start, day_name, meal_type, meal_id)
                            VALUES (%s, %s, %s, %s, %s)
                        """,
                            (user_id, week_start, day, meal, meal_id),
                        )
    finally:
        conn.close()


def auto_generate_balanced_plan(
    user_id: int,
    week_start: str,
    target_daily_calories: float,
    dietary_filter: list[str],
    cuisine_filter: list[str],
    excluded_allergens: list[str],
):
    meals, ingredients, links = load_catalog(user_id)

    # Precompute calories per meal
    ing_map = {i["id"]: float(i["calories_per_unit"]) for i in ingredients}
    meal_cals = {}
    for link in links:
        m_id = link["meal_id"]
        i_id = link["ingredient_id"]
        qty = float(link["quantity"])
        meal_cals[m_id] = meal_cals.get(m_id, 0.0) + (qty * ing_map.get(i_id, 0.0))

    def is_eligible(m):
        if dietary_filter and m["dietary_category"] not in dietary_filter:
            return False
        if cuisine_filter and m["cuisine_type"] not in cuisine_filter:
            return False
        if excluded_allergens:
            m_allergens = [a.strip() for a in (m.get("allergens") or "").split(",") if a.strip()]
            if any(ea in m_allergens for ea in excluded_allergens):
                return False
        return True

    eligible_b = [m for m in meals if m["meal_type"] == "breakfast" and is_eligible(m)]
    eligible_l = [m for m in meals if m["meal_type"] == "lunch" and is_eligible(m)]
    eligible_d = [m for m in meals if m["meal_type"] == "dinner" and is_eligible(m)]

    # Fallback to all meals if filters are too strict
    if not eligible_b:
        eligible_b = [m for m in meals if m["meal_type"] == "breakfast"]
    if not eligible_l:
        eligible_l = [m for m in meals if m["meal_type"] == "lunch"]
    if not eligible_d:
        eligible_d = [m for m in meals if m["meal_type"] == "dinner"]

    random.shuffle(eligible_b)
    random.shuffle(eligible_l)
    random.shuffle(eligible_d)

    # Track usage count to prevent repeated meals across the 7 days
    used_b = {}
    used_l = {}
    used_d = {}

    b_target = target_daily_calories * 0.25
    new_plan = {}

    for day in DAYS:
        # Prioritize unused meals closest to meal calorie targets
        cand_b = sorted(
            eligible_b,
            key=lambda m: (
                used_b.get(m["id"], 0),
                abs(meal_cals.get(m["id"], 0) - b_target) + random.uniform(0, 40),
            ),
        )
        chosen_b = cand_b[0]
        used_b[chosen_b["id"]] = used_b.get(chosen_b["id"], 0) + 1

        rem_after_b = target_daily_calories - meal_cals.get(chosen_b["id"], 0)
        l_target = rem_after_b * 0.55
        cand_l = sorted(
            eligible_l,
            key=lambda m: (
                used_l.get(m["id"], 0),
                abs(meal_cals.get(m["id"], 0) - l_target) + random.uniform(0, 40),
            ),
        )
        chosen_l = cand_l[0]
        used_l[chosen_l["id"]] = used_l.get(chosen_l["id"], 0) + 1

        d_target = target_daily_calories - meal_cals.get(chosen_b["id"], 0) - meal_cals.get(chosen_l["id"], 0)
        cand_d = sorted(
            eligible_d,
            key=lambda m: (
                used_d.get(m["id"], 0),
                abs(meal_cals.get(m["id"], 0) - d_target) + random.uniform(0, 40),
            ),
        )
        chosen_d = cand_d[0]
        used_d[chosen_d["id"]] = used_d.get(chosen_d["id"], 0) + 1

        new_plan[day] = {
            "breakfast": chosen_b["id"],
            "lunch": chosen_l["id"],
            "dinner": chosen_d["id"],
        }

    save_plan(user_id, new_plan, week_start)
    return new_plan
