"""
WeeklyBite - a simple weekly meal planner.

Tech: Streamlit (UI) + Supabase/PostgreSQL (storage).
Single user (id = 1), no login screen. Shows the current week.

Run:  streamlit run app.py
"""
import os
import random
from collections import OrderedDict
from datetime import date, datetime, timedelta

import streamlit as st
from dotenv import load_dotenv
from supabase import create_client

load_dotenv()


# ------------------------------------------------------------------
#  Constants
# ------------------------------------------------------------------
USER_ID = 1

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday",
        "Friday", "Saturday", "Sunday"]
MEAL_TYPES = ["breakfast", "lunch", "dinner"]
MEAL_LABEL = {"breakfast": "Breakfast", "lunch": "Lunch", "dinner": "Dinner"}

DIETARY = ["vegetarian", "non-vegetarian", "vegan"]
CUISINES = ["indian", "fusion", "international"]
DIETARY_LABEL = {"vegetarian": "Vegetarian",
                 "non-vegetarian": "Non-Vegetarian", "vegan": "Vegan"}
CUISINE_LABEL = {"indian": "Indian", "fusion": "Fusion",
                 "international": "International"}

# Multipliers for the TDEE calculation
ACTIVITY_FACTOR = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}
ACTIVITY_LABEL = {
    "sedentary": "Sedentary",
    "light": "Lightly active",
    "moderate": "Moderately active",
    "active": "Very active",
    "very_active": "Extra active",
}


def monday_of_this_week():
    """Return the Monday of the current week."""
    return date.today() - timedelta(days=date.today().weekday())


# ------------------------------------------------------------------
#  Database layer
# ------------------------------------------------------------------
@st.cache_resource
def get_db():
    """Single shared Supabase client (created once)."""
    return create_client(os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_KEY"))


def load_catalog():
    """Fetch meals, ingredients, and the meal-ingredient links."""
    db = get_db()
    meals = db.table("meals").select("*").order("name").execute().data or []
    ingredients = db.table("ingredients").select("*").execute().data or []
    links = (db.table("meal_ingredients")
             .select("meal_id,ingredient_id,quantity").execute().data or [])
    return meals, ingredients, links


def load_profile():
    """Fetch the single user's profile (returns {} if missing)."""
    try:
        return get_db().table("users").select("*").eq("id", USER_ID).single().execute().data
    except Exception:
        return {}


def load_plan(week_start):
    """Return {day: {meal_type: meal_id or None}} for the given week."""
    plan = {d: {mt: None for mt in MEAL_TYPES} for d in DAYS}
    try:
        rows = (get_db().table("weekly_plans")
                .select("day_name,meal_type,meal_id")
                .eq("user_id", USER_ID)
                .eq("week_start", week_start.isoformat())
                .execute().data)
        for r in rows:
            if r["meal_type"] in plan.get(r["day_name"], {}):
                plan[r["day_name"]][r["meal_type"]] = r["meal_id"]
    except Exception as e:
        st.warning(f"Could not load plan: {e}")
    return plan


def save_plan(plan, week_start):
    """Replace the stored plan for the given week with `plan`."""
    db = get_db()
    ws = week_start.isoformat()
    db.table("weekly_plans").delete().eq("user_id", USER_ID).eq("week_start", ws).execute()
    rows = [{"user_id": USER_ID, "week_start": ws, "day_name": d,
             "meal_type": mt, "meal_id": plan[d][mt]}
            for d in DAYS for mt in MEAL_TYPES if plan[d][mt] is not None]
    if rows:
        db.table("weekly_plans").insert(rows).execute()


def save_profile(age, height, weight, gender, activity):
    get_db().table("users").update({
        "age": age, "height_cm": height, "weight_kg": weight,
        "gender": gender, "activity_level": activity,
        "updated_at": datetime.now().isoformat(),
    }).eq("id", USER_ID).execute()


# ------------------------------------------------------------------
#  Computed data (nutrition + grocery list)
# ------------------------------------------------------------------
def compute_nutrition(ingredients, links):
    """Per-meal nutrition and ingredient lists, summed from per-unit values."""
    ing_by_id = {i["id"]: i for i in ingredients}
    nutrition = {}
    for link in links:
        ing = ing_by_id.get(link["ingredient_id"])
        if not ing:
            continue
        row = nutrition.setdefault(
            link["meal_id"],
            {"calories": 0, "protein": 0, "carbs": 0, "fat": 0, "items": []},
        )
        qty = link["quantity"]
        row["calories"] += qty * ing["calories_per_unit"]
        row["protein"] += qty * ing["protein_per_unit"]
        row["carbs"] += qty * ing["carbs_per_unit"]
        row["fat"] += qty * ing["fat_per_unit"]
        row["items"].append({
            "name": ing["name"], "qty": qty, "unit": ing["unit"],
            "category": ing["category"],
            "cost": qty * (ing.get("unit_cost") or 0),
        })
    return nutrition


def build_grocery_list(plan, nutrition):
    """De-duplicate ingredients across the whole week, grouped by id."""
    merged = {}
    for day in DAYS:
        for mt in MEAL_TYPES:
            meal_id = plan[day][mt]
            if not meal_id:
                continue
            for item in nutrition.get(meal_id, {}).get("items", []):
                row = merged.setdefault(
                    item["name"].lower(),
                    {"name": item["name"], "unit": item["unit"], "qty": 0.0,
                     "category": item["category"], "cost": 0.0},
                )
                row["qty"] += item["qty"]
                row["cost"] += item["cost"]
    return list(merged.values())


def filtered_ids(meals, meal_type, dietary, cuisine):
    """Meal ids that match the active filters for a given slot."""
    return [m["id"] for m in meals
            if m["meal_type"] == meal_type
            and m["dietary_category"] in dietary
            and m["cuisine_type"] in cuisine]


# ------------------------------------------------------------------
#  Small UI helpers
# ------------------------------------------------------------------
def calc_tdee(gender, weight, height, age, activity):
    """Mifflin-St Jeor BMR, multiplied by an activity factor."""
    base = 10 * weight + 6.25 * height - 5 * age
    bmr = base + 5 if gender == "male" else base - 161
    return bmr, int(bmr * ACTIVITY_FACTOR[activity])


def fmt_qty(qty):
    """Show whole numbers without a decimal point."""
    return int(qty) if qty == int(qty) else round(qty, 1)


def slot_key(day, mt):
    """Stable session-state key for a day/slot dropdown."""
    return f"{day}_{mt}"


def snapshot_plan():
    """Read the current plan straight from the dropdowns' state."""
    return {d: {mt: st.session_state.get(slot_key(d, mt)) for mt in MEAL_TYPES}
            for d in DAYS}


# ------------------------------------------------------------------
#  Initial data load (once per session)
# ------------------------------------------------------------------
st.set_page_config(page_title="WeeklyBite", page_icon="", layout="wide")

if "meals" not in st.session_state:
    m, ing, lnk = load_catalog()
    st.session_state.meals = m
    st.session_state.ingredients = ing
    st.session_state.links = lnk
    st.session_state.profile = load_profile()

meals = st.session_state.meals
meals_by_id = {m["id"]: m for m in meals}
nutrition = compute_nutrition(st.session_state.ingredients, st.session_state.links)
profile = st.session_state.get("profile") or {}

week_start = monday_of_this_week()

# Load this week's saved plan into the dropdowns once
if not st.session_state.get("plan_loaded"):
    loaded = load_plan(week_start)
    for d in DAYS:
        for mt in MEAL_TYPES:
            st.session_state[slot_key(d, mt)] = loaded[d][mt]
    st.session_state.plan_loaded = True


# ------------------------------------------------------------------
#  Sidebar: profile + filters
# ------------------------------------------------------------------
with st.sidebar:
    st.header("Profile")

    gender = st.selectbox(
        "Gender", ["male", "female"],
        index=["male", "female"].index(profile.get("gender", "male")),
        format_func=str.capitalize)
    age = st.number_input("Age (years)", 5, 120, int(profile.get("age", 25) or 25))
    height = st.number_input("Height (cm)", 80.0, 230.0, float(profile.get("height_cm", 170) or 170))
    weight = st.number_input("Weight (kg)", 20.0, 250.0, float(profile.get("weight_kg", 65) or 65))
    activity = st.selectbox(
        "Activity level", list(ACTIVITY_FACTOR),
        index=list(ACTIVITY_FACTOR).index(profile.get("activity_level", "light"))
        if profile.get("activity_level", "light") in ACTIVITY_FACTOR else 1,
        format_func=lambda k: ACTIVITY_LABEL[k])

    if st.button("Save profile"):
        try:
            save_profile(age, height, weight, gender, activity)
            st.session_state.profile = load_profile()
            st.success("Profile saved.")
        except Exception as e:
            st.error(f"Could not save profile: {e}")

    bmr, tdee = calc_tdee(gender, weight, height, age, activity)
    st.metric("Daily target (TDEE)", f"{tdee} kcal")
    st.caption(f"Basal metabolic rate (BMR): {bmr:.0f} kcal")

    st.divider()
    st.header("Filters")
    dietary = st.multiselect("Dietary", DIETARY, DIETARY, format_func=lambda k: DIETARY_LABEL[k])
    cuisine = st.multiselect("Cuisine", CUISINES, CUISINES, format_func=lambda k: CUISINE_LABEL[k])

    if st.button("Reload data"):
        for k in ("meals", "ingredients", "links", "profile", "plan_loaded"):
            st.session_state.pop(k, None)
        st.rerun()


# ------------------------------------------------------------------
#  Header + actions
# ------------------------------------------------------------------
st.title("WeeklyBite")
st.caption(f"Weekly meal planner - week of {week_start.strftime('%b %d, %Y')}")

# Row 1: randomise
r_scope, r_day, r_btn, _ = st.columns([1.6, 1.6, 1.2, 5])
rand_scope = r_scope.selectbox("Randomise", ["Whole week", "Current day"])
rand_day = r_day.selectbox("Day", DAYS, disabled=(rand_scope == "Whole week"))
if r_btn.button("Randomise", use_container_width=True):
    target_days = DAYS if rand_scope == "Whole week" else [rand_day]
    for d in target_days:
        for mt in MEAL_TYPES:
            pool = filtered_ids(meals, mt, dietary, cuisine)
            if pool:
                st.session_state[slot_key(d, mt)] = random.choice(pool)
    st.rerun()

# Row 2: plan actions
b_save, b_load, b_clear, _ = st.columns([1, 1, 1, 9])
if b_save.button("Save plan", type="primary"):
    try:
        save_plan(snapshot_plan(), week_start)
        st.success("Plan saved.")
    except Exception as e:
        st.error(f"Save failed: {e}")
if b_load.button("Reload plan"):
    loaded = load_plan(week_start)
    for d in DAYS:
        for mt in MEAL_TYPES:
            st.session_state[slot_key(d, mt)] = loaded[d][mt]
    st.rerun()
if b_clear.button("Clear plan"):
    for d in DAYS:
        for mt in MEAL_TYPES:
            st.session_state[slot_key(d, mt)] = None
    st.rerun()


# ------------------------------------------------------------------
#  Weekly meal grid (7 columns x 3 rows)
# ------------------------------------------------------------------
st.subheader("Weekly Meal Plan")

if not meals:
    st.warning("No meals found in the database.")
else:
    # Drop any selection that the current filters hide (keeps dropdowns valid)
    for day in DAYS:
        for mt in MEAL_TYPES:
            key = slot_key(day, mt)
            val = st.session_state.get(key)
            if val is not None and val not in filtered_ids(meals, mt, dietary, cuisine):
                st.session_state[key] = None

    cols = st.columns(7)
    for i, day in enumerate(DAYS):
        with cols[i]:
            with st.container(border=True):
                st.markdown(f"**{day}**")
                st.caption((week_start + timedelta(days=i)).strftime("%b %d"))
                for mt in MEAL_TYPES:
                    options = [None] + filtered_ids(meals, mt, dietary, cuisine)
                    picked = st.selectbox(
                        MEAL_LABEL[mt], options,
                        format_func=lambda mid: "select" if mid is None else meals_by_id[mid]["name"],
                        key=slot_key(day, mt),
                        label_visibility="collapsed")
                    n = nutrition.get(picked, {})
                    # Always show one caption line so every column stays aligned
                    st.caption(f"{n['calories']:.0f} kcal"
                               if picked and n.get("calories") else " ")

# Read the current selections for the summary sections
plan = snapshot_plan()


# ------------------------------------------------------------------
#  Nutrition summary
# ------------------------------------------------------------------
daily_calories = {
    day: sum(nutrition.get(plan[day][mt], {}).get("calories", 0) for mt in MEAL_TYPES)
    for day in DAYS
}

st.divider()
st.subheader("Nutrition Summary")
st.bar_chart(daily_calories, width="stretch")

avg_calories = sum(daily_calories.values()) / 7
col1, col2 = st.columns(2)
col1.metric("Average calories / day", f"{avg_calories:.0f} kcal")
col2.metric("Daily target (TDEE)", f"{tdee} kcal")

# Macro totals (weekly) averaged to per-day, compared to a target split
totals = {"carbs": 0, "protein": 0, "fat": 0}
for day in DAYS:
    for mt in MEAL_TYPES:
        n = nutrition.get(plan[day][mt], {})
        for k in totals:
            totals[k] += n.get(k, 0)
per_day = {k: v / 7 for k, v in totals.items()}
targets = {
    "carbs": tdee * 0.5 / 4,    # 50% of calories from carbs (4 kcal/g)
    "protein": tdee * 0.2 / 4,  # 20% from protein
    "fat": tdee * 0.3 / 9,      # 30% from fat (9 kcal/g)
}

st.write("**Macros per day vs target**")
for k, label in [("carbs", "Carbs"), ("protein", "Protein"), ("fat", "Fat")]:
    value = per_day[k]
    target = targets[k]
    ratio = min(value / target, 1.0) if target else 0
    st.write(f"{label}: **{value:.0f} g** / {target:.0f} g target")
    st.progress(ratio)


# ------------------------------------------------------------------
#  Grocery list
# ------------------------------------------------------------------
st.divider()
st.subheader("Grocery List")

grocery = build_grocery_list(plan, nutrition)

if not grocery:
    st.info("Select meals above to build your grocery list.")
else:
    budget = profile.get("weekly_budget") or 0
    total_cost = sum(g["cost"] for g in grocery)

    col1, col2 = st.columns(2)
    col1.metric("Unique ingredients", len(grocery))
    col2.metric("Estimated weekly cost",
                f"Rs {total_cost:.0f}" + (f" / {budget:.0f}" if budget else ""))
    if budget:
        st.progress(min(total_cost / budget, 1.0) if budget else 0,
                    text="Cost vs weekly budget")

    # Group items by category, sorted within each group
    grouped = OrderedDict()
    for item in sorted(grocery, key=lambda x: (x["category"], x["name"])):
        grouped.setdefault(item["category"], []).append(item)

    lines = []
    for category, items in grouped.items():
        st.markdown(f"**{category.title()}**")
        for it in items:
            st.markdown(f"- [ ] {fmt_qty(it['qty'])} {it['unit']} - {it['name']}")
            lines.append(f"{fmt_qty(it['qty'])} {it['unit']} {it['name']}")

    st.download_button("Download grocery list (.txt)",
                       "\n".join(lines),
                       file_name="weeklybite_grocery_list.txt")
