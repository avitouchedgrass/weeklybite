import json
import random
import time
from datetime import date, datetime, timedelta
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components
import streamlit_shadcn_ui as ui

import db

# Constants
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MEAL_TYPES = ["breakfast", "lunch", "dinner"]
DIETARY_OPTIONS = ["vegetarian", "non-vegetarian", "vegan"]
CUISINE_OPTIONS = ["indian", "fusion", "international"]
ALLERGEN_OPTIONS = ["dairy", "gluten", "nuts", "egg"]

FITNESS_GOALS = {
    "maintain": {"label": "Weight Maintenance", "delta": 0},
    "loss": {"label": "Fat Loss (−500 kcal/day)", "delta": -500},
    "gain": {"label": "Muscle Building (+300 kcal/day)", "delta": 300},
}

ACTIVITY_FACTORS = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}


def get_current_monday():
    today = date.today()
    return today - timedelta(days=today.weekday())


def format_title(text):
    return text.replace("_", " ").title()


def format_qty(quantity):
    rounded = round(float(quantity), 1)
    return int(rounded) if rounded.is_integer() else rounded


def compute_nutrition(ingredients, links):
    ingredients_by_id = {ing["id"]: ing for ing in ingredients}
    nutrition = {}
    for link in links:
        meal_id = link["meal_id"]
        ing_id = link["ingredient_id"]
        qty = float(link["quantity"])
        ing = ingredients_by_id.get(ing_id)
        if not ing:
            continue
        if meal_id not in nutrition:
            nutrition[meal_id] = {
                "calories": 0.0,
                "protein": 0.0,
                "carbs": 0.0,
                "fat": 0.0,
                "cost": 0.0,
                "items": [],
            }
        unit_cost = float(ing.get("unit_cost") or 0.0)
        nutrition[meal_id]["calories"] += qty * float(ing["calories_per_unit"])
        nutrition[meal_id]["protein"] += qty * float(ing["protein_per_unit"])
        nutrition[meal_id]["carbs"] += qty * float(ing["carbs_per_unit"])
        nutrition[meal_id]["fat"] += qty * float(ing["fat_per_unit"])
        nutrition[meal_id]["cost"] += qty * unit_cost
        nutrition[meal_id]["items"].append({
            "id": ing["id"],
            "name": ing["name"],
            "qty": qty,
            "unit": ing["unit"],
            "category": ing["category"],
            "cost": qty * unit_cost,
        })
    return nutrition


def build_provisions_summary(plan, nutrition, pantry_ids):
    merged = {}
    pantry_set = set(pantry_ids)
    for day in DAYS:
        for meal in MEAL_TYPES:
            meal_id = plan.get(day, {}).get(meal)
            for item in nutrition.get(meal_id, {}).get("items", []):
                ing_id = item["id"]
                if ing_id not in merged:
                    merged[ing_id] = {
                        "id": ing_id,
                        "name": item["name"],
                        "unit": item["unit"],
                        "category": item["category"],
                        "qty": 0.0,
                        "cost": 0.0,
                        "in_pantry": ing_id in pantry_set,
                    }
                merged[ing_id]["qty"] += item["qty"]
                merged[ing_id]["cost"] += item["cost"]
    items_list = list(merged.values())
    total_cost = sum(i["cost"] for i in items_list)
    saved_cost = sum(i["cost"] for i in items_list if i["in_pantry"])
    return {
        "all_items": items_list,
        "items_to_buy": [i for i in items_list if not i["in_pantry"]],
        "total_cost": total_cost,
        "saved_cost": saved_cost,
        "cost_to_buy": total_cost - saved_cost,
    }


def get_eligible_meal_ids(meals, meal_type, dietary_filter, cuisine_filter, excluded_allergens):
    matching = []
    for m in meals:
        if m["meal_type"] != meal_type:
            continue
        if dietary_filter and m["dietary_category"] not in dietary_filter:
            continue
        if cuisine_filter and m["cuisine_type"] not in cuisine_filter:
            continue
        if excluded_allergens:
            m_allergens = [a.strip() for a in (m.get("allergens") or "").split(",") if a.strip()]
            if any(ea in m_allergens for ea in excluded_allergens):
                continue
        matching.append(m["id"])
    return matching


st.set_page_config(
    page_title="WeeklyBite — Precision Culinary Planning",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Dark zinc theme
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,100..900;1,14..32,100..900&display=swap');

    html, body, .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif !important;
        background-color: #09090b !important;
        color: #f4f4f5 !important;
        -webkit-font-smoothing: antialiased;
    }

    #MainMenu, header, footer, [data-testid="stToolbar"] {
        display: none !important;
    }

    .block-container {
        padding: 1.5rem 2rem 4rem !important;
        max-width: 1440px !important;
    }

    h1, h2, h3, h4 {
        color: #fafafa !important;
        letter-spacing: -0.025em !important;
        font-weight: 700 !important;
    }

    /* Primary button */
    button[data-testid="baseButton-primary"] {
        background-color: #fafafa !important;
        color: #09090b !important;
        border: 1px solid #ffffff !important;
        border-radius: 6px !important;
        font-weight: 600 !important;
        font-size: 0.875rem !important;
        letter-spacing: -0.01em !important;
        padding: 0.5rem 1rem !important;
        box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2) !important;
        transition: all 0.15s ease !important;
    }
    button[data-testid="baseButton-primary"] * {
        color: #09090b !important;
        font-weight: 600 !important;
    }
    button[data-testid="baseButton-primary"]:hover {
        background-color: #e4e4e7 !important;
        border-color: #e4e4e7 !important;
        transform: translateY(-1px) !important;
    }

    /* Secondary button */
    button[data-testid="baseButton-secondary"] {
        background-color: #18181b !important;
        color: #e4e4e7 !important;
        border: 1px solid #27272a !important;
        border-radius: 6px !important;
        font-weight: 500 !important;
        font-size: 0.875rem !important;
        padding: 0.5rem 1rem !important;
        transition: all 0.15s ease !important;
    }
    button[data-testid="baseButton-secondary"] * {
        color: #e4e4e7 !important;
    }
    button[data-testid="baseButton-secondary"]:hover {
        background-color: #27272a !important;
        border-color: #3f3f46 !important;
    }
    button[data-testid="baseButton-secondary"]:hover * {
        color: #ffffff !important;
    }
    button[data-testid="baseButton-secondary"]:disabled {
        opacity: 0.5 !important;
        background-color: #121215 !important;
        border-color: #27272a !important;
    }

    /* Tags and dropdowns */
    div[data-baseweb="tag"] {
        background-color: #27272a !important;
        border: 1px solid #3f3f46 !important;
        border-radius: 4px !important;
        padding: 3px 8px !important;
        margin: 2px !important;
    }
    div[data-baseweb="tag"] span,
    div[data-baseweb="tag"] p,
    div[data-baseweb="tag"] div {
        color: #f4f4f5 !important;
        font-size: 0.78rem !important;
        font-weight: 500 !important;
    }
    div[data-baseweb="tag"] svg {
        fill: #a1a1aa !important;
    }

    div[data-baseweb="select"] > div {
        background-color: #18181b !important;
        border: 1px solid #27272a !important;
        border-radius: 6px !important;
        color: #f4f4f5 !important;
        min-height: 38px !important;
    }
    div[data-baseweb="select"]:focus-within > div {
        border-color: #52525b !important;
        box-shadow: 0 0 0 1px #52525b !important;
    }
    div[data-baseweb="select"] input {
        color: #f4f4f5 !important;
    }

    div[data-baseweb="popover"],
    div[data-baseweb="menu"] {
        background-color: #18181b !important;
        border: 1px solid #27272a !important;
        border-radius: 8px !important;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.5) !important;
    }
    div[data-baseweb="menu"] li {
        background-color: #18181b !important;
        color: #e4e4e7 !important;
        padding: 8px 12px !important;
        border-radius: 4px !important;
        font-size: 0.85rem !important;
    }
    div[data-baseweb="menu"] li:hover,
    div[data-baseweb="menu"] li[aria-selected="true"] {
        background-color: #27272a !important;
        color: #ffffff !important;
    }

    /* Inputs */
    div[data-baseweb="input"],
    div[data-baseweb="base-input"] {
        background-color: #18181b !important;
        border: 1px solid #27272a !important;
        border-radius: 6px !important;
    }
    div[data-baseweb="input"]:focus-within {
        border-color: #52525b !important;
    }
    input, textarea {
        color: #f4f4f5 !important;
        background-color: transparent !important;
    }
    input::placeholder, textarea::placeholder {
        color: #71717a !important;
    }
    label[data-testid="stWidgetLabel"] p {
        color: #a1a1aa !important;
        font-size: 0.8rem !important;
        font-weight: 500 !important;
        letter-spacing: 0.01em !important;
    }

    div[data-testid="stVerticalBlockBorderWrapper"] {
        background-color: #121215 !important;
        border: 1px solid #27272a !important;
        border-radius: 10px !important;
        padding: 1.25rem !important;
    }

    /* Cards and badges */
    .wb-card {
        background: #121215;
        border: 1px solid #27272a;
        border-radius: 10px;
        padding: 1.25rem;
        transition: border-color 0.15s ease;
    }
    .wb-card:hover {
        border-color: #3f3f46;
    }

    .wb-badge {
        display: inline-flex;
        align-items: center;
        gap: 5px;
        padding: 3px 8px;
        font-size: 0.72rem;
        font-weight: 500;
        border-radius: 4px;
        letter-spacing: 0.01em;
    }
    .wb-badge-veg    { background: rgba(16, 185, 129, 0.12); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.25); }
    .wb-badge-nonveg { background: rgba(244, 63, 94, 0.12);  color: #fb7185; border: 1px solid rgba(244, 63, 94, 0.25);  }
    .wb-badge-vegan  { background: rgba(139, 92, 246, 0.12); color: #c4b5fd; border: 1px solid rgba(139, 92, 246, 0.25); }
    .wb-badge-zinc   { background: #27272a; color: #d4d4d8; border: 1px solid #3f3f46; }
    .wb-badge-amber  { background: rgba(245, 158, 11, 0.12); color: #fbbf24; border: 1px solid rgba(245, 158, 11, 0.25); }
    .wb-badge-sky    { background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.25); }

    /* Tables */
    .wb-table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.875rem;
    }
    .wb-table th {
        background-color: #18181b;
        color: #71717a;
        font-size: 0.72rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        padding: 10px 14px;
        text-align: left;
        border-bottom: 1px solid #27272a;
    }
    .wb-table td {
        padding: 11px 14px;
        border-bottom: 1px solid #1c1c1e;
        color: #d4d4d8;
    }
    .wb-table tr:hover td {
        background-color: rgba(39, 39, 42, 0.4);
    }

    div[data-testid="stProgress"] > div {
        background-color: #27272a !important;
        border-radius: 9999px !important;
        height: 6px !important;
    }
    div[data-testid="stProgress"] > div > div {
        background-color: #fafafa !important;
        border-radius: 9999px !important;
    }
    div[data-testid="stAlert"] {
        border-radius: 8px !important;
        border: 1px solid #27272a !important;
        background-color: #121215 !important;
    }

    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #09090b; }
    ::-webkit-scrollbar-thumb { background: #27272a; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #3f3f46; }

    @media print {
        @page {
            size: landscape;
            margin: 1.2cm;
        }
        html, body, .stApp {
            background-color: #ffffff !important;
            color: #111827 !important;
        }
        #MainMenu, header, footer, [data-testid="stToolbar"], [data-baseweb="tab-list"], .stButton, button, .no-print {
            display: none !important;
        }
        .block-container {
            padding: 0 !important;
            max-width: 100% !important;
        }
        #fridge-print-area {
            display: block !important;
            background: #ffffff !important;
            color: #111827 !important;
        }
        #fridge-print-area * {
            color: #111827 !important;
        }
        #fridge-print-area table {
            width: 100% !important;
            border-collapse: collapse !important;
        }
        #fridge-print-area th {
            background-color: #f3f4f6 !important;
            color: #111827 !important;
            border: 1px solid #111827 !important;
        }
        #fridge-print-area td {
            border: 1px solid #d1d5db !important;
            color: #111827 !important;
        }
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# Authentication screen
def render_auth_screen():
    _, col, _ = st.columns([1, 1.4, 1])
    with col:
        st.markdown(
            """
            <div style='text-align: center; margin-top: 3.5rem; margin-bottom: 2rem;'>
                <div style='display: inline-flex; align-items: center; gap: 8px; margin-bottom: 6px;'>
                    <span style='font-size: 2rem; font-weight: 800; color: #fafafa; letter-spacing: -0.04em;'>WeeklyBite</span>
                    <span class='wb-badge wb-badge-zinc' style='font-size: 0.7rem;'>PRO</span>
                </div>
                <div style='font-size: 0.875rem; color: #a1a1aa;'>Precision culinary planning & intelligent metabolic nutrition</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        auth_tab = ui.tabs(["Sign In", "Create Account"], key="auth_screen_tabs")

        with st.container(border=True):
            if auth_tab == "Sign In":
                st.markdown("<div style='font-size: 1.1rem; font-weight: 700; color: #fafafa; margin-bottom: 4px;'>Welcome Back</div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 0.8rem; color: #a1a1aa; margin-bottom: 16px;'>Sign in to access your weekly meal plan and kitchen pantry.</div>", unsafe_allow_html=True)

                with st.form("login_form"):
                    identifier = st.text_input("Username or Email", placeholder="demo")
                    password = st.text_input("Password", type="password", placeholder="••••••••")
                    submit_login = st.form_submit_button("Sign In", type="primary", use_container_width=True)

                    if submit_login:
                        if not identifier or not password:
                            st.error("Please enter both username/email and password.")
                        else:
                            user = db.authenticate_user(identifier, password)
                            if user:
                                st.session_state.user = user
                                st.rerun()
                            else:
                                st.error("Invalid credentials. Please verify your login details.")

                st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
                if st.button("⚡ Quick Sign In as John Doe (demo / password123)", use_container_width=True, type="secondary"):
                    user = db.authenticate_user("demo", "password123")
                    if user:
                        st.session_state.user = user
                        st.rerun()

            else:
                st.markdown("<div style='font-size: 1.1rem; font-weight: 700; color: #fafafa; margin-bottom: 4px;'>Create Your Account</div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 0.8rem; color: #a1a1aa; margin-bottom: 16px;'>Set up your profile to start planning high-variety nutritious weeks.</div>", unsafe_allow_html=True)

                with st.form("register_form"):
                    full_name = st.text_input("Full Name", placeholder="e.g. John Doe")
                    reg_user = st.text_input("Username", placeholder="e.g. johndoe")
                    reg_email = st.text_input("Email (Optional)", placeholder="e.g. john@example.com")
                    reg_pwd = st.text_input("Password", type="password", placeholder="At least 4 characters")
                    reg_pwd2 = st.text_input("Confirm Password", type="password")
                    submit_register = st.form_submit_button("Create Account", type="primary", use_container_width=True)

                    if submit_register:
                        if not reg_user or not reg_pwd:
                            st.error("Username and password are required.")
                        elif reg_pwd != reg_pwd2:
                            st.error("Passwords do not match.")
                        elif len(reg_pwd) < 4:
                            st.error("Password must be at least 4 characters.")
                        else:
                            success, result = db.register_user(reg_user, reg_email, reg_pwd, full_name)
                            if success:
                                st.session_state.user = result
                                st.rerun()
                            else:
                                st.error(f"Registration failed: {result}")


# Main application
def render_app():
    user = st.session_state.user
    user_id = user["id"]
    profile = db.get_user_profile(user_id) or user
    meals, ingredients, links = db.load_catalog(user_id)
    meals_by_id = {m["id"]: m for m in meals}
    nutrition = compute_nutrition(ingredients, links)
    pantry_ids = db.get_user_pantry(user_id)

    # Health baseline
    gender = profile.get("gender", "male")
    weight = float(profile.get("weight_kg", 65.0) or 65.0)
    height = float(profile.get("height_cm", 170.0) or 170.0)
    age = int(profile.get("age", 24) or 24)
    activity = profile.get("activity_level", "light")
    fitness_goal = profile.get("fitness_goal", "maintain")
    weekly_budget = float(profile.get("weekly_budget", 2000.0) or 2000.0)
    water_glasses = int(profile.get("water_glasses", 0) or 0)
    habits = profile.get("habits_json") or {}

    bmr = (10 * weight) + (6.25 * height) - (5 * age) + (5 if gender == "male" else -161)
    tdee = int(bmr * ACTIVITY_FACTORS.get(activity, 1.375))
    goal_delta = FITNESS_GOALS.get(fitness_goal, {}).get("delta", 0)
    target_calories = max(1200, tdee + goal_delta)

    # Week state
    if "week_offset" not in st.session_state:
        st.session_state.week_offset = 0
    if "plan_version" not in st.session_state:
        st.session_state.plan_version = 0

    week_start = get_current_monday() + timedelta(weeks=st.session_state.week_offset)
    week_end = week_start + timedelta(days=6)
    week_start_str = week_start.isoformat()

    # Load weekly plan from database
    if (
        "current_plan" not in st.session_state
        or st.session_state.get("current_plan_week") != week_start_str
    ):
        st.session_state.current_plan = db.load_plan(user_id, week_start_str)
        st.session_state.current_plan_week = week_start_str

    def get_ui_plan():
        if (
            "current_plan" not in st.session_state
            or st.session_state.get("current_plan_week") != week_start_str
        ):
            st.session_state.current_plan = db.load_plan(user_id, week_start_str)
            st.session_state.current_plan_week = week_start_str
        return st.session_state.current_plan

    # Header
    p_name = profile.get("full_name") or profile.get("username", "User")
    p_initials = "".join([part[0].upper() for part in p_name.split()[:2]]) or "U"

    top_col1, top_col2, top_col3 = st.columns([3.5, 4.5, 2.5])
    with top_col1:
        st.markdown(
            f"""
            <div style='display: flex; align-items: center; gap: 10px; padding: 4px 0;'>
                <div style='font-size: 1.45rem; font-weight: 800; color: #fafafa; letter-spacing: -0.04em;'>WeeklyBite</div>
                <span class='wb-badge wb-badge-veg'>● Active Plan</span>
            </div>
            <div style='font-size: 0.78rem; color: #71717a;'>Week of {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}</div>
            """,
            unsafe_allow_html=True,
        )

    with top_col2:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        w_prev, w_today, w_next = st.columns([1, 1.2, 1])
        with w_prev:
            if st.button("← Previous", use_container_width=True, type="secondary"):
                st.session_state.week_offset -= 1
                st.session_state.pop("current_plan_week", None)
                st.session_state.pop("current_plan", None)
                st.session_state.plan_version += 1
                st.rerun()
        with w_today:
            if st.button("This Week", use_container_width=True, type="secondary", disabled=(st.session_state.week_offset == 0)):
                st.session_state.week_offset = 0
                st.session_state.pop("current_plan_week", None)
                st.session_state.pop("current_plan", None)
                st.session_state.plan_version += 1
                st.rerun()
        with w_next:
            if st.button("Next Week →", use_container_width=True, type="secondary"):
                st.session_state.week_offset += 1
                st.session_state.pop("current_plan_week", None)
                st.session_state.pop("current_plan", None)
                st.session_state.plan_version += 1
                st.rerun()

    with top_col3:
        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)
        u_col1, u_col2 = st.columns([2, 1])
        with u_col1:
            st.markdown(
                f"""
                <div style='display: flex; align-items: center; gap: 8px; justify-content: flex-end; padding-top: 4px;'>
                    <div style='width: 32px; height: 32px; border-radius: 50%; background: #27272a; border: 1px solid #3f3f46; display: flex; align-items: center; justify-content: center; font-size: 0.8rem; font-weight: 700; color: #fafafa;'>
                        {p_initials}
                    </div>
                    <div style='text-align: left; line-height: 1.1;'>
                        <div style='font-size: 0.82rem; font-weight: 600; color: #fafafa;'>{p_name}</div>
                        <div style='font-size: 0.7rem; color: #71717a;'>{target_calories} kcal/day</div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with u_col2:
            if st.button("Log Out", use_container_width=True, type="secondary"):
                st.session_state.clear()
                st.rerun()

    st.markdown("<div style='height: 12px; border-bottom: 1px solid #27272a; margin-bottom: 16px;'></div>", unsafe_allow_html=True)

    # Navigation tabs
    nav_tab = ui.tabs(
        options=[
            "Weekly Planner",
            "Cook Mode",
            "Kitchen Pantry",
            "Provisions & Budget",
            "Fridge Menu",
            "Recipe Compendium",
            "Wellness & Health",
        ],
        key="main_app_tabs_v2",
    )

    # Weekly Planner tab
    if nav_tab == "Weekly Planner":
        active_plan = get_ui_plan()
        daily_calories = {}
        total_p = total_c = total_f = 0.0
        for day in DAYS:
            d_sum = 0.0
            for meal in MEAL_TYPES:
                mid = active_plan.get(day, {}).get(meal)
                nut = nutrition.get(mid, {})
                d_sum += nut.get("calories", 0.0)
                total_p += nut.get("protein", 0.0)
                total_c += nut.get("carbs", 0.0)
                total_f += nut.get("fat", 0.0)
            daily_calories[day] = d_sum

        avg_daily_cal = sum(daily_calories.values()) / 7.0
        cal_diff = avg_daily_cal - target_calories

        m_col1, m_col2, m_col3, m_col4 = st.columns(4)
        with m_col1:
            ui.metric_card(
                label="Average Daily Intake",
                value=f"{avg_daily_cal:.0f} kcal",
                description=f"Clinical Target: {target_calories} kcal/day",
                delta=f"{cal_diff:+.0f} kcal vs target",
                key="metric_avg_intake",
            )
        with m_col2:
            ui.metric_card(
                label="Daily Protein Average",
                value=f"{total_p / 7.0:.1f} g",
                description="Target: 80 – 120 g/day",
                delta="Optimal Range" if (total_p / 7.0 >= 80) else "Low Intake",
                key="metric_protein_avg",
            )
        with m_col3:
            ui.metric_card(
                label="Macro Split (C / F)",
                value=f"{total_c / 7.0:.0f}g / {total_f / 7.0:.0f}g",
                description="Carbohydrate / Fat Balance",
                key="metric_macros_avg",
            )
        with m_col4:
            ui.metric_card(
                label="Weekly Grocery Allowance",
                value=f"₹ {weekly_budget:.0f}",
                description="Configured in health profile",
                key="metric_grocery_budget",
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        with st.container(border=True):
            f1, f2, f3, f4 = st.columns([2.5, 2.5, 2.5, 2.5])
            with f1:
                selected_diet = st.multiselect(
                    "Dietary Preference",
                    DIETARY_OPTIONS,
                    default=DIETARY_OPTIONS,
                    format_func=format_title,
                )
            with f2:
                selected_cuisine = st.multiselect(
                    "Cuisine Type",
                    CUISINE_OPTIONS,
                    default=CUISINE_OPTIONS,
                    format_func=format_title,
                )
            with f3:
                excluded_allergens = st.multiselect(
                    "Allergen Exclusions",
                    ALLERGEN_OPTIONS,
                    default=[],
                    format_func=lambda a: f"No {a.capitalize()}",
                )
            with f4:
                st.markdown("<div style='height: 27px;'></div>", unsafe_allow_html=True)
                btn_auto = st.button("✨ Auto-Balance Week", type="primary", use_container_width=True)

        if btn_auto:
            with st.spinner("Generating 7 unique balanced meals for your week..."):
                new_plan = db.auto_generate_balanced_plan(
                    user_id=user_id,
                    week_start=week_start_str,
                    target_daily_calories=float(target_calories),
                    dietary_filter=selected_diet,
                    cuisine_filter=selected_cuisine,
                    excluded_allergens=excluded_allergens,
                )
                st.session_state.current_plan = new_plan
                st.session_state.current_plan_week = week_start_str
                st.session_state.plan_version += 1
                db.save_plan(user_id, new_plan, week_start_str)
                st.success("Week auto-balanced! All 7 days populated with distinct meals matching your TDEE target.")
                st.rerun()

        st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
        vh_col1, vh_col2 = st.columns([6, 4])
        with vh_col1:
            st.markdown(
                """
                <div style='font-size: 1.15rem; font-weight: 700; color: #fafafa; display: flex; align-items: center; gap: 8px;'>
                    <span>Weekly Meal Board</span>
                    <span class='wb-badge wb-badge-zinc' style='font-weight: 400;'>7-Day Schedule</span>
                </div>
                """,
                unsafe_allow_html=True,
            )
        with vh_col2:
            act_c1, act_c2 = st.columns([1, 1])
            with act_c1:
                if st.button("💾 Save Plan to DB", type="primary", use_container_width=True):
                    db.save_plan(user_id, st.session_state.current_plan, week_start_str)
                    st.success("Saved to MySQL!")
            with act_c2:
                if st.button("🧹 Clear All Slots", type="secondary", use_container_width=True):
                    empty_plan = {d: {m: None for m in MEAL_TYPES} for d in DAYS}
                    st.session_state.current_plan = empty_plan
                    st.session_state.plan_version += 1
                    db.save_plan(user_id, empty_plan, week_start_str)
                    st.rerun()

        st.markdown("<div style='height: 6px;'></div>", unsafe_allow_html=True)

        # 4x2 day board: Monday to Thursday
        row1_cols = st.columns(4)
        for idx, day in enumerate(DAYS[:4]):
            day_date = week_start + timedelta(days=idx)
            with row1_cols[idx]:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #27272a;'>
                            <span style='font-size: 1.05rem; font-weight: 700; color: #fafafa;'>{day}</span>
                            <span style='font-size: 0.75rem; color: #71717a;'>{day_date.strftime('%b %d')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    day_cals = 0.0
                    day_prot = 0.0

                    for meal in MEAL_TYPES:
                        st.markdown(
                            f"<div style='font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #a1a1aa; margin-top: 10px; margin-bottom: 4px;'>{meal}</div>",
                            unsafe_allow_html=True,
                        )
                        current_meal_id = st.session_state.current_plan.get(day, {}).get(meal)

                        eligible_ids = get_eligible_meal_ids(
                            meals, meal, selected_diet, selected_cuisine, excluded_allergens
                        )
                        options = [None] + eligible_ids

                        if current_meal_id not in options:
                            current_meal_id = None
                            st.session_state.current_plan[day][meal] = None

                        def format_option(mid):
                            if mid is None or mid not in meals_by_id:
                                return "— No Meal Planned —"
                            m = meals_by_id[mid]
                            nut = nutrition.get(mid, {})
                            return f"{m['name']} ({nut.get('calories', 0):.0f} kcal)"

                        slot_key = f"w_slot_{week_start_str}_{day}_{meal}_v{st.session_state.plan_version}"
                        selected_id = st.selectbox(
                            meal,
                            options,
                            index=options.index(current_meal_id),
                            format_func=format_option,
                            key=slot_key,
                            label_visibility="collapsed",
                        )

                        if selected_id != current_meal_id:
                            st.session_state.current_plan[day][meal] = selected_id
                            db.save_plan(user_id, st.session_state.current_plan, week_start_str)
                            st.rerun()

                        if selected_id:
                            m_nut = nutrition.get(selected_id, {})
                            day_cals += m_nut.get("calories", 0.0)
                            day_prot += m_nut.get("protein", 0.0)

                    cal_badge_cls = "wb-badge-veg" if abs(day_cals - target_calories) <= 250 else "wb-badge-amber"
                    st.markdown(
                        f"""
                        <div style='margin-top: 14px; padding-top: 10px; border-top: 1px solid #27272a; display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <span class='wb-badge {cal_badge_cls}'>{day_cals:.0f} kcal</span>
                                <span class='wb-badge wb-badge-zinc'>{day_prot:.0f}g protein</span>
                            </div>
                        </div>
                        <div style='height: 8px;'></div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(f"Cook {day}", key=f"btn_cook_{day}", use_container_width=True, type="secondary"):
                        st.session_state.cook_target_day = day
                        st.session_state.main_app_tabs_v2 = "Cook Mode"
                        st.rerun()

        st.markdown("<div style='height: 10px;'></div>", unsafe_allow_html=True)

        # Friday to Sunday
        row2_cols = st.columns(4)
        for idx, day in enumerate(DAYS[4:], start=4):
            day_date = week_start + timedelta(days=idx)
            with row2_cols[idx - 4]:
                with st.container(border=True):
                    st.markdown(
                        f"""
                        <div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #27272a;'>
                            <span style='font-size: 1.05rem; font-weight: 700; color: #fafafa;'>{day}</span>
                            <span style='font-size: 0.75rem; color: #71717a;'>{day_date.strftime('%b %d')}</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

                    day_cals = 0.0
                    day_prot = 0.0

                    for meal in MEAL_TYPES:
                        st.markdown(
                            f"<div style='font-size: 0.68rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: #a1a1aa; margin-top: 10px; margin-bottom: 4px;'>{meal}</div>",
                            unsafe_allow_html=True,
                        )
                        current_meal_id = st.session_state.current_plan.get(day, {}).get(meal)

                        eligible_ids = get_eligible_meal_ids(
                            meals, meal, selected_diet, selected_cuisine, excluded_allergens
                        )
                        options = [None] + eligible_ids

                        if current_meal_id not in options:
                            current_meal_id = None
                            st.session_state.current_plan[day][meal] = None

                        def format_option_r2(mid):
                            if mid is None or mid not in meals_by_id:
                                return "— No Meal Planned —"
                            m = meals_by_id[mid]
                            nut = nutrition.get(mid, {})
                            return f"{m['name']} ({nut.get('calories', 0):.0f} kcal)"

                        slot_key = f"w_slot_{week_start_str}_{day}_{meal}_v{st.session_state.plan_version}"
                        selected_id = st.selectbox(
                            meal,
                            options,
                            index=options.index(current_meal_id),
                            format_func=format_option_r2,
                            key=slot_key,
                            label_visibility="collapsed",
                        )

                        if selected_id != current_meal_id:
                            st.session_state.current_plan[day][meal] = selected_id
                            db.save_plan(user_id, st.session_state.current_plan, week_start_str)
                            st.rerun()

                        if selected_id:
                            m_nut = nutrition.get(selected_id, {})
                            day_cals += m_nut.get("calories", 0.0)
                            day_prot += m_nut.get("protein", 0.0)

                    cal_badge_cls = "wb-badge-veg" if abs(day_cals - target_calories) <= 250 else "wb-badge-amber"
                    st.markdown(
                        f"""
                        <div style='margin-top: 14px; padding-top: 10px; border-top: 1px solid #27272a; display: flex; justify-content: space-between; align-items: center;'>
                            <div>
                                <span class='wb-badge {cal_badge_cls}'>{day_cals:.0f} kcal</span>
                                <span class='wb-badge wb-badge-zinc'>{day_prot:.0f}g protein</span>
                            </div>
                        </div>
                        <div style='height: 8px;'></div>
                        """,
                        unsafe_allow_html=True,
                    )

                    if st.button(f"Cook {day}", key=f"btn_cook_{day}", use_container_width=True, type="secondary"):
                        st.session_state.cook_target_day = day
                        st.session_state.main_app_tabs_v2 = "Cook Mode"
                        st.rerun()

        # Weekly summary
        with row2_cols[3]:
            with st.container(border=True):
                st.markdown(
                    """
                    <div style='margin-bottom: 8px; padding-bottom: 6px; border-bottom: 1px solid #27272a;'>
                        <span style='font-size: 1.05rem; font-weight: 700; color: #fafafa;'>Weekly Targets</span>
                        <div style='font-size: 0.75rem; color: #71717a;'>Mifflin-St Jeor Clinical Alignment</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                chart_df = pd.DataFrame({"Calories": list(daily_calories.values())}, index=[d[:3] for d in DAYS])
                st.bar_chart(chart_df, height=140)

                st.markdown(
                    f"""
                    <div style='margin-top: 12px; font-size: 0.8rem; color: #a1a1aa; line-height: 1.5;'>
                        <div>🎯 <b>Target:</b> {target_calories} kcal/day</div>
                        <div>⚖️ <b>Avg Intake:</b> {avg_daily_cal:.0f} kcal/day</div>
                        <div>🥩 <b>Weekly Protein:</b> {total_p:.0f} g</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

    # Cook mode
    elif nav_tab == "Cook Mode":
        st.markdown("<div style='font-size: 1.25rem; font-weight: 700; color: #fafafa;'>Kitchen Cook Mode</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; color: #a1a1aa; margin-bottom: 1.25rem;'>Live guidance, ingredient checklists, and countdown timer for your planned meals.</div>", unsafe_allow_html=True)

        active_plan = get_ui_plan()
        default_day = st.session_state.get("cook_target_day", "Monday")

        sel_c1, sel_c2 = st.columns([2, 2])
        with sel_c1:
            cook_day = st.selectbox("Select Day", DAYS, index=DAYS.index(default_day) if default_day in DAYS else 0)
        with sel_c2:
            cook_meal_type = st.selectbox("Select Meal Slot", MEAL_TYPES, format_func=format_title)

        chosen_meal_id = active_plan.get(cook_day, {}).get(cook_meal_type)

        if not chosen_meal_id or chosen_meal_id not in meals_by_id:
            ui.alert(
                title="No meal planned for this slot",
                description=f"You haven't selected a meal for {cook_day} {format_title(cook_meal_type)} yet. Head to the Weekly Planner tab to assign a recipe!",
                key="cook_mode_empty_alert",
            )
        else:
            recipe = meals_by_id[chosen_meal_id]
            rec_nut = nutrition.get(chosen_meal_id, {})
            prep_mins = int(recipe.get("prep_time_mins", 20) or 20)
            allergens_str = recipe.get("allergens") or "none"
            diet_badge = "wb-badge-veg" if recipe["dietary_category"] == "vegetarian" else ("wb-badge-vegan" if recipe["dietary_category"] == "vegan" else "wb-badge-nonveg")

            with st.container(border=True):
                h_c1, h_c2 = st.columns([6, 2])
                with h_c1:
                    st.markdown(
                        f"""
                        <div>
                            <span class='wb-badge {diet_badge}'>{format_title(recipe['dietary_category'])}</span>
                            <span class='wb-badge wb-badge-zinc'>{format_title(recipe['cuisine_type'])}</span>
                            <span class='wb-badge wb-badge-amber'>⏱️ {prep_mins} mins</span>
                            <span class='wb-badge wb-badge-sky'>🔥 {rec_nut.get('calories', 0):.0f} kcal</span>
                            <div style='font-size: 1.6rem; font-weight: 800; color: #fafafa; margin-top: 8px; letter-spacing: -0.02em;'>{recipe['name']}</div>
                            <div style='font-size: 0.85rem; color: #a1a1aa; margin-top: 4px;'>{recipe.get('description') or ''}</div>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                with h_c2:
                    st.markdown(
                        f"""
                        <div style='text-align: right;'>
                            <span class='wb-badge {"wb-badge-nonveg" if allergens_str != "none" else "wb-badge-veg"}'>
                                Allergens: {allergens_str.title()}
                            </span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )

            col_prep, col_timer = st.columns([5, 3])
            with col_prep:
                with st.container(border=True):
                    st.markdown("<div style='font-size: 1rem; font-weight: 600; color: #fafafa; margin-bottom: 10px;'>Required Ingredients</div>", unsafe_allow_html=True)
                    items = rec_nut.get("items", [])
                    pantry_set = set(pantry_ids)
                    for it in items:
                        is_owned = it["id"] in pantry_set
                        st.checkbox(
                            f"**{format_qty(it['qty'])} {it['unit']}** {it['name']}" + (" (In Pantry)" if is_owned else ""),
                            key=f"cook_chk_{it['name']}_{chosen_meal_id}",
                        )

                with st.container(border=True):
                    st.markdown("<div style='font-size: 1rem; font-weight: 600; color: #fafafa; margin-bottom: 10px;'>Cooking Instructions</div>", unsafe_allow_html=True)
                    steps = recipe.get("instructions") or "Prepare ingredients, cook according to preference, and serve hot."
                    for s_idx, step in enumerate(steps.split(". "), start=1):
                        clean_step = step.strip()
                        if clean_step:
                            st.markdown(f"**Step {s_idx}:** {clean_step}.")

            with col_timer:
                timer_html = f"""
                <!DOCTYPE html>
                <html>
                <head>
                <meta charset="utf-8">
                <style>
                  * {{ box-sizing: border-box; margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }}
                  body {{ background: transparent; color: #fafafa; }}
                  .timer-box {{
                    background: #121215;
                    border: 1px solid #27272a;
                    border-radius: 10px;
                    padding: 1.25rem 1rem;
                    text-align: center;
                  }}
                  .timer-title {{
                    font-size: 1rem;
                    font-weight: 600;
                    color: #fafafa;
                  }}
                  .timer-sub {{
                    font-size: 0.75rem;
                    color: #71717a;
                    margin-top: 3px;
                  }}
                  .timer-display {{
                    font-size: 3.5rem;
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace;
                    font-weight: 800;
                    color: #fafafa;
                    letter-spacing: -0.04em;
                    margin: 1.1rem 0 0.8rem;
                    transition: color 0.15s ease;
                  }}
                  .timer-display.running {{ color: #38bdf8; }}
                  .timer-display.done {{ color: #f87171; animation: pulse 1s infinite; }}
                  @keyframes pulse {{
                    0%, 100% {{ opacity: 1; }}
                    50% {{ opacity: 0.4; }}
                  }}
                  .badge {{
                    display: inline-block;
                    font-size: 0.72rem;
                    font-weight: 600;
                    padding: 3px 10px;
                    border-radius: 9999px;
                    margin-bottom: 1.1rem;
                    background: #27272a;
                    color: #a1a1aa;
                    border: 1px solid #3f3f46;
                  }}
                  .badge.running {{
                    background: rgba(56, 189, 248, 0.15);
                    color: #38bdf8;
                    border-color: rgba(56, 189, 248, 0.3);
                  }}
                  .badge.done {{
                    background: rgba(239, 68, 68, 0.15);
                    color: #f87171;
                    border-color: rgba(239, 68, 68, 0.3);
                  }}
                  .btn-row {{
                    display: flex;
                    gap: 8px;
                    justify-content: center;
                    margin-bottom: 8px;
                  }}
                  button {{
                    cursor: pointer;
                    border-radius: 6px;
                    font-size: 0.85rem;
                    font-weight: 600;
                    padding: 0.5rem 0.75rem;
                    transition: all 0.15s ease;
                  }}
                  .btn-pri {{
                    flex: 1.4;
                    background: #fafafa;
                    color: #09090b;
                    border: 1px solid #ffffff;
                  }}
                  .btn-pri:hover {{ background: #e4e4e7; transform: translateY(-1px); }}
                  .btn-sec {{
                    flex: 1;
                    background: #18181b;
                    color: #e4e4e7;
                    border: 1px solid #27272a;
                  }}
                  .btn-sec:hover {{ background: #27272a; border-color: #3f3f46; color: #ffffff; }}
                  .btn-sm {{
                    flex: 1;
                    font-size: 0.75rem;
                    padding: 0.35rem 0.5rem;
                  }}
                </style>
                </head>
                <body>
                  <div class="timer-box">
                    <div class="timer-title">Kitchen Countdown Timer</div>
                    <div class="timer-sub">Target Prep Time: {prep_mins} minutes</div>
                    <div id="clock" class="timer-display">00:00</div>
                    <div><span id="pill" class="badge">Ready</span></div>

                    <div class="btn-row">
                      <button id="toggleBtn" class="btn-pri" onclick="handleToggle()">▶ Start</button>
                      <button class="btn-sec" onclick="handleReset()">Reset</button>
                    </div>
                    <div class="btn-row">
                      <button class="btn-sec btn-sm" onclick="adjust(-300)">−5m</button>
                      <button class="btn-sec btn-sm" onclick="adjust(-60)">−1m</button>
                      <button class="btn-sec btn-sm" onclick="adjust(60)">+1m</button>
                      <button class="btn-sec btn-sm" onclick="adjust(300)">+5m</button>
                    </div>
                  </div>

                  <script>
                    const baseSecs = {prep_mins} * 60;
                    let currentSecs = baseSecs;
                    let intervalId = null;
                    let running = false;
                    let audioContext = null;

                    const clock = document.getElementById('clock');
                    const pill = document.getElementById('pill');
                    const toggleBtn = document.getElementById('toggleBtn');

                    function getAudio() {{
                      if (!audioContext) {{
                        audioContext = new (window.AudioContext || window.webkitAudioContext)();
                      }}
                      if (audioContext.state === 'suspended') {{
                        audioContext.resume();
                      }}
                      return audioContext;
                    }}

                    function chime() {{
                      try {{
                        const ctx = getAudio();
                        const osc = ctx.createOscillator();
                        const g = ctx.createGain();
                        osc.type = 'sine';
                        osc.frequency.setValueAtTime(880, ctx.currentTime);
                        g.gain.setValueAtTime(0.3, ctx.currentTime);
                        g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + 1.2);
                        osc.connect(g);
                        g.connect(ctx.destination);
                        osc.start();
                        osc.stop(ctx.currentTime + 1.2);
                      }} catch (e) {{}}
                    }}

                    function updateUI() {{
                      const m = Math.floor(currentSecs / 60);
                      const s = currentSecs % 60;
                      clock.textContent = String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');

                      if (currentSecs === 0) {{
                        clock.className = 'timer-display done';
                        pill.className = 'badge done';
                        pill.textContent = "🔔 Time's Up!";
                        toggleBtn.textContent = '▶ Restart';
                      }} else if (running) {{
                        clock.className = 'timer-display running';
                        pill.className = 'badge running';
                        pill.textContent = '● Cooking in Progress';
                        toggleBtn.textContent = '⏸ Pause';
                      }} else {{
                        clock.className = 'timer-display';
                        pill.className = 'badge';
                        pill.textContent = (currentSecs === baseSecs) ? 'Ready' : 'Paused';
                        toggleBtn.textContent = (currentSecs === baseSecs) ? '▶ Start' : '▶ Resume';
                      }}
                    }}

                    function handleToggle() {{
                      getAudio();
                      if (currentSecs === 0) {{
                        currentSecs = baseSecs;
                      }}
                      if (running) {{
                        clearInterval(intervalId);
                        intervalId = null;
                        running = false;
                      }} else {{
                        running = true;
                        intervalId = setInterval(() => {{
                          if (currentSecs > 0) {{
                            currentSecs--;
                            updateUI();
                            if (currentSecs === 0) {{
                              clearInterval(intervalId);
                              intervalId = null;
                              running = false;
                              updateUI();
                              chime();
                            }}
                          }}
                        }}, 1000);
                      }}
                      updateUI();
                    }}

                    function handleReset() {{
                      clearInterval(intervalId);
                      intervalId = null;
                      running = false;
                      currentSecs = baseSecs;
                      updateUI();
                    }}

                    function adjust(delta) {{
                      currentSecs = Math.max(0, currentSecs + delta);
                      updateUI();
                    }}

                    updateUI();
                  </script>
                </body>
                </html>
                """
                components.html(timer_html, height=295)

    # Kitchen pantry
    elif nav_tab == "Kitchen Pantry":
        st.markdown("<div style='font-size: 1.25rem; font-weight: 700; color: #fafafa;'>Kitchen Pantry Inventory</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; color: #a1a1aa; margin-bottom: 1.25rem;'>Check items you currently have in your kitchen or fridge. WeeklyBite automatically deducts them from your grocery shopping budget!</div>", unsafe_allow_html=True)

        pantry_set = set(db.get_user_pantry(user_id))
        ui.alert(
            title=f"{len(pantry_set)} ingredients currently stocked in your kitchen",
            description="Items marked as owned are automatically deducted from your shopping total in the Provisions tab.",
            key="pantry_alert_stocked",
        )

        categories = {}
        for ing in sorted(ingredients, key=lambda x: (x["category"], x["name"])):
            cat = ing["category"]
            categories.setdefault(cat, []).append(ing)

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)
        p_cols = st.columns(3)
        for c_idx, (cat_name, items) in enumerate(categories.items()):
            with p_cols[c_idx % 3]:
                with st.container(border=True):
                    st.markdown(f"<div style='font-size: 0.85rem; font-weight: 700; color: #fafafa; margin-bottom: 8px; text-transform: uppercase; letter-spacing: 0.05em;'>{cat_name}</div>", unsafe_allow_html=True)
                    for ing in items:
                        is_in = ing["id"] in pantry_set
                        checked = st.checkbox(
                            f"{ing['name']} ({ing['unit']})",
                            value=is_in,
                            key=f"pantry_ing_{ing['id']}",
                        )
                        if checked != is_in:
                            db.toggle_pantry_item(user_id, ing["id"])
                            st.rerun()

    # Provisions and budget
    elif nav_tab == "Provisions & Budget":
        st.markdown("<div style='font-size: 1.25rem; font-weight: 700; color: #fafafa;'>Provisions & Shopping Budget</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; color: #a1a1aa; margin-bottom: 1.25rem;'>Consolidated grocery checklist across your planned week, with pantry inventory deductions applied automatically.</div>", unsafe_allow_html=True)

        active_plan = get_ui_plan()
        pantry_ids = db.get_user_pantry(user_id)
        summary = build_provisions_summary(active_plan, nutrition, pantry_ids)

        if not summary["all_items"]:
            ui.alert(
                title="No meals planned yet",
                description="Assign meals in your Weekly Planner to compile your consolidated grocery list.",
                key="provisions_empty_alert",
            )
        else:
            g_col1, g_col2, g_col3, g_col4 = st.columns(4)
            with g_col1:
                ui.metric_card("Total Items Needed", f"{len(summary['all_items'])}", key="prov_total_items")
            with g_col2:
                ui.metric_card(
                    "Pantry Deductions",
                    f"{len(summary['all_items']) - len(summary['items_to_buy'])} items",
                    delta=f"Saved ₹ {summary['saved_cost']:.0f}",
                    key="prov_pantry_saved",
                )
            with g_col3:
                ui.metric_card("Items to Purchase", f"{len(summary['items_to_buy'])}", key="prov_items_to_buy")
            with g_col4:
                ui.metric_card(
                    "Est. Shopping Cost",
                    f"₹ {summary['cost_to_buy']:.0f}",
                    delta=f"₹ {weekly_budget - summary['cost_to_buy']:.0f} remaining",
                    key="prov_shopping_cost",
                )

            st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
            budget_ratio = min(summary["cost_to_buy"] / weekly_budget, 1.0) if weekly_budget > 0 else 0.0
            st.progress(budget_ratio)

            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)

            cat_groups = {}
            for it in sorted(summary["all_items"], key=lambda x: (x["category"], x["name"])):
                cat_groups.setdefault(it["category"], []).append(it)

            col_l, col_r = st.columns(2)
            half = (len(cat_groups) + 1) // 2
            cat_list = list(cat_groups.items())

            export_lines = [
                f"WeeklyBite Grocery List (Week of {week_start.strftime('%b %d, %Y')})",
                f"Budget: ₹ {weekly_budget:.0f} | Estimated Cost to Buy: ₹ {summary['cost_to_buy']:.0f} | Pantry Savings: ₹ {summary['saved_cost']:.0f}",
                "=" * 50,
            ]

            for idx, (cat_name, items) in enumerate(cat_list):
                target_col = col_l if idx < half else col_r
                with target_col:
                    with st.container(border=True):
                        st.markdown(f"<div style='font-size: 0.85rem; font-weight: 700; color: #fafafa; margin-bottom: 8px; text-transform: uppercase;'>{cat_name}</div>", unsafe_allow_html=True)
                        export_lines.append(f"\n[{cat_name.upper()}]")
                        for it in items:
                            owned_str = " (Owned in Pantry)" if it["in_pantry"] else f" — approx ₹ {it['cost']:.0f}"
                            label_str = f"{it['name']} — **{format_qty(it['qty'])} {it['unit']}**{owned_str}"
                            st.checkbox(label_str, key=f"buy_chk_{it['id']}", value=it["in_pantry"], disabled=it["in_pantry"])
                            export_lines.append(f"- {format_qty(it['qty'])} {it['unit']} {it['name']}{owned_str}")

            st.markdown("<div style='height: 14px;'></div>", unsafe_allow_html=True)
            st.download_button(
                "📥 Download Grocery Checklist (.txt)",
                "\n".join(export_lines),
                file_name=f"weeklybite_groceries_{week_start_str}.txt",
                mime="text/plain",
                type="secondary",
            )

    # Fridge menu
    elif nav_tab == "Fridge Menu":
        st.markdown("<div style='font-size: 1.25rem; font-weight: 700; color: #fafafa;'>Fridge-Ready Printable Schedule</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; color: #a1a1aa; margin-bottom: 1.25rem;'>An editorial weekly schedule ready to print or pin to your refrigerator door.</div>", unsafe_allow_html=True)

        active_plan = get_ui_plan()
        table_rows = []
        total_plan_cals = 0.0
        for idx, day in enumerate(DAYS):
            day_date = week_start + timedelta(days=idx)
            b_id = active_plan.get(day, {}).get("breakfast")
            l_id = active_plan.get(day, {}).get("lunch")
            d_id = active_plan.get(day, {}).get("dinner")

            b_name = meals_by_id[b_id]["name"] if b_id in meals_by_id else "—"
            l_name = meals_by_id[l_id]["name"] if l_id in meals_by_id else "—"
            d_name = meals_by_id[d_id]["name"] if d_id in meals_by_id else "—"

            cals = sum([nutrition.get(mid, {}).get("calories", 0) for mid in [b_id, l_id, d_id] if mid])
            total_plan_cals += cals

            table_rows.append({
                "day": day,
                "date": day_date.strftime("%b %d"),
                "breakfast": b_name,
                "lunch": l_name,
                "dinner": d_name,
                "energy": f"{cals:.0f} kcal",
            })

        avg_cal = total_plan_cals / 7.0

        rows_print_html = ""
        for r in table_rows:
            rows_print_html += f"""
            <tr>
                <td style="font-weight: 700; width: 16%;">
                    {r['day']}
                    <span style="font-size: 11px; color: #6b7280; display: block; font-weight: 400; margin-top: 2px;">{r['date']}</span>
                </td>
                <td style="width: 25%;">{r['breakfast']}</td>
                <td style="width: 25%;">{r['lunch']}</td>
                <td style="width: 25%;">{r['dinner']}</td>
                <td style="width: 9%; text-align: right; font-weight: 700;">{r['energy']}</td>
            </tr>
            """

        fridge_printable_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>WeeklyBite Meal Schedule — Week of {week_start.strftime('%b %d, %Y')}</title>
<style>
  @page {{
    size: landscape;
    margin: 1.2cm;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
    color: #111827;
    background: #ffffff;
    padding: 24px;
    -webkit-print-color-adjust: exact;
    print-color-adjust: exact;
  }}
  .print-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    border-bottom: 2px solid #111827;
    padding-bottom: 12px;
    margin-bottom: 18px;
  }}
  .brand-title {{
    font-size: 22px;
    font-weight: 800;
    letter-spacing: -0.02em;
    color: #111827;
  }}
  .brand-subtitle {{
    font-size: 12px;
    color: #4b5563;
    margin-top: 3px;
  }}
  .meta-info {{
    text-align: right;
    font-size: 12px;
    color: #4b5563;
    line-height: 1.4;
  }}
  .meta-info strong {{ color: #111827; }}
  table {{
    width: 100%;
    border-collapse: collapse;
    margin-bottom: 18px;
  }}
  th {{
    background-color: #f3f4f6;
    color: #111827;
    font-size: 11px;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    padding: 10px 14px;
    border: 1px solid #d1d5db;
    text-align: left;
  }}
  td {{
    padding: 11px 14px;
    border: 1px solid #e5e7eb;
    font-size: 13px;
    color: #374151;
    vertical-align: middle;
  }}
  tr:nth-child(even) td {{
    background-color: #f9fafb;
  }}
  .notes-card {{
    border: 1px dashed #9ca3af;
    border-radius: 6px;
    padding: 12px 16px;
    display: flex;
    justify-content: space-between;
    font-size: 12px;
    color: #4b5563;
    margin-top: 14px;
  }}
  .print-footer {{
    margin-top: 16px;
    text-align: center;
    font-size: 11px;
    color: #9ca3af;
  }}
</style>
</head>
<body>
  <div class="print-header">
    <div>
      <div class="brand-title">WeeklyBite — Weekly Meal Schedule</div>
      <div class="brand-subtitle">Precision Culinary Planning &amp; Metabolic Nutrition</div>
    </div>
    <div class="meta-info">
      <div><strong>Week:</strong> {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')}</div>
      <div><strong>Plan For:</strong> {p_name} &bull; <strong>Daily Target:</strong> {target_calories} kcal/day</div>
    </div>
  </div>

  <table>
    <thead>
      <tr>
        <th>Day</th>
        <th>Breakfast</th>
        <th>Lunch</th>
        <th>Dinner</th>
        <th style="text-align: right;">Energy</th>
      </tr>
    </thead>
    <tbody>
      {rows_print_html}
    </tbody>
  </table>

  <div class="notes-card">
    <div>💧 <strong>Hydration:</strong> 8 glasses (2L) daily</div>
    <div>⚖️ <strong>Average Intake:</strong> {avg_cal:.0f} kcal/day (Target: {target_calories} kcal)</div>
    <div>📌 <strong>Pantry Checklist:</strong> Prepped &amp; verified</div>
  </div>

  <div class="print-footer">
    WeeklyBite &bull; Pin to your refrigerator door for daily meal prep
  </div>
</body>
</html>
"""

        p_c1, p_c2 = st.columns([1, 1])
        with p_c1:
            print_button_component = f"""
            <!DOCTYPE html>
            <html>
            <head>
            <meta charset="utf-8">
            <style>
              body {{ margin: 0; padding: 0; background: transparent; }}
              button {{
                display: flex;
                align-items: center;
                justify-content: center;
                gap: 8px;
                width: 100%;
                height: 38px;
                background-color: #fafafa;
                color: #09090b;
                border: 1px solid #ffffff;
                border-radius: 6px;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                font-size: 0.875rem;
                font-weight: 600;
                cursor: pointer;
                transition: all 0.15s ease;
                box-shadow: 0 1px 2px rgba(0, 0, 0, 0.2);
              }}
              button:hover {{
                background-color: #e4e4e7;
                transform: translateY(-1px);
              }}
            </style>
            </head>
            <body>
              <button onclick="doPrint()">🖨️ Print Fridge Schedule</button>
              <script>
                function doPrint() {{
                  const html = {json.dumps(fridge_printable_html)};
                  const w = window.open('', '_blank');
                  if (w) {{
                    w.document.open();
                    w.document.write(html);
                    w.document.close();
                    w.focus();
                    setTimeout(function() {{
                      w.print();
                    }}, 350);
                  }} else {{
                    window.parent.print();
                  }}
                }}
              </script>
            </body>
            </html>
            """
            components.html(print_button_component, height=45)

        with p_c2:
            st.download_button(
                "📥 Download Printable Schedule (.html)",
                fridge_printable_html,
                file_name=f"weeklybite_fridge_menu_{week_start_str}.html",
                mime="text/html",
                type="secondary",
                use_container_width=True,
            )

        st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)

        on_screen_table_rows = ""
        for r in table_rows:
            on_screen_table_rows += f"""
            <tr>
                <td style='font-weight: 700; color: #fafafa; width: 16%;'>
                    {r['day']}
                    <span style='font-size: 0.72rem; color: #71717a; display: block;'>{r['date']}</span>
                </td>
                <td style='color: #e4e4e7; width: 26%;'>{r['breakfast']}</td>
                <td style='color: #e4e4e7; width: 26%;'>{r['lunch']}</td>
                <td style='color: #e4e4e7; width: 26%;'>{r['dinner']}</td>
                <td style='text-align: right; font-weight: 600; color: #38bdf8; width: 10%;'>{r['energy']}</td>
            </tr>
            """

        st.markdown(
            f"""
            <div id='fridge-print-area' class='wb-card'>
                <div style='display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 12px; padding-bottom: 10px; border-bottom: 1px solid #27272a;'>
                    <div>
                        <div style='font-size: 1.15rem; font-weight: 700; color: #fafafa;'>Weekly Meal Schedule</div>
                        <div style='font-size: 0.75rem; color: #71717a;'>Week of {week_start.strftime('%b %d')} – {week_end.strftime('%b %d, %Y')} &bull; {p_name}</div>
                    </div>
                    <div style='text-align: right;'>
                        <span class='wb-badge wb-badge-zinc'>Target: {target_calories} kcal/day</span>
                    </div>
                </div>
                <table class='wb-table'>
                    <thead>
                        <tr>
                            <th style='width: 16%;'>Day</th>
                            <th style='width: 26%;'>Breakfast</th>
                            <th style='width: 26%;'>Lunch</th>
                            <th style='width: 26%;'>Dinner</th>
                            <th style='width: 10%; text-align: right;'>Energy</th>
                        </tr>
                    </thead>
                    <tbody>
                        {on_screen_table_rows}
                    </tbody>
                </table>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # Recipe compendium
    elif nav_tab == "Recipe Compendium":
        st.markdown("<div style='font-size: 1.25rem; font-weight: 700; color: #fafafa;'>Recipe Compendium & Meal Creator</div>", unsafe_allow_html=True)

        sub_mode = ui.tabs(["Browse Recipes", "Add Custom Recipe"], key="catalog_sub_tabs_v2")

        if sub_mode == "Browse Recipes":
            search_query = st.text_input("Search catalog by recipe name", "").strip().lower()
            filtered = [m for m in meals if not search_query or search_query in m["name"].lower()]

            st.write(f"Showing **{len(filtered)}** recipe(s):")
            c_grid = st.columns(3)
            for idx, m in enumerate(filtered):
                with c_grid[idx % 3]:
                    with st.container(border=True):
                        m_nut = nutrition.get(m["id"], {})
                        badge_c = "wb-badge-veg" if m["dietary_category"] == "vegetarian" else ("wb-badge-vegan" if m["dietary_category"] == "vegan" else "wb-badge-nonveg")
                        st.markdown(
                            f"""
                            <div style='display: flex; justify-content: space-between;'>
                                <span class='wb-badge {badge_c}'>{format_title(m['dietary_category'])}</span>
                                <span class='wb-badge wb-badge-amber'>⏱️ {m['prep_time_mins']}m</span>
                            </div>
                            <div style='font-size: 1.15rem; font-weight: 700; margin-top: 8px; color: #fafafa;'>{m['name']}</div>
                            <div style='font-size: 0.8rem; color: #a1a1aa; margin-bottom: 10px;'>{m.get('description') or ''}</div>
                            <div style='font-size: 0.8rem; font-weight: 600; color: #e4e4e7;'>
                                {m_nut.get('calories', 0):.0f} kcal | P: {m_nut.get('protein', 0):.0f}g | C: {m_nut.get('carbs', 0):.0f}g | F: {m_nut.get('fat', 0):.0f}g
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
        else:
            with st.container(border=True):
                st.markdown("<div style='font-size: 1.1rem; font-weight: 700; color: #fafafa;'>Create Custom Recipe</div>", unsafe_allow_html=True)
                st.markdown("<div style='font-size: 0.8rem; color: #a1a1aa; margin-bottom: 14px;'>Custom recipes are saved permanently to MySQL and become instantly available in your planner.</div>", unsafe_allow_html=True)
                with st.form("new_meal_form"):
                    nm_c1, nm_c2 = st.columns(2)
                    with nm_c1:
                        c_name = st.text_input("Recipe Name *")
                        c_type = st.selectbox("Meal Slot", MEAL_TYPES, format_func=format_title)
                        c_diet = st.selectbox("Dietary Category", DIETARY_OPTIONS, format_func=format_title)
                    with nm_c2:
                        c_cuisine = st.selectbox("Cuisine Type", CUISINE_OPTIONS, format_func=format_title)
                        c_prep = st.number_input("Prep Time (minutes)", 5, 120, 20)
                        c_allergens = st.text_input("Allergens (comma-separated, e.g. dairy, gluten)", "")

                    c_desc = st.text_area("Description")
                    c_inst = st.text_area("Cooking Instructions")

                    st.markdown("**Ingredients & Quantities**")
                    all_ing_labels = [f"{i['name']} ({i['unit']}) - {i['category']}" for i in ingredients]
                    picked_labels = st.multiselect("Pick ingredients needed", all_ing_labels)

                    picked_pairs = []
                    if picked_labels:
                        q_cols = st.columns(min(len(picked_labels), 3))
                        for q_idx, pl in enumerate(picked_labels):
                            ing_obj = next(i for i in ingredients if f"{i['name']} ({i['unit']}) - {i['category']}" == pl)
                            with q_cols[q_idx % 3]:
                                qty_val = st.number_input(
                                    f"{ing_obj['name']} ({ing_obj['unit']})",
                                    0.1, 20.0, 1.0, 0.1,
                                    key=f"custom_qty_{ing_obj['id']}",
                                )
                                picked_pairs.append((ing_obj["id"], qty_val))

                    submit_custom = st.form_submit_button("Save Recipe to Database", type="primary")
                    if submit_custom:
                        if not c_name.strip():
                            st.error("Please provide a recipe name.")
                        elif not picked_pairs:
                            st.error("Please add at least one ingredient.")
                        else:
                            db.add_custom_meal(
                                user_id=user_id,
                                name=c_name,
                                meal_type=c_type,
                                dietary_category=c_diet,
                                cuisine_type=c_cuisine,
                                description=c_desc,
                                prep_time_mins=int(c_prep),
                                image_url="",
                                allergens=c_allergens,
                                instructions=c_inst,
                                ingredient_quantities=picked_pairs,
                            )
                            st.success(f"Recipe '{c_name}' created successfully!")
                            st.rerun()

    # Wellness and health
    elif nav_tab == "Wellness & Health":
        st.markdown("<div style='font-size: 1.25rem; font-weight: 700; color: #fafafa;'>Mindful Wellness & Nutrition Goals</div>", unsafe_allow_html=True)
        st.markdown("<div style='font-size: 0.85rem; color: #a1a1aa; margin-bottom: 1.25rem;'>Log your hydration, mindful health habits, and maintain clinical metabolic accuracy.</div>", unsafe_allow_html=True)

        w_col1, w_col2 = st.columns([1, 1])

        with w_col1:
            with st.container(border=True):
                st.markdown("<div style='font-size: 1rem; font-weight: 600; color: #fafafa;'>Daily Hydration Tracker</div>", unsafe_allow_html=True)
                st.caption("Stay energized. Recommended target: 8 glasses (approx 2 Litres) per day.")

                water_ratio = min(water_glasses / 8.0, 1.0)
                st.progress(water_ratio)

                st.markdown(
                    f"""
                    <div style='text-align: center; margin: 1.25rem 0;'>
                        <div style='font-size: 2.8rem; font-weight: 800; color: #38bdf8;'>{water_glasses} / 8</div>
                        <div style='font-size: 0.8rem; color: #a1a1aa;'>Glasses of water consumed today</div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                h_btn1, h_btn2 = st.columns(2)
                with h_btn1:
                    if st.button("💧 + 1 Glass", use_container_width=True, type="primary"):
                        new_val = min(16, water_glasses + 1)
                        db.update_water_intake(user_id, new_val)
                        st.rerun()
                with h_btn2:
                    if st.button("− 1 Glass", use_container_width=True, type="secondary", disabled=(water_glasses == 0)):
                        new_val = max(0, water_glasses - 1)
                        db.update_water_intake(user_id, new_val)
                        st.rerun()

            with st.container(border=True):
                st.markdown("<div style='font-size: 1rem; font-weight: 600; color: #fafafa; margin-bottom: 8px;'>Daily Mindful Habits</div>", unsafe_allow_html=True)
                h_vitamins = st.checkbox("Took daily multivitamins / supplements", value=bool(habits.get("vitamins", False)))
                h_cooked = st.checkbox("Ate 100% home-cooked nutritious meals", value=bool(habits.get("cooked", True)))
                h_exercise = st.checkbox("Completed 30+ minutes of physical activity", value=bool(habits.get("exercise", False)))
                h_mindful = st.checkbox("Logged meals mindfully without skipping slots", value=bool(habits.get("mindful", False)))

                if (
                    h_vitamins != habits.get("vitamins")
                    or h_cooked != habits.get("cooked")
                    or h_exercise != habits.get("exercise")
                    or h_mindful != habits.get("mindful")
                ):
                    db.update_user_habits(
                        user_id,
                        {
                            "vitamins": h_vitamins,
                            "cooked": h_cooked,
                            "exercise": h_exercise,
                            "mindful": h_mindful,
                        },
                    )
                    st.rerun()

        with w_col2:
            with st.container(border=True):
                st.markdown("<div style='font-size: 1rem; font-weight: 600; color: #fafafa;'>Personal Health Profile & TDEE</div>", unsafe_allow_html=True)
                st.caption("Computed using the clinical Mifflin-St Jeor equation.")

                with st.form("health_profile_form"):
                    f_gender = st.selectbox("Biological Gender", ["male", "female"], index=0 if gender == "male" else 1, format_func=str.capitalize)
                    f_age = st.number_input("Age (years)", 10, 110, age)
                    f_height = st.number_input("Height (cm)", 100.0, 240.0, height, 0.5)
                    f_weight = st.number_input("Weight (kg)", 30.0, 250.0, weight, 0.5)

                    act_keys = list(ACTIVITY_FACTORS.keys())
                    f_act = st.selectbox("Activity Level", act_keys, index=act_keys.index(activity) if activity in act_keys else 1, format_func=format_title)

                    goal_keys = list(FITNESS_GOALS.keys())
                    f_goal = st.selectbox("Fitness Objective", goal_keys, index=goal_keys.index(fitness_goal) if fitness_goal in goal_keys else 0, format_func=lambda k: FITNESS_GOALS[k]["label"])

                    f_budget = st.number_input("Target Weekly Budget (₹)", 500.0, 50000.0, weekly_budget, 100.0)

                    save_prof = st.form_submit_button("Update Profile & Recalculate", type="primary")
                    if save_prof:
                        db.update_user_profile(
                            user_id=user_id,
                            age=int(f_age),
                            height=float(f_height),
                            weight=float(f_weight),
                            gender=f_gender,
                            fitness_goal=f_goal,
                            activity=f_act,
                            weekly_budget=float(f_budget),
                        )
                        st.session_state.user = db.get_user_profile(user_id)
                        st.success("Health profile updated!")
                        st.rerun()

                st.markdown(
                    f"""
                    <div style='margin-top: 1rem; padding-top: 10px; border-top: 1px solid #27272a;'>
                        <div style='display: flex; justify-content: space-between;'>
                            <span style='color: #a1a1aa;'>Basal Metabolic Rate (BMR):</span>
                            <span style='font-weight: 600; color: #fafafa;'>{bmr:.0f} kcal</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; margin-top: 4px;'>
                            <span style='color: #a1a1aa;'>Maintenance TDEE:</span>
                            <span style='font-weight: 600; color: #fafafa;'>{tdee} kcal</span>
                        </div>
                        <div style='display: flex; justify-content: space-between; margin-top: 4px;'>
                            <span style='color: #a1a1aa;'>Target Energy Intake:</span>
                            <span style='font-weight: 700; color: #38bdf8;'>{target_calories} kcal/day</span>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )


# Router
if "user" not in st.session_state or st.session_state.user is None:
    render_auth_screen()
else:
    render_app()

