# WeeklyBite — Precision Culinary Planning & Nutrition

**A full-stack culinary meal planner, provisions tracker, and metabolic health companion** built with Python, **Streamlit + Shadcn UI (`streamlit-shadcn-ui`)**, and **MySQL 8.0**. Styled strictly following `/impeccable` design principles with a crisp zinc aesthetic, high contrast, clean typography, and zero visual clutter.

---

## Key Features

| Section | Feature | Description |
|---|---|---|
| **📅 Weekly Menu** | **7-Day Menu Cadence** | Plan Breakfast, Lunch, and Dinner with live daily calorie counts, macro split (Protein/Carbs/Fat), and day-by-day energy tracking. |
| **✨ Smart Auto-Balance** | **High-Variety Target Solver** | Knapsack-inspired algorithm that fills your entire week to match your target calorie baseline (TDEE ±5%) while guaranteeing **7 distinct, non-repeating meals** for Breakfast, Lunch, and Dinner. |
| **🧺 Kitchen Pantry** | **"Cook with What I Have"** | Interactive pantry inventory where you check off ingredients you already have at home. These are **automatically deducted** from your grocery shopping checklist with live cost savings tracked. |
| **🔍 Allergen & Diet Filters** | **Exclusion Toggles** | Live filtering for **Dairy-Free**, **Gluten-Free**, **Nut-Free**, and **Egg-Free** meals, plus Dietary (Veg/Non-Veg/Vegan) and Cuisine (Indian/Fusion/International). |
| **🍳 Kitchen Cook Mode** | **Live Guidance & Timer** | View ingredients checklist, step-by-step cooking instructions, allergen warnings, and an **interactive kitchen countdown timer** with presets and quick adjustments. |
| **📋 Fridge-Ready Menu** | **Printable Kitchen Schedule** | Clean, high-contrast editorial weekly table designed for printing or posting to a home refrigerator door. |
| **🛒 Provisions & Budget** | **Smart Grocery List** | Categorized provisions list with unit quantities, pantry deduction badges, total shopping cost, budget progress meter, and `.txt` export. |
| **📖 Recipe Catalog** | **Catalog & Custom Meal Creator** | Browse 24 curated recipes or create your own custom dishes with ingredient quantities, saved permanently to MySQL. |
| **🌿 Wellness & Goals** | **Hydration & Mindful Habits** | Daily water tracker (up to 8 glasses/day), mindful habits checkboxes, and personal BMR/TDEE calculator using the clinical Mifflin-St Jeor equation. |
| **🔐 Accounts** | **Multi-User Auth** | Salted cryptographic password hashing (`PBKDF2-HMAC-SHA256`) with isolated user sessions. Default demo user: **John Doe** (`demo` / `password123`). |

---

## Tech Stack

* **Frontend & Framework:** Streamlit, `streamlit-shadcn-ui` (Zinc design tokens, clean cards, badges, and controls)
* **Backend Database:** Local MySQL Server 8.0 via `pymysql`
* **Security:** `hashlib.pbkdf2_hmac` with random 16-byte hex salts and constant-time digest verification
* **Algorithms:** Clinical Mifflin-St Jeor TDEE formula & variety-guaranteed randomized knapsack balancing solver

---

## Quick Start

### 1. Install Dependencies

```powershell
python -m pip install -r requirements.txt
```

### 2. Configure Database

Ensure local MySQL is running. Credentials in [.env](file:///.env):

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=1501
DB_NAME=weeklybite
```

### 3. Initialize & Seed Database (If not already seeded)

```powershell
python seed_db.py
```

### 4. Launch the App

```powershell
python -m streamlit run app.py --server.port 8501
```

Access the application in your browser at: **`http://localhost:8501`**
Demo account: Username `demo`, Password `password123` (or click **Quick Sign In as John Doe**).
