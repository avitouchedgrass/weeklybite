# WeeklyBite

**Precision culinary planning & nutrition — a full-stack meal planner built with Streamlit and MySQL.**

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-1.50%2B-FF4B4B?style=flat-square&logo=streamlit&logoColor=white)
![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?style=flat-square&logo=mysql&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-22c55e?style=flat-square)

WeeklyBite turns a daily calorie target into a complete seven-day menu. It plans breakfast, lunch and dinner, builds a consolidated grocery list, deducts the ingredients already in your pantry, and walks you through cooking each meal — all inside a dark, zinc-themed Streamlit interface.

---

## Overview

Most meal planners stop at "here is a recipe". WeeklyBite connects the whole week:

1. **Set a health profile** — age, height, weight, activity level and goal produce a clinical BMR/TDEE target.
2. **Generate or hand-pick a menu** — auto-balance fills 21 meal slots with distinct recipes that fit your target and dietary filters.
3. **Shop with a budget** — every recipe is costed from its ingredient quantities; pantry items are deducted automatically.
4. **Cook from the plan** — ingredient checklists, step-by-step instructions and a kitchen countdown timer.
5. **Track the week** — calories, macros, hydration, habits and spending are stored per user in MySQL.

---

## Features

| Area | What it does |
|---|---|
| **🔐 Accounts** | Sign in or register. Passwords are hashed with PBKDF2-HMAC-SHA256 and a random per-user salt. Sessions are isolated per user. |
| **📅 Weekly Planner** | A 7-day × 3-meal board with live calories and protein per day, week navigation (previous / current / next), manual meal selection, weekly energy chart, and save/clear controls. |
| **✨ Auto-Balance Week** | Fills all 21 slots with seven distinct breakfasts, lunches and dinners chosen to hit your calorie target, respecting diet, cuisine and allergen filters. |
| **🍳 Cook Mode** | Recipe header with diet/cuisine/prep/calorie badges, allergen warning, ingredient checklist with pantry flags, numbered instructions and a countdown timer initialised to the prep time, with ±1 / ±5 minute adjustments and an audible chime. |
| **🧺 Kitchen Pantry** | Tick off the ingredients you already own across six grocery categories. Pantry items are excluded from shopping totals and savings are shown. |
| **🛒 Provisions & Budget** | Consolidates every ingredient across the week into one quantity-aware shopping list, grouped by category, with total cost, pantry savings, budget progress bar and a `.txt` export. |
| **📋 Fridge Menu** | A high-contrast, landscape weekly schedule designed for printing, with a print button and an `.html` download. |
| **📖 Recipe Compendium** | Browse and search 24 seeded recipes with macros and prep time, or create a custom recipe with your own ingredient quantities. Custom recipes are saved to MySQL and appear in the planner immediately. |
| **🌿 Wellness & Health** | Hydration tracker (up to 16 glasses), daily habit checkboxes, BMR/TDEE breakdown, profile editor and weekly budget setting. |
| **🎨 Interface** | Custom zinc dark theme (`#09090b`), editorial typography, badge system and zero-clutter layouts on top of `streamlit-shadcn-ui`. |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| UI / Framework | [Streamlit](https://streamlit.io) 1.50+, `streamlit-shadcn-ui` 1.4+ |
| Charts & tables | `pandas`, Streamlit primitives |
| Database | MySQL 8.0 (InnoDB, `utf8mb4`) |
| DB driver | `pymysql` with `DictCursor` |
| Configuration | `python-dotenv` |
| Security | `hashlib.pbkdf2_hmac` (100,000 iterations), `secrets.compare_digest`, parameterised SQL |
| Client-side extras | Injected HTML/CSS/JS for the print view and cook timer |

---

## Project Structure

```
weeklybite/
├── app.py                  # Streamlit UI: routing, theme, planner, cook mode, pantry,
│                           # provisions, fridge menu, recipes, wellness
├── db.py                   # Data layer: auth, profiles, pantry, plans, auto-balance
├── seed_db.py              # Demo user, 37 ingredients, 24 recipes, sample week plan
├── schema.sql              # Database and table definitions (run once)
├── requirements.txt        # Python dependencies
├── .env.example            # Template for local database credentials
├── .streamlit/config.toml  # Dark theme and server defaults
└── LICENSE                 # MIT
```

---

## Prerequisites

- **Python 3.10 or newer**
- **MySQL 8.0+** (or MariaDB 10.5+) running locally
- The `mysql` command-line client (or MySQL Workbench)
- Git

---

## Getting Started

### 1. Clone the repository

```bash
git clone https://github.com/avitouchedgrass/weeklybite.git
cd weeklybite
```

### 2. Create a virtual environment and install dependencies

```bash
python -m venv .venv
```

Activate it:

```bash
# macOS / Linux
source .venv/bin/activate

# Windows (PowerShell)
.venv\Scripts\Activate.ps1

# Windows (Command Prompt)
.venv\Scripts\activate.bat
```

Then install:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 3. Create the database

The app expects the schema to exist before it starts. Run the included script once:

```bash
mysql -u root -p < schema.sql
```

This creates the `weeklybite` database and all six tables.

> On **Windows PowerShell**, `<` input redirection is not supported. Use `Get-Content schema.sql | mysql -u root -p` instead, or run the script from MySQL Workbench.

To verify:

```bash
mysql -u root -p -e "USE weeklybite; SHOW TABLES;"
```

You should see `ingredients`, `meal_ingredients`, `meals`, `user_pantry`, `users` and `weekly_plans`.

> If `mysql` is not recognised, either add MySQL's `bin` directory to your `PATH` or run the file from MySQL Workbench (`File → Open SQL Script` → execute).

### 4. Configure environment variables

```bash
# macOS / Linux
cp .env.example .env

# Windows (PowerShell)
Copy-Item .env.example .env
```

Open `.env` and set your MySQL password:

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_mysql_password
DB_NAME=weeklybite
```

`.env` is git-ignored — never commit your real credentials.

### 5. Seed the demo data

```bash
python seed_db.py
```

This loads the demo account, 37 ingredients across six categories, 24 recipes and a fully populated current-week plan.

> ⚠️ `seed_db.py` **truncates** the existing tables before inserting. Run it on a fresh or disposable database, not on data you want to keep.

### 6. Run the app

```bash
python -m streamlit run app.py
```

Open **http://localhost:8501** in your browser. The port and dark theme are pre-set in `.streamlit/config.toml`; override the port with `--server.port 8502` if needed.

---

## Demo Account

| Username | Password |
|---|---|
| `demo` | `password123` |

The sign-in screen also has a **⚡ Quick Sign In as John Doe** button. Or choose **Create Account** to register a fresh profile — new users start with an empty plan and default health values.

---

## Using WeeklyBite

| Tab | Guided workflow |
|---|---|
| **Weekly Planner** | Set diet, cuisine and allergen filters at the top, then press **✨ Auto-Balance Week** or choose meals slot by slot. Changes save to MySQL immediately. Use **← Previous / Next Week →** to plan ahead. |
| **Cook Mode** | Pick a day and meal slot to see the recipe, ingredients (pantry-owned items are flagged), instructions and timer. The **Cook \<Day\>** button on the planner jumps straight here. |
| **Kitchen Pantry** | Check everything you already have. The provisions tab recalculates instantly. |
| **Provisions & Budget** | Review the merged shopping list, estimated cost, pantry deductions and remaining budget. Download the checklist as `.txt`. |
| **Fridge Menu** | Print the landscape schedule or download the standalone HTML file. |
| **Recipe Compendium** | Search the catalogue, inspect macros, or add a custom recipe with ingredient quantities. |
| **Wellness & Health** | Log water and habits, then update your health profile to recalculate BMR/TDEE and the calorie target. |

---

## How the Planning Works

### Calorie target

The app uses the clinical **Mifflin-St Jeor** equation:

```
BMR (male)   = 10 × weight(kg) + 6.25 × height(cm) − 5 × age + 5
BMR (female) = 10 × weight(kg) + 6.25 × height(cm) − 5 × age − 161

TDEE         = BMR × activity factor   # 1.2 → 1.9
Target       = max(1200, TDEE + goal delta)
```

Goal deltas are `0` (maintain), `−500` (fat loss) and `+300` (muscle building). A 1,200 kcal floor prevents unsafe targets.

### Auto-balance

1. Recipes are filtered by meal type, dietary category, cuisine and excluded allergens.
2. Calories and macros are computed from each recipe's ingredient quantities, not hard-coded.
3. For each day, the algorithm sorts candidates by how often they have already been used, then by distance from the slot's calorie target (with a small random jitter for variety).
   - Breakfast targets **25%** of the daily goal.
   - Lunch targets **55%** of the remaining calories.
   - Dinner takes the remainder.
4. With at least seven eligible recipes per meal type, the week gets **seven distinct breakfasts, lunches and dinners**. If a filter is too strict, the app falls back to the unfiltered pool for that slot rather than leaving it empty.

The result is a full week within a few hundred calories of target, with no repeated recipe.

### Grocery list

Every planned meal contributes its ingredient quantities. Identical ingredients are merged across the week, costed from `ingredients.unit_cost`, and marked as owned or to-buy based on `user_pantry`. The budget meter compares the to-buy cost against `users.weekly_budget`.

---

## Database Design

The schema lives in [`schema.sql`](schema.sql). Six InnoDB tables with foreign keys and cascading deletes:

| Table | Purpose | Key relationships |
|---|---|---|
| `users` | Account credentials and health profile | Parent of plans, pantry and custom recipes |
| `ingredients` | Nutrition and cost per ingredient unit | Referenced by recipes and pantries |
| `meals` | Recipe catalogue (`user_id NULL` = shared, else custom) | `user_id → users.id` |
| `meal_ingredients` | Quantity of each ingredient in a recipe | `meal_id → meals.id`, `ingredient_id → ingredients.id` |
| `weekly_plans` | One row per user/week/day/meal slot | `user_id → users.id`, `meal_id → meals.id` |
| `user_pantry` | Ingredients a user already owns | `user_id → users.id`, `ingredient_id → ingredients.id` |

`weekly_plans` has a unique key on `(user_id, week_start, day_name, meal_type)`, and `user_pantry` on `(user_id, ingredient_id)`, so a slot or pantry item cannot be duplicated.

---

## Configuration

All configuration is read from `.env` at startup:

| Variable | Default | Description |
|---|---|---|
| `DB_HOST` | `localhost` | MySQL host |
| `DB_PORT` | `3306` | MySQL port |
| `DB_USER` | `root` | MySQL user |
| `DB_PASSWORD` | — | MySQL password (set this) |
| `DB_NAME` | `weeklybite` | Database name created by `schema.sql` |

UI options live in `.streamlit/config.toml`: theme colours, headless mode, port `8501`, CORS/XSRF settings and usage-statistics opt-out.

---

## Security Notes

- Passwords are never stored in plain text: PBKDF2-HMAC-SHA256, 100,000 iterations, random 16-byte hex salt per user, and constant-time digest comparison.
- All SQL uses parameterised queries.
- `.env` and virtual environments are excluded from version control.
- This is a learning/coursework project, not a hardened production service. It has no email verification, password reset, rate limiting or CSRF tokens, and session state is stored in Streamlit's in-memory session.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `Can't connect to MySQL server` / error 2003 | Start the MySQL service and confirm `DB_HOST` / `DB_PORT`. |
| `Access denied for user` / error 1045 | Check `DB_USER` and `DB_PASSWORD` in `.env`. |
| `Unknown database 'weeklybite'` / error 1049 | Run `mysql -u root -p < schema.sql`. |
| `Table 'weeklybite.users' doesn't exist` | The schema was not imported, or `DB_NAME` points elsewhere. |
| `ModuleNotFoundError: streamlit_shadcn_ui` | Activate the virtual environment and reinstall `requirements.txt`. |
| `mysql` is not recognised | Add MySQL's `bin` folder to `PATH`, or use MySQL Workbench. |
| Port 8501 already in use | Run `python -m streamlit run app.py --server.port 8502`. |
| Blank / unstyled cards | Hard-refresh the browser; ensure Streamlit ≥ 1.50 and `streamlit-shadcn-ui` ≥ 1.4. |
| Recipe images do not load | Meal images are remote Unsplash URLs and need an internet connection. |

---

## Limitations & Roadmap

- Ingredient prices are seeded in Indian rupees and are **static estimates**, not live market rates.
- Auto-balance is a greedy heuristic, not a globally optimal solver.
- One plan per user per week; there is no household or shared-plan mode.
- No password reset, email verification or account deletion flow yet.
- Recipe images are hot-linked from Unsplash.

Planned improvements: editable ingredient prices, live currency selection, nutrition goal presets, PDF export, and stronger authentication.

> **Disclaimer:** Nutrition values are approximate and intended for planning and education. They are not medical or dietary advice.

---

## Contributing

1. Fork the repository and create a feature branch.
2. Make your changes and test against a local MySQL instance.
3. Open a pull request describing the change.

Bug reports and feature suggestions are welcome via [GitHub Issues](https://github.com/avitouchedgrass/weeklybite/issues).

---

## License

Released under the [MIT License](LICENSE) © 2026 Avi Sharma.
