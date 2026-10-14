import hashlib
import os
import secrets
from datetime import date, timedelta
import pymysql
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


def seed():
    conn = get_db()
    cursor = conn.cursor()

    print("Cleaning existing records for fresh pristine seed...")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
    cursor.execute("TRUNCATE TABLE user_pantry;")
    cursor.execute("TRUNCATE TABLE weekly_plans;")
    cursor.execute("TRUNCATE TABLE meal_ingredients;")
    cursor.execute("TRUNCATE TABLE meals;")
    cursor.execute("TRUNCATE TABLE ingredients;")
    cursor.execute("TRUNCATE TABLE users;")
    cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")

    # 1. Seed Demo User as John Doe
    demo_hash, demo_salt = hash_password("password123")
    cursor.execute(
        """
        INSERT INTO users (username, email, password_hash, salt, full_name, age, height_cm, weight_kg, gender, fitness_goal, dietary_pref, cuisine_pref, weekly_budget, activity_level, water_glasses, habits_json)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, 4, '{"vitamins": true, "cooked": true, "exercise": false}')
    """,
        (
            "demo",
            "demo@weeklybite.local",
            demo_hash,
            demo_salt,
            "John Doe",
            25,
            175.0,
            70.0,
            "male",
            "maintain",
            "all",
            "all",
            2500.0,
            "moderate",
        ),
    )
    demo_user_id = cursor.lastrowid
    print(f"Created demo user 'demo' (id: {demo_user_id}, full_name: 'John Doe')")

    # 2. Seed Ingredients
    ingredients_data = [
        # Grains & Staples
        ("Rolled Oats", "100g", 380, 13.0, 68.0, 7.0, 30.0, "Grains & Staples"),
        ("Basmati Rice", "100g", 350, 7.0, 77.0, 1.0, 15.0, "Grains & Staples"),
        ("Brown Rice", "100g", 340, 7.5, 72.0, 2.5, 20.0, "Grains & Staples"),
        ("Whole Wheat Atta (Roti)", "100g", 340, 12.0, 71.0, 1.5, 8.0, "Grains & Staples"),
        ("Poha (Flattened Rice)", "100g", 360, 6.5, 79.0, 1.0, 10.0, "Grains & Staples"),
        ("Quinoa", "100g", 368, 14.0, 64.0, 6.0, 40.0, "Grains & Staples"),
        ("Brown Bread", "2 slices", 150, 6.0, 28.0, 2.0, 12.0, "Grains & Staples"),
        ("Sourdough Bread", "2 slices", 180, 7.0, 36.0, 1.5, 25.0, "Grains & Staples"),
        ("Penne Pasta", "100g", 350, 12.0, 71.0, 1.5, 18.0, "Grains & Staples"),
        # Proteins & Pulses
        ("Chicken Breast", "150g", 240, 46.0, 0.0, 5.0, 65.0, "Protein"),
        ("Eggs (Large)", "2 pcs", 148, 12.6, 0.8, 10.0, 16.0, "Protein"),
        ("Salmon Fillet", "150g", 310, 34.0, 0.0, 18.0, 190.0, "Protein"),
        ("Yellow Moong Dal", "60g", 210, 14.5, 36.0, 0.8, 12.0, "Protein"),
        ("Rajma (Kidney Beans)", "70g", 235, 16.0, 42.0, 1.0, 15.0, "Protein"),
        ("Chole (Chickpeas)", "70g", 255, 14.0, 43.0, 4.0, 15.0, "Protein"),
        ("Soya Chunks", "50g", 170, 26.0, 16.0, 0.5, 12.0, "Protein"),
        ("Tofu (Firm)", "150g", 125, 13.0, 3.5, 7.0, 35.0, "Protein"),
        # Dairy & Alternatives
        ("Paneer (Cottage Cheese)", "100g", 265, 18.0, 3.0, 20.0, 45.0, "Dairy"),
        ("Cow Milk (Tonned)", "200ml", 116, 6.2, 9.4, 6.0, 14.0, "Dairy"),
        ("Curd / Yogurt", "150g", 90, 5.5, 7.0, 4.5, 15.0, "Dairy"),
        ("Greek Yogurt", "150g", 140, 15.0, 6.0, 5.0, 40.0, "Dairy"),
        ("Cheddar Cheese", "30g", 120, 7.0, 0.5, 10.0, 30.0, "Dairy"),
        # Produce (Vegetables & Fruits)
        ("Onion", "100g", 40, 1.1, 9.3, 0.1, 5.0, "Produce"),
        ("Tomato", "100g", 18, 0.9, 3.9, 0.2, 5.0, "Produce"),
        ("Spinach (Palak)", "150g", 35, 4.3, 5.4, 0.6, 15.0, "Produce"),
        ("Broccoli", "150g", 50, 4.2, 10.0, 0.6, 30.0, "Produce"),
        ("Bell Pepper / Capsicum", "100g", 25, 1.0, 5.5, 0.2, 12.0, "Produce"),
        ("Potato", "150g", 115, 3.0, 26.0, 0.2, 8.0, "Produce"),
        ("Garlic & Ginger", "15g", 18, 0.5, 4.0, 0.1, 4.0, "Produce"),
        ("Banana", "1 pc", 105, 1.3, 27.0, 0.3, 7.0, "Produce"),
        ("Mixed Berries", "80g", 45, 0.8, 11.0, 0.3, 50.0, "Produce"),
        ("Hass Avocado", "1 pc", 240, 3.0, 12.0, 22.0, 75.0, "Produce"),
        # Healthy Fats, Nuts & Seeds
        ("Olive Oil", "15ml", 120, 0.0, 0.0, 13.5, 16.0, "Oils & Fats"),
        ("Pure Desi Ghee", "10g", 90, 0.0, 0.0, 10.0, 15.0, "Oils & Fats"),
        ("Peanuts (Roasted)", "30g", 170, 7.5, 4.8, 14.5, 8.0, "Nuts & Seeds"),
        ("Chia Seeds", "15g", 73, 2.5, 6.3, 4.6, 12.0, "Nuts & Seeds"),
        ("Peanut Butter", "30g", 190, 8.0, 6.0, 16.0, 18.0, "Nuts & Seeds"),
    ]

    ing_id_map = {}
    for name, unit, cal, prot, carb, fat, cost, cat in ingredients_data:
        cursor.execute(
            """
            INSERT INTO ingredients (name, unit, calories_per_unit, protein_per_unit, carbs_per_unit, fat_per_unit, unit_cost, category)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (name, unit, cal, prot, carb, fat, cost, cat),
        )
        ing_id_map[name] = cursor.lastrowid

    # Give demo user pantry staples
    pantry_seed_names = ["Basmati Rice", "Yellow Moong Dal", "Olive Oil", "Onion", "Garlic & Ginger"]
    for pname in pantry_seed_names:
        if pname in ing_id_map:
            cursor.execute("INSERT INTO user_pantry (user_id, ingredient_id) VALUES (%s, %s)", (demo_user_id, ing_id_map[pname]))

    # 3. Exactly matched, unique high-res editorial daylight photos for all 24 meals
    meals_catalog = [
        # --- BREAKFAST (8 distinct recipes) ---
        (
            "Masala Spiced Oats",
            "breakfast",
            "vegetarian",
            "indian",
            "Rolled oats slow-cooked with fresh onion, ripe tomato, and aromatic Indian whole spices.",
            15,
            "https://images.unsplash.com/photo-1517673132405-a56a62b18caf?auto=format&fit=crop&w=800&q=80",
            "gluten",
            "1. Heat olive oil in a pan and sauté diced onions until translucent.\n2. Add chopped tomatoes, a pinch of turmeric, and salt; cook until softened.\n3. Add rolled oats and 1.5 cups of water. Simmer on low heat for 5 minutes.\n4. Garnish with fresh herbs and serve warm.",
            [("Rolled Oats", 1.0), ("Onion", 0.5), ("Tomato", 0.5), ("Olive Oil", 0.5)],
        ),
        (
            "Paneer Bhurji & Toast",
            "breakfast",
            "vegetarian",
            "indian",
            "Hand-crumbled fresh cottage cheese wok-tossed with shallots, tomatoes, and toasted brown bread.",
            15,
            "https://images.unsplash.com/photo-1565557623262-b51c2513a641?auto=format&fit=crop&w=800&q=80",
            "dairy,gluten",
            "1. Melt desi ghee in a skillet over medium heat.\n2. Add finely diced onions and tomatoes; sauté until fragrant.\n3. Crumble fresh paneer into the skillet and toss gently with salt and cumin.\n4. Toast brown bread slices until crisp and serve alongside.",
            [("Paneer (Cottage Cheese)", 1.0), ("Brown Bread", 1.0), ("Onion", 0.5), ("Tomato", 0.5), ("Pure Desi Ghee", 0.5)],
        ),
        (
            "Scrambled Eggs on Sourdough",
            "breakfast",
            "non-vegetarian",
            "international",
            "Soft-curd pasture eggs served gently over artisanal toasted sourdough with cold-pressed olive oil.",
            12,
            "https://images.unsplash.com/photo-1525351484163-7529414344d8?auto=format&fit=crop&w=800&q=80",
            "eggs,gluten",
            "1. Whisk eggs in a small ceramic bowl with a pinch of salt.\n2. Heat olive oil in a non-stick pan over gentle low-medium heat.\n3. Pour in eggs and fold slowly with a silicone spatula for creamy soft curds.\n4. Pile onto hot toasted sourdough bread and finish with cracked black pepper.",
            [("Eggs (Large)", 1.0), ("Sourdough Bread", 1.0), ("Olive Oil", 0.5)],
        ),
        (
            "Homestyle Poha with Peanuts",
            "breakfast",
            "vegan",
            "indian",
            "Steamed flattened rice tempered with mustard seeds, curry leaves, and crunchy roasted peanuts.",
            15,
            "https://images.unsplash.com/photo-1626074353765-517a681e40be?auto=format&fit=crop&w=800&q=80",
            "nuts",
            "1. Rinse poha in a colander under running water and drain thoroughly.\n2. Heat oil in a pan, roast peanuts until golden, then add mustard seeds and sliced onions.\n3. Stir in turmeric, salt, and drained poha; toss gently to combine.\n4. Cover and steam on low for 3 minutes before finishing with lemon juice.",
            [("Poha (Flattened Rice)", 1.0), ("Peanuts (Roasted)", 1.0), ("Onion", 0.5), ("Olive Oil", 0.5)],
        ),
        (
            "Avocado & Poached Egg Toast",
            "breakfast",
            "non-vegetarian",
            "fusion",
            "Ripe mashed Hass avocado layered over sourdough toast, crowned with a tender poached egg.",
            10,
            "https://images.unsplash.com/photo-1541519227354-08fa5d50c44d?auto=format&fit=crop&w=800&q=80",
            "eggs,gluten",
            "1. Toast sourdough slices until deep golden and crisp.\n2. Scoop and gently mash avocado with sea salt and a squeeze of lemon.\n3. Poach fresh egg in simmering water for 3 minutes until white is set.\n4. Spread avocado generously over toast, top with poached egg, and drizzle olive oil.",
            [("Hass Avocado", 0.5), ("Eggs (Large)", 1.0), ("Sourdough Bread", 1.0), ("Olive Oil", 0.3)],
        ),
        (
            "PB Banana Protein Smoothie",
            "breakfast",
            "vegan",
            "international",
            "Thick, velvety blend of ripe banana, roasted peanut butter, rolled oats, and chia seeds.",
            5,
            "https://images.unsplash.com/photo-1553530666-ba11a7da3888?auto=format&fit=crop&w=800&q=80",
            "nuts,gluten",
            "1. Add peeled ripe banana, rolled oats, and peanut butter to a blender.\n2. Add chia seeds and 1 cup of chilled water or plant milk.\n3. Blend on high speed for 60 seconds until completely smooth.\n4. Pour into a tall glass and sprinkle extra chia seeds on top.",
            [("Banana", 1.0), ("Peanut Butter", 1.0), ("Rolled Oats", 0.5), ("Chia Seeds", 1.0)],
        ),
        (
            "Greek Yogurt Berry Crunch",
            "breakfast",
            "vegetarian",
            "international",
            "Velvety strained Greek yogurt paired with antioxidant wild berries and organic chia seeds.",
            5,
            "https://images.unsplash.com/photo-1488477181946-6428a0291777?auto=format&fit=crop&w=800&q=80",
            "dairy",
            "1. Spoon chilled Greek yogurt into a shallow ceramic bowl.\n2. Rinse fresh mixed berries and arrange across the surface.\n3. Scatter chia seeds evenly for a delicate crunch.\n4. Serve immediately.",
            [("Greek Yogurt", 1.0), ("Mixed Berries", 1.0), ("Chia Seeds", 1.0)],
        ),
        (
            "Masala Omelette with Brown Bread",
            "breakfast",
            "non-vegetarian",
            "indian",
            "Farm eggs whisked with diced onions, tomatoes, green coriander, and griddled brown toast.",
            10,
            "https://images.unsplash.com/photo-1510693206972-df098062cb71?auto=format&fit=crop&w=800&q=80",
            "eggs,gluten,dairy",
            "1. Whisk eggs vigorously with chopped onions, tomatoes, and salt.\n2. Heat desi ghee in a wide frying pan over medium flame.\n3. Pour egg mixture and tilt pan to distribute evenly; cook 2 minutes per side.\n4. Serve piping hot with toasted brown bread.",
            [("Eggs (Large)", 1.0), ("Onion", 0.5), ("Tomato", 0.5), ("Brown Bread", 1.0), ("Pure Desi Ghee", 0.5)],
        ),
        # --- LUNCH (8 distinct recipes) ---
        (
            "Dal Tadka with Steamed Rice",
            "lunch",
            "vegan",
            "indian",
            "Slow-simmered yellow moong dal tempered with garlic, roasted cumin, and basmati rice.",
            25,
            "https://images.unsplash.com/photo-1546833999-b9f581a1996d?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Pressure cook moong dal with water, salt, and turmeric until creamy.\n2. In a small pan, heat olive oil and sizzle garlic, ginger, and cumin seeds until aromatic.\n3. Add diced tomatoes and sauté until oil separates; pour tadka over the dal.\n4. Serve alongside freshly steamed basmati rice.",
            [("Yellow Moong Dal", 1.0), ("Basmati Rice", 1.0), ("Garlic & Ginger", 1.0), ("Tomato", 0.5), ("Olive Oil", 0.8)],
        ),
        (
            "Grilled Herb Chicken & Quinoa",
            "lunch",
            "non-vegetarian",
            "international",
            "Rosemary-garlic marinated chicken breast paired with fluffy Andean quinoa and broccoli.",
            25,
            "https://images.unsplash.com/photo-1543339308-43e59d6b73a6?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Season chicken breast with olive oil, minced garlic, sea salt, and herbs.\n2. Sear in a hot grill pan for 6-7 minutes per side until deeply caramelized.\n3. Simmer quinoa in salted water (1:2 ratio) for 15 minutes until tender and fluffy.\n4. Steam broccoli florets for 4 minutes and plate alongside sliced chicken.",
            [("Chicken Breast", 1.0), ("Quinoa", 1.0), ("Broccoli", 1.0), ("Olive Oil", 0.8)],
        ),
        (
            "Punjabi Rajma with Steamed Rice",
            "lunch",
            "vegan",
            "indian",
            "Tender red kidney beans braised in a slow-reduced onion, ginger, and ripe tomato reduction.",
            35,
            "https://images.unsplash.com/photo-1585937421612-70a008356fbe?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Boil pre-soaked rajma until tender and soft to the touch.\n2. Sauté minced onions in olive oil until deep golden brown, then add garlic-ginger paste.\n3. Add pureed tomatoes and simmer until rich and glossy; stir in cooked beans with broth.\n4. Mash a few beans to thicken gravy, simmer 10 minutes, and serve with hot rice.",
            [("Rajma (Kidney Beans)", 1.0), ("Basmati Rice", 1.0), ("Onion", 1.0), ("Tomato", 1.0), ("Garlic & Ginger", 1.0), ("Olive Oil", 0.8)],
        ),
        (
            "Palak Paneer with Wheat Roti",
            "lunch",
            "vegetarian",
            "indian",
            "Velvety blanched spinach puree folded with fresh paneer cubes and warm whole wheat rotis.",
            25,
            "https://images.unsplash.com/photo-1601050690597-df0568f70950?auto=format&fit=crop&w=800&q=80",
            "dairy,gluten",
            "1. Blanch spinach leaves in boiling water for 2 minutes, then plunge into ice water and puree.\n2. Warm desi ghee in a pan, sauté ginger and garlic until golden.\n3. Pour in spinach puree, season with salt and garam masala, and simmer gently.\n4. Fold in cubed paneer for 3 minutes and serve with freshly rolled rotis.",
            [("Paneer (Cottage Cheese)", 1.0), ("Spinach (Palak)", 1.0), ("Whole Wheat Atta (Roti)", 1.0), ("Garlic & Ginger", 0.5), ("Pure Desi Ghee", 0.5)],
        ),
        (
            "Mediterranean Chickpea Bowl",
            "lunch",
            "vegan",
            "international",
            "Sun-kissed chickpeas, crunchy bell peppers, garden tomatoes, and extra virgin olive oil.",
            15,
            "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Rinse boiled chickpeas and place into a wide ceramic bowl.\n2. Dice bell peppers, tomatoes, and red onions into uniform bite-sized pieces.\n3. Whisk olive oil with lemon juice, salt, and oregano in a ramekin.\n4. Toss vegetables and chickpeas with dressing; chill slightly before serving.",
            [("Chole (Chickpeas)", 1.0), ("Bell Pepper / Capsicum", 1.0), ("Tomato", 0.5), ("Onion", 0.5), ("Olive Oil", 1.0)],
        ),
        (
            "Pan-Seared Salmon with Brown Rice",
            "lunch",
            "non-vegetarian",
            "international",
            "Crispy skin wild salmon with lemon garlic essence served over nutty steamed brown rice.",
            20,
            "https://images.unsplash.com/photo-1467003909585-2f8a72700288?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Pat salmon fillet dry with paper towels; season skin and flesh with salt.\n2. Heat olive oil in a heavy stainless steel skillet over medium-high heat.\n3. Place salmon skin-side down and press gently; sear 4 minutes until crisp, then flip for 2 minutes.\n4. Rest fish for 2 minutes and serve over warm brown rice with fresh lemon.",
            [("Salmon Fillet", 1.0), ("Brown Rice", 1.0), ("Garlic & Ginger", 0.5), ("Olive Oil", 0.8)],
        ),
        (
            "Crispy Tofu & Bell Pepper Stir-Fry",
            "lunch",
            "vegan",
            "fusion",
            "Firm organic tofu cubes wok-charred with sweet bell peppers, ginger, and brown rice.",
            20,
            "https://images.unsplash.com/photo-1546069901-ba9599a7e63c?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Press tofu to remove excess moisture and cut into 1-inch cubes.\n2. Sear tofu cubes in a smoking hot wok with olive oil until golden on all sides.\n3. Toss in sliced bell peppers, minced garlic, and ginger; stir-fry over high heat for 3 minutes.\n4. Serve immediately over steamed brown rice.",
            [("Tofu (Firm)", 1.0), ("Bell Pepper / Capsicum", 1.0), ("Garlic & Ginger", 1.0), ("Olive Oil", 0.8), ("Brown Rice", 0.8)],
        ),
        (
            "Chicken Tikka Rice Bowl",
            "lunch",
            "non-vegetarian",
            "fusion",
            "Clay-oven spiced roasted chicken fillets served with basmati rice and cooling yogurt dip.",
            30,
            "https://images.unsplash.com/photo-1599488615731-7e5c2823ff28?auto=format&fit=crop&w=800&q=80",
            "dairy",
            "1. Marinate chicken cubes in curd, ginger-garlic paste, and spices for 20 minutes.\n2. Thread onto skewers or place on a baking sheet; roast at 200°C for 15 minutes.\n3. Rest chicken under foil to preserve juices.\n4. Assemble bowl with steamed basmati rice, roasted chicken, and a spoonful of cold curd.",
            [("Chicken Breast", 1.0), ("Basmati Rice", 1.0), ("Curd / Yogurt", 0.5), ("Garlic & Ginger", 0.5), ("Olive Oil", 0.5)],
        ),
        # --- DINNER (8 distinct recipes) ---
        (
            "Comforting Moong Khichdi & Curd",
            "dinner",
            "vegetarian",
            "indian",
            "A restorative, gentle pot of yellow moong lentils, fragrant rice, desi ghee, and fresh curd.",
            20,
            "https://images.unsplash.com/photo-1631452180519-c014fe946bc7?auto=format&fit=crop&w=800&q=80",
            "dairy",
            "1. Wash equal parts moong dal and rice together in cold water.\n2. In a pressure cooker, warm desi ghee with a pinch of cumin and turmeric.\n3. Add rice, lentils, and 3.5 cups of water; cook on medium for 3 whistles.\n4. Let steam release naturally, stir until creamy, and serve with set curd.",
            [("Yellow Moong Dal", 0.8), ("Basmati Rice", 0.8), ("Pure Desi Ghee", 0.8), ("Curd / Yogurt", 1.0)],
        ),
        (
            "Grilled Chicken & Steamed Broccoli",
            "dinner",
            "non-vegetarian",
            "international",
            "Lean herb chicken breast char-grilled and paired with crisp steamed garden broccoli florets.",
            20,
            "https://images.unsplash.com/photo-1532550907401-a500c9a57435?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Rub chicken breast with olive oil, garlic paste, salt, and cracked pepper.\n2. Grill in a ridged skillet for 6 minutes per side until thermometer reaches 74°C.\n3. Steam broccoli in a perforated basket for 3.5 minutes until bright emerald and crisp.\n4. Slice chicken against the grain and arrange with broccoli.",
            [("Chicken Breast", 1.0), ("Broccoli", 1.0), ("Olive Oil", 0.6), ("Garlic & Ginger", 0.5)],
        ),
        (
            "Soya Chunks Masala with Roti",
            "dinner",
            "vegan",
            "indian",
            "Dense plant protein soya chunks simmered in a rich tomato-onion reduction with warm flatbread.",
            25,
            "https://images.unsplash.com/photo-1546833998-877b37c2e5c6?auto=format&fit=crop&w=800&q=80",
            "gluten",
            "1. Boil soya chunks in salted water for 5 minutes; drain and squeeze out moisture.\n2. Sauté onions in olive oil until caramelized; add garlic and tomato puree.\n3. Add soya chunks and simmer with 1/2 cup water for 8 minutes to absorb spices.\n4. Roll and puff whole wheat rotis on a cast-iron tawa and serve together.",
            [("Soya Chunks", 1.0), ("Whole Wheat Atta (Roti)", 1.0), ("Onion", 0.8), ("Tomato", 0.8), ("Olive Oil", 0.6)],
        ),
        (
            "Tomato Herb Penne Pasta",
            "dinner",
            "vegetarian",
            "international",
            "Bronze-cut penne tossed in slow-simmered vine tomato concassé, garlic, and aged cheddar.",
            20,
            "https://images.unsplash.com/photo-1551183053-bf91a1d81141?auto=format&fit=crop&w=800&q=80",
            "gluten,dairy",
            "1. Cook penne pasta in rolling salted water until al dente; reserve 1/4 cup pasta water.\n2. In a saucepan, simmer finely chopped vine tomatoes with olive oil and garlic for 10 minutes.\n3. Toss pasta directly into sauce with reserved water to create a glossy glaze.\n4. Plate in a warm bowl and grate sharp cheddar cheese over the top.",
            [("Penne Pasta", 1.0), ("Tomato", 1.5), ("Garlic & Ginger", 0.5), ("Olive Oil", 0.8), ("Cheddar Cheese", 0.5)],
        ),
        (
            "Paneer Capsicum Kadai",
            "dinner",
            "vegetarian",
            "indian",
            "Smoky wok-charred bell peppers and cottage cheese cubes simmered with whole wheat rotis.",
            20,
            "https://images.unsplash.com/photo-1631452180539-96aca7d4861e?auto=format&fit=crop&w=800&q=80",
            "dairy,gluten",
            "1. Heat desi ghee in a heavy kadai and flash-fry cubed bell peppers and onions for 2 minutes.\n2. Add pureed tomatoes, coriander seeds, and spices; simmer until fragrant.\n3. Gently fold in fresh paneer cubes and let them absorb gravy on low heat.\n4. Serve piping hot with freshly prepared whole wheat rotis.",
            [("Paneer (Cottage Cheese)", 1.0), ("Bell Pepper / Capsicum", 1.0), ("Onion", 0.5), ("Tomato", 0.5), ("Whole Wheat Atta (Roti)", 1.0), ("Pure Desi Ghee", 0.5)],
        ),
        (
            "Baked Lemon Salmon with Potatoes",
            "dinner",
            "non-vegetarian",
            "international",
            "Oven-roasted wild salmon fillet infused with thyme, alongside golden garlic baby potatoes.",
            25,
            "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Par-boil potatoes, halve them, and toss with olive oil, salt, and garlic.\n2. Roast potatoes on a baking sheet at 200°C for 15 minutes.\n3. Place salmon fillet on the same sheet, drizzle with lemon and herbs, and bake 10 minutes.\n4. Plate salmon alongside crispy golden potatoes with lemon wedges.",
            [("Salmon Fillet", 1.0), ("Potato", 1.0), ("Garlic & Ginger", 0.5), ("Olive Oil", 0.8)],
        ),
        (
            "Mixed Lentil Soup with Garlic Toast",
            "dinner",
            "vegan",
            "international",
            "Earthy yellow lentil broth steeped with garden herbs, paired with crunchy sourdough toast.",
            25,
            "https://images.unsplash.com/photo-1547592166-23ac45744acd?auto=format&fit=crop&w=800&q=80",
            "gluten",
            "1. Cook yellow moong dal with water, garlic, and ginger until completely softened.\n2. Blend half the soup for silky body while leaving half with texture.\n3. Sauté diced tomatoes in olive oil and stir into soup; simmer 5 minutes.\n4. Rub toasted sourdough with a garlic clove and serve alongside steaming soup.",
            [("Yellow Moong Dal", 1.0), ("Tomato", 0.5), ("Garlic & Ginger", 0.5), ("Sourdough Bread", 1.0), ("Olive Oil", 0.5)],
        ),
        (
            "Mexican Black Bean & Rice Bowl",
            "dinner",
            "vegan",
            "fusion",
            "Seasoned kidney beans, roasted sweet peppers, brown rice, and ripe Hass avocado slices.",
            20,
            "https://images.unsplash.com/photo-1540420773420-3366772f4999?auto=format&fit=crop&w=800&q=80",
            "",
            "1. Warm cooked kidney beans with cumin, chili powder, and olive oil in a skillet.\n2. Sauté bell pepper strips until slightly charred around edges.\n3. Scoop warm brown rice into the base of a wide shallow bowl.\n4. Top with spiced beans, charred peppers, and freshly fanned avocado slices.",
            [("Rajma (Kidney Beans)", 0.8), ("Brown Rice", 0.8), ("Bell Pepper / Capsicum", 0.5), ("Hass Avocado", 0.5), ("Olive Oil", 0.5)],
        ),
    ]

    for name, m_type, diet, cuisine, desc, prep, img, allergens, instr, ing_links in meals_catalog:
        cursor.execute(
            """
            INSERT INTO meals (user_id, name, meal_type, dietary_category, cuisine_type, description, prep_time_mins, image_url, allergens, instructions)
            VALUES (NULL, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
            (name, m_type, diet, cuisine, desc, prep, img, allergens, instr),
        )
        meal_id = cursor.lastrowid

        for ing_name, qty in ing_links:
            if ing_name in ing_id_map:
                cursor.execute(
                    """
                    INSERT INTO meal_ingredients (meal_id, ingredient_id, quantity)
                    VALUES (%s, %s, %s)
                """,
                    (meal_id, ing_id_map[ing_name], qty),
                )

    # 4. Pre-fill John Doe's current week plan with 7 completely unique meals per slot
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    monday_str = monday.isoformat()

    days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    cursor.execute("SELECT id, meal_type FROM meals WHERE user_id IS NULL")
    all_seeded_meals = cursor.fetchall()
    b_meals = [m["id"] for m in all_seeded_meals if m["meal_type"] == "breakfast"]
    l_meals = [m["id"] for m in all_seeded_meals if m["meal_type"] == "lunch"]
    d_meals = [m["id"] for m in all_seeded_meals if m["meal_type"] == "dinner"]

    for i, d in enumerate(days):
        cursor.execute(
            """
            INSERT INTO weekly_plans (user_id, week_start, day_name, meal_type, meal_id)
            VALUES (%s, %s, %s, 'breakfast', %s), (%s, %s, %s, 'lunch', %s), (%s, %s, %s, 'dinner', %s)
        """,
            (
                demo_user_id,
                monday_str,
                d,
                b_meals[i % len(b_meals)],
                demo_user_id,
                monday_str,
                d,
                l_meals[i % len(l_meals)],
                demo_user_id,
                monday_str,
                d,
                d_meals[i % len(d_meals)],
            ),
        )

    print("Seeded 24 uniquely photographed meals and John Doe weekly plan.")
    conn.close()


if __name__ == "__main__":
    seed()
