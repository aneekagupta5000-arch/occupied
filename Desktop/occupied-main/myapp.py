import tkinter as tk
from tkinter import ttk, messagebox, colorchooser, filedialog
import json
import random
import csv
from datetime import datetime, date, timedelta
import calendar
import os
from pathlib import Path
import time
from PIL import Image, ImageTk

# Import Supabase Client & Config Helpers
import supabase_client
from supabase_client import get_supabase, is_configured

# ============================================================
# OCCUPIED — Personal Time & Life Audit
# Cloud Multi-User Frosted Tkinter + Supabase Desktop Application
# ============================================================

ICON_IMAGE = str(Path(__file__).with_name("icon.ico"))
ICON_ICO = ICON_IMAGE
ICE_GIF = str(Path(__file__).with_name("ice_melting.gif"))
PLANE_GIF = str(Path(__file__).with_name("flying_airplane.gif"))
SESSION_FILE = Path(os.getenv("APPDATA", Path.home())) / "Occupied" / "remembered_session.json"

# ---------------- THEME & COLOR SYSTEM ----------------
COLORS = {
    # Backgrounds & canvas
    "outer": "#BFA0E3",          # Soft lavender outer window frame
    "bg": "#C9A8E9",             # Bold lavender/purple outer background
    "header_bg": "#E5D4F0",       # Lighter lavender for top bar/header area
    "shadow": "#A786CA",         # Drop shadow tone for elevated cards
    "card": "#FFFFFF",           # Frosted clean white card surface
    "card_subtle": "#FAF7FD",    # Secondary frosted background
    "white_soft": "#F3E9F5",     # Very light lavender-white (used for smaller sub-cards)
    "card_border": "#B899DA",    # Subtle refined card border
    "line": "#B899DA",           # Hairline divider

    # Glassy pastel accent cards
    "purple_card": "#E2CEF7",
    "purple_border": "#C4A6EB",
    "pink_card": "#F13B9E",      # Bold hot pink (used for main recap/stat card)
    "pink_border": "#D42784",
    "mauve_card": "#C589A0",     # Dusty mauve pink (used for secondary stat card)
    "mauve_border": "#B06E87",
    "mint_card": "#C8DEDA",      # Soft mint (used for "today" panel)
    "mint_border": "#A5C9C3",
    "yellow_card": "#FBE7A1",    # Bold soft yellow (used for quote/notes card)
    "yellow_border": "#E8CE78",
    "blue_card": "#D7E7FA",
    "blue_border": "#A8CCF3",

    # Button & interactive accents (with matching hover states)
    "purple": "#8E5FE6",
    "purple_hover": "#7A4BD4",
    "pink": "#F13B9E",
    "pink_hover": "#D42784",
    "green": "#36B37E",
    "green_hover": "#2B9E6C",
    "mint": "#36B37E",
    "mint_hover": "#2B9E6C",
    "yellow": "#F7B928",
    "yellow_hover": "#E2A416",
    "blue": "#4E95E6",
    "blue_hover": "#3981D2",
    "danger": "#E64C5A",
    "danger_hover": "#D13947",
    "danger_light": "#FDEEF0",
    "danger_border": "#F7C7CC",

    # Typography
    "text": "#201A29",           # Crisp slate plum for high readability
    "muted": "#6E637D",          # Soft secondary text
    "subtle": "#988DA7",         # Micro copy and labels
    "white": "#FFFFFF",
}

CATEGORIES = [
    ("Work", "#36B37E"),
    ("Gym", "#F7B928"),
    ("Study", "#4E95E6"),
    ("Project", "#8E5FE6"),
    ("Design", "#EA588C"),
    ("Entertainment", "#FF7D6B"),
    ("Other", "#928B9B"),
]


class LifeAuditApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Occupied")
        self.root.geometry("1180x760")
        self.root.minsize(1000, 680)
        self.root.configure(bg=COLORS["outer"])

        # Set window icon if available
        if Path(ICON_ICO).exists():
            try:
                self.root.iconbitmap(ICON_ICO)
            except Exception:
                pass

        # Session & user state (Cloud Auth via Supabase)
        self.current_user = None
        self.current_user_id = None
        self.current_user_email = None
        self.current_username = None
        self.remember_var = tk.BooleanVar(value=False)
        self.user_name = ""
        self.custom_categories = [name for name, _ in CATEGORIES]
        self.custom_category_colors = {name: color for name, color in CATEGORIES}

        # Timer state
        self.timer_running = False
        self.timer_started_at = None
        self.timer_elapsed = 0
        self.activity_timers = {
            "study": {"running": False, "started_at": None, "elapsed": 0, "target": 25 * 60, "frame": 0},
            "japan": {"running": False, "started_at": None, "elapsed": 0, "target": 60 * 60, "frame": 0},
        }

        # UI assets
        self.icon_image_large = None
        self.icon_image_small = None
        self.adventure_gifs = {"study": [], "japan": []}
        self.load_icon_image()
        self.load_adventure_gifs()

        self.setup_styles()
        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

        # Show animated splash screen on startup
        self.show_splash_screen()

    def load_icon_image(self):
        """Load app icon image for UI rendering."""
        if Path(ICON_IMAGE).exists():
            try:
                with Image.open(ICON_IMAGE) as image:
                    self.icon_image_large = ImageTk.PhotoImage(
                        image.copy().resize((64, 64), Image.Resampling.LANCZOS)
                    )
                    self.icon_image_small = ImageTk.PhotoImage(
                        image.copy().resize((32, 32), Image.Resampling.LANCZOS)
                    )
            except Exception:
                self.icon_image_large = None
                self.icon_image_small = None

    def load_adventure_gifs(self):
        for key, path in (("study", ICE_GIF), ("japan", PLANE_GIF)):
            if not Path(path).exists():
                continue
            try:
                index = 0
                while True:
                    self.adventure_gifs[key].append(tk.PhotoImage(file=path, format=f"gif -index {index}"))
                    index += 1
            except tk.TclError:
                pass

    # ---------------- SUPABASE AUTHENTICATION ----------------

    def authenticate_user(self, email_input: str, password_input: str):
        """Authenticate user with Supabase Auth (email + password)."""
        email = email_input.strip()
        pwd = password_input.strip()

        if not email:
            return False, "Please enter your email address.", None
        if not pwd:
            return False, "Please enter your password.", None

        if not is_configured():
            return False, "Your account service is not available right now. Please try again later.", None

        try:
            client = get_supabase()
            res = client.auth.sign_in_with_password({"email": email, "password": pwd})
            if res.user:
                return True, res.user, email.split("@")[0]
            else:
                return False, "Login failed. Please check your credentials.", None
        except Exception as ex:
            err_msg = str(ex).lower()
            if "invalid login credentials" in err_msg or "invalid credentials" in err_msg:
                return False, "Incorrect email or password. Please try again.", None
            elif "email not confirmed" in err_msg:
                return False, "Please check your inbox and confirm your email address before logging in.", None
            elif "network" in err_msg or "connection" in err_msg or "connect" in err_msg or "timeout" in err_msg:
                return False, "No internet connection — please check your network and try again.", None
            else:
                return False, "We couldn't sign you in right now. Please try again.", None

    def register_user(self, email_input: str, password_input: str, confirm_input: str):
        """Register a new user account with Supabase Cloud Auth."""
        email = email_input.strip()
        pwd = password_input.strip()
        confirm = confirm_input.strip()

        if not email or "@" not in email or "." not in email:
            return False, "Please enter a valid email address.", None
        if not pwd or len(pwd) < 6:
            return False, "Password must be at least 6 characters long.", None
        if pwd != confirm:
            return False, "Passwords do not match.", None

        if not is_configured():
            return False, "Your account service is not available right now. Please try again later.", None

        try:
            client = get_supabase()
            res = client.auth.sign_up({"email": email, "password": pwd})
            if res.user:
                # Seed default categories in Supabase
                try:
                    for cat_name, cat_color in CATEGORIES:
                        client.table("categories").upsert({
                            "user_id": str(res.user.id),
                            "name": cat_name,
                            "color": cat_color
                        }, on_conflict="user_id,name").execute()
                except Exception:
                    pass

                has_session = res.session is not None
                return True, res.user, email.split("@")[0]
            else:
                return False, "Could not create account. Please try again.", None
        except Exception as ex:
            err_msg = str(ex).lower()
            if "already registered" in err_msg or "already exists" in err_msg:
                return False, "An account with this email already exists. Please log in.", None
            elif "weak password" in err_msg:
                return False, "Password is too weak. Please use at least 6 characters.", None
            elif "network" in err_msg or "connection" in err_msg or "connect" in err_msg or "timeout" in err_msg:
                return False, "No internet connection — please check your network and try again.", None
            else:
                return False, "We couldn't create your account right now. Please try again.", None

    # ---------------- SUPABASE CLOUD DATA STORAGE ----------------

    def add_activity_to_db(self, activity, category, duration, activity_date, notes):
        if not self.current_user_id or not is_configured():
            return
        try:
            client = get_supabase()
            client.table("activities").insert({
                "user_id": self.current_user_id,
                "name": activity,
                "category": category,
                "duration_minutes": duration,
                "logged_at": activity_date,
                "notes": notes or ""
            }).execute()
        except Exception as ex:
            messagebox.showerror("Couldn't Save Activity", "Your activity could not be saved. Please try again.")

    def get_activities(self, start_date=None, end_date=None):
        if not self.current_user_id or not is_configured():
            return []
        try:
            client = get_supabase()
            query = client.table("activities").select(
                "id, name, category, duration_minutes, logged_at, notes"
            ).eq("user_id", self.current_user_id)

            if start_date and end_date:
                query = query.gte("logged_at", start_date).lte("logged_at", end_date)

            res = query.order("logged_at", desc=True).order("id", desc=True).execute()
            return [
                (r["id"], r["name"], r["category"], r["duration_minutes"], str(r["logged_at"]), r.get("notes") or "")
                for r in (res.data or [])
            ]
        except Exception as ex:
            print("Error loading activities from Supabase:", ex)
            return []

    def update_activity_in_db(self, activity_id, activity, category, duration, activity_date, notes):
        if not self.current_user_id or not is_configured():
            return
        try:
            client = get_supabase()
            client.table("activities").update({
                "name": activity,
                "category": category,
                "duration_minutes": duration,
                "logged_at": activity_date,
                "notes": notes or ""
            }).eq("id", activity_id).eq("user_id", self.current_user_id).execute()
        except Exception as ex:
            messagebox.showerror("Couldn't Update Activity", "Your activity could not be updated. Please try again.")

    def delete_activity_from_db(self, activity_id):
        if not self.current_user_id or not is_configured():
            return
        try:
            client = get_supabase()
            client.table("activities").delete().eq("id", activity_id).eq("user_id", self.current_user_id).execute()
        except Exception as ex:
            messagebox.showerror("Couldn't Delete Activity", "Your activity could not be deleted. Please try again.")

    def get_goal(self, category):
        if not self.current_user_id or not is_configured():
            return 0
        try:
            client = get_supabase()
            res = client.table("goals").select("target_hours").eq(
                "user_id", self.current_user_id
            ).eq("name", category).eq("period", "weekly").execute()
            if res.data:
                return round(float(res.data[0]["target_hours"]) * 60)
            return 0
        except Exception:
            return 0

    def save_goal(self, category, minutes):
        if not self.current_user_id or not is_configured():
            return
        try:
            client = get_supabase()
            target_hours = round(minutes / 60, 2)
            client.table("goals").upsert({
                "user_id": self.current_user_id,
                "name": category,
                "target_hours": target_hours,
                "period": "weekly"
            }, on_conflict="user_id,name,period").execute()
        except Exception as ex:
            messagebox.showerror("Couldn't Save Goals", "Your goals could not be saved. Please try again.")

    def load_settings(self):
        """Load user categories and colors from Supabase."""
        self.user_name = self.current_username or ""
        if not self.current_user_id or not is_configured():
            self.custom_categories = [name for name, _ in CATEGORIES]
            self.custom_category_colors = {name: color for name, color in CATEGORIES}
            return

        try:
            client = get_supabase()
            res = client.table("categories").select("name, color").eq("user_id", self.current_user_id).order("id").execute()
            if res.data:
                self.custom_categories = [r["name"] for r in res.data]
                self.custom_category_colors = {r["name"]: r["color"] for r in res.data if r.get("color")}
            else:
                # Seed defaults
                for name, color in CATEGORIES:
                    client.table("categories").upsert({
                        "user_id": self.current_user_id,
                        "name": name,
                        "color": color
                    }, on_conflict="user_id,name").execute()
                self.custom_categories = [name for name, _ in CATEGORIES]
                self.custom_category_colors = {name: color for name, color in CATEGORIES}
        except Exception as ex:
            print("Error loading settings from Supabase:", ex)
            self.custom_categories = [name for name, _ in CATEGORIES]
            self.custom_category_colors = {name: color for name, color in CATEGORIES}

    def get_category_options(self):
        return self.custom_categories or [name for name, _ in CATEGORIES]

    # ---------------- UI STYLING & HELPERS ----------------

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "TCombobox",
            fieldbackground=COLORS["white"],
            background=COLORS["white"],
            foreground=COLORS["text"],
            padding=7,
            relief="flat"
        )

        style.configure(
            "Treeview",
            background=COLORS["white"],
            fieldbackground=COLORS["white"],
            foreground=COLORS["text"],
            rowheight=34,
            font=("Segoe UI", 10),
            borderwidth=0
        )

        style.configure(
            "Treeview.Heading",
            background=COLORS["purple_card"],
            foreground=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            padding=6
        )

    def make_button(self, parent, text, command, bg=COLORS["purple"], fg=COLORS["white"],
                    hover_bg=None, width=None, font=("Segoe UI", 10, "bold"),
                    padx=16, pady=8, bd=0, relief="flat", cursor="hand2"):
        """Create a modern button with automated hover animations."""
        if hover_bg is None:
            if bg == COLORS["purple"]:
                hover_bg = COLORS["purple_hover"]
            elif bg == COLORS["pink"]:
                hover_bg = COLORS["pink_hover"]
            elif bg == COLORS["green"] or bg == COLORS["mint"]:
                hover_bg = COLORS["green_hover"]
            elif bg == COLORS["yellow"]:
                hover_bg = COLORS["yellow_hover"]
            elif bg == COLORS["blue"]:
                hover_bg = COLORS["blue_hover"]
            elif bg == COLORS["danger"]:
                hover_bg = COLORS["danger_hover"]
            elif bg == COLORS["white"]:
                hover_bg = COLORS["header_bg"]
            else:
                hover_bg = bg

        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=fg,
            activebackground=hover_bg,
            activeforeground=fg,
            relief=relief,
            bd=bd,
            cursor=cursor,
            font=font,
            padx=padx,
            pady=pady
        )
        if width:
            btn.config(width=width)

        def on_enter(e):
            try:
                if btn.cget("state") != "disabled":
                    btn.config(bg=hover_bg)
            except Exception:
                pass

        def on_leave(e):
            try:
                if btn.cget("state") != "disabled":
                    btn.config(bg=bg)
            except Exception:
                pass

        btn.bind("<Enter>", on_enter)
        btn.bind("<Leave>", on_leave)
        return btn

    def clear_root(self):
        """Clear all child widgets from root window."""
        for widget in self.root.winfo_children():
            widget.destroy()

    def clear_content(self):
        """Clear content frame for subpage rendering."""
        for widget in self.content.winfo_children():
            widget.destroy()

    def build_subpage_header(self, title: str, subtitle: str = None):
        """Render a consistent top navigation header with Back button on every subpage."""
        header = tk.Frame(self.content, bg=COLORS["bg"])
        header.pack(fill="x", pady=(0, 14))

        top_bar = tk.Frame(header, bg=COLORS["bg"])
        top_bar.pack(fill="x")

        back_btn = self.make_button(
            top_bar,
            "← Back to Dashboard",
            self.show_dashboard,
            bg=COLORS["white"],
            fg=COLORS["text"],
            hover_bg=COLORS["header_bg"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=6,
            bd=1,
            relief="solid"
        )
        back_btn.config(highlightbackground=COLORS["card_border"], highlightthickness=1)
        back_btn.pack(side="left")

        tk.Label(
            header,
            text=title,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 22, "bold")
        ).pack(anchor="w", pady=(8, 2))

        if subtitle:
            tk.Label(
                header,
                text=subtitle,
                bg=COLORS["bg"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9)
            ).pack(anchor="w")

    # ---------------- CANVAS & ROUNDED CORNER CARD HELPERS ----------------

    def draw_rounded_rect(self, canvas, x1, y1, x2, y2, radius=12, **kwargs):
        """Draw a smooth polygon-based rounded rectangle on a Tkinter Canvas."""
        points = [
            x1 + radius, y1,
            x1 + radius, y1,
            x2 - radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def build_rounded_card(self, parent, bg=COLORS["card"], border=COLORS["card_border"], radius=14,
                           shadow=True, padx=14, pady=12, side=None, expand=False, fill="both",
                           padx_outer=(0,0), pady_outer=(0,0), canvas_expand=True):
        """
        Creates an elevated card container with Canvas-drawn rounded corners,
        crisp highlight border, and soft drop-shadow depth illusion.
        canvas_expand=False: inner canvas won't stretch vertically; useful for fixed-height cards.
        """
        wrapper = tk.Frame(parent, bg=parent.cget("bg"))
        if side:
            wrapper.pack(side=side, fill=fill, expand=expand, padx=padx_outer, pady=pady_outer)
        else:
            wrapper.pack(fill=fill, expand=expand, padx=padx_outer, pady=pady_outer)

        canvas = tk.Canvas(wrapper, bg=wrapper.cget("bg"), highlightthickness=0)
        canvas.pack(fill="both", expand=canvas_expand)

        inner_frame = tk.Frame(canvas, bg=bg)
        win_id = canvas.create_window((0, 0), window=inner_frame, anchor="nw")

        def on_resize(event):
            w, h = event.width, event.height
            if w < 10 or h < 10:
                return
            canvas.delete("card_bg")
            px, py = 2, 2

            if shadow:
                self.draw_rounded_rect(
                    canvas, px + 3, py + 3, w - px + 1, h - py + 1,
                    radius=radius, fill=COLORS["shadow"], outline="", tags="card_bg"
                )
                self.draw_rounded_rect(
                    canvas, px, py, w - px - 3, h - py - 3,
                    radius=radius, fill=bg, outline=border, width=1, tags="card_bg"
                )
                canvas.coords(win_id, px + padx, py + pady)
                canvas.itemconfig(win_id, width=max(10, w - 2*px - 3 - 2*padx), height=max(10, h - 2*py - 3 - 2*pady))
            else:
                self.draw_rounded_rect(
                    canvas, px, py, w - px, h - py,
                    radius=radius, fill=bg, outline=border, width=1, tags="card_bg"
                )
                canvas.coords(win_id, px + padx, py + pady)
                canvas.itemconfig(win_id, width=max(10, w - 2*px - 2*padx), height=max(10, h - 2*py - 2*pady))
            canvas.tag_lower("card_bg")

        canvas.bind("<Configure>", on_resize)
        return inner_frame

    def build_styled_card(self, parent, bg, border, side=None, expand=False, padx_outer=(0,0), pady_outer=(0,0)):
        """Helper to create a drop-shadowed card in layouts."""
        return self.build_rounded_card(parent, bg=bg, border=border, radius=12, shadow=True,
                                       side=side, expand=expand, padx_outer=padx_outer, pady_outer=pady_outer)

    def hex_to_pastel_bg(self, hex_color, factor=0.82):
        """Blend any hex color with white to produce a cohesive soft pastel tint."""
        try:
            hex_clean = hex_color.lstrip("#")
            r, g, b = tuple(int(hex_clean[i:i+2], 16) for i in (0, 2, 4))
            r = int(r * (1 - factor) + 255 * factor)
            g = int(g * (1 - factor) + 255 * factor)
            b = int(b * (1 - factor) + 255 * factor)
            return f"#{r:02x}{g:02x}{b:02x}"
        except Exception:
            return COLORS["card_subtle"]

    # ---------------- REAL METRICS CALCULATION HELPERS ----------------

    def calculate_current_streak(self) -> int:
        """Calculate consecutive active days with logged activities up to today (or yesterday)."""
        rows = self.get_activities()
        if not rows:
            return 0
        logged_dates = set(row[4] for row in rows)
        today = date.today()
        yesterday = today - timedelta(days=1)

        if today.isoformat() in logged_dates:
            check_date = today
        elif yesterday.isoformat() in logged_dates:
            check_date = yesterday
        else:
            return 0

        streak = 0
        while check_date.isoformat() in logged_dates:
            streak += 1
            check_date -= timedelta(days=1)
        return streak

    def calculate_goals_on_track(self) -> tuple[int, int]:
        """Calculate how many weekly goals are currently on pace vs total active goals."""
        goals = [(category, self.get_goal(category)) for category in self.get_category_options()]
        active_goals = [(c, g) for c, g in goals if g > 0]
        if not active_goals:
            return 0, 0

        start, end = self.current_week_range()
        rows = self.get_activities(start.isoformat(), end.isoformat())
        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]

        today = date.today()
        day_fraction = (today.weekday() + 1) / 7.0

        on_track_count = 0
        for category, goal_minutes in active_goals:
            logged = totals.get(category, 0)
            if logged >= goal_minutes or (goal_minutes > 0 and (logged / goal_minutes) >= (day_fraction * 0.75)):
                on_track_count += 1

        return on_track_count, len(active_goals)

    def get_top_categories_this_week(self, limit=2):
        """Retrieve the top N most logged categories this week (category_name, total_minutes)."""
        start, end = self.current_week_range()
        rows = self.get_activities(start.isoformat(), end.isoformat())
        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]

        sorted_cats = sorted(totals.items(), key=lambda x: x[1], reverse=True)
        return [(c, m) for c, m in sorted_cats if m > 0][:limit]

    def consistency_days_and_points(self):
        """Return the current 100-day cycle progress and cumulative points."""
        daily_totals = {}
        for row in self.get_activities():
            activity_date = str(row[4])[:10]
            daily_totals[activity_date] = daily_totals.get(activity_date, 0) + row[3]

        qualifying_days = sum(1 for minutes in daily_totals.values() if minutes >= 60)
        completed_cycles, cycle_days = divmod(qualifying_days, 100)
        points = completed_cycles * 25
        for milestone, award in ((25, 3), (50, 5), (75, 7), (100, 10)):
            if cycle_days >= milestone:
                points += award
        return cycle_days, points

    def sync_reward_progress(self):
        """Save the calculated reward progress with the user's cloud account."""
        if not self.current_user_id or not is_configured():
            return
        cycle_days, points = self.consistency_days_and_points()
        try:
            get_supabase().auth.update_user({
                "data": {
                    "reward_points": points,
                    "consistency_cycle_day": cycle_days,
                }
            })
        except Exception as ex:
            print("Error saving reward progress:", ex)

    # ---------------- STARTUP SPLASH SCREEN ----------------

    def show_splash_screen(self):
        """Display an animated startup splash loading screen."""
        self.clear_root()
        self.root.title("Occupied - Starting...")

        splash_frame = tk.Frame(self.root, bg=COLORS["outer"])
        splash_frame.pack(fill="both", expand=True)

        card_wrapper = tk.Frame(splash_frame, bg=COLORS["outer"])
        card_wrapper.place(relx=0.5, rely=0.5, anchor="center", width=540, height=440)

        # Soft drop shadow
        tk.Frame(card_wrapper, bg=COLORS["shadow"]).place(x=4, y=4, relwidth=1, relheight=1)

        card = tk.Frame(
            card_wrapper,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=40,
            pady=36
        )
        card.place(x=0, y=0, relwidth=1, relheight=1)

        # App Icon
        if getattr(self, "icon_image_large", None):
            tk.Label(card, image=self.icon_image_large, bg=COLORS["card"]).pack(pady=(8, 8))
        else:
            tk.Label(card, text="⭐", bg=COLORS["card"], fg="#E9A600", font=("Segoe UI Emoji", 44)).pack(pady=(8, 4))

        tk.Label(
            card,
            text="OCCUPIED",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 30, "bold")
        ).pack()

        tk.Label(
            card,
            text="YOUR PERSONAL TIME TRACKER",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "bold")
        ).pack(pady=(4, 24))

        # Progress bar canvas
        self.splash_canvas = tk.Canvas(
            card,
            width=380,
            height=16,
            bg=COLORS["card_subtle"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1
        )
        self.splash_canvas.pack(pady=(0, 10))

        self.splash_status_label = tk.Label(
            card,
            text="Getting things ready...",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "italic")
        )
        self.splash_status_label.pack()

        self.splash_percent_label = tk.Label(
            card,
            text="0%",
            bg=COLORS["card"],
            fg=COLORS["purple"],
            font=("Segoe UI", 11, "bold")
        )
        self.splash_percent_label.pack(pady=(4, 0))

        self.animate_splash(0)

    def animate_splash(self, step):
        if not hasattr(self, "splash_canvas") or not self.splash_canvas.winfo_exists():
            return

        progress = min(step, 100)
        width = int((progress / 100) * 378)

        self.splash_canvas.delete("bar")
        if width > 0:
            self.splash_canvas.create_rectangle(
                1, 1, 1 + width, 15,
                fill=COLORS["purple"],
                outline="",
                tags="bar"
            )

        self.splash_percent_label.config(text=f"{progress}%")

        if progress < 25:
            self.splash_status_label.config(text="Getting things ready...")
        elif progress < 50:
            self.splash_status_label.config(text="Loading your workspace...")
        elif progress < 80:
            self.splash_status_label.config(text="Almost ready...")
        else:
            self.splash_status_label.config(text="Ready!")

        if step < 100:
            self.root.after(20, lambda: self.animate_splash(step + 1))
        else:
            self.root.after(180, self.restore_saved_session)

    def save_session_for_device(self, session):
        """Remember the temporary sign-in session, never the account password."""
        if not session or not session.access_token or not session.refresh_token:
            return
        try:
            SESSION_FILE.parent.mkdir(parents=True, exist_ok=True)
            SESSION_FILE.write_text(json.dumps({
                "access_token": session.access_token,
                "refresh_token": session.refresh_token,
            }), encoding="utf-8")
        except OSError:
            pass

    def clear_saved_session(self):
        try:
            SESSION_FILE.unlink(missing_ok=True)
        except OSError:
            pass

    def restore_saved_session(self):
        """Restore the last remembered account, or show the sign-in screen."""
        if not is_configured() or not SESSION_FILE.exists():
            self.show_auth_screen()
            return

        try:
            saved = json.loads(SESSION_FILE.read_text(encoding="utf-8"))
            response = get_supabase().auth.set_session(
                saved["access_token"], saved["refresh_token"]
            )
            user = response.user
            if not user:
                user_response = get_supabase().auth.get_user()
                user = getattr(user_response, "user", user_response)
            if user:
                self.start_session(user, user.email.split("@")[0])
                return
        except (OSError, KeyError, ValueError, TypeError):
            pass

        self.clear_saved_session()
        self.show_auth_screen()

    # ---------------- AUTH (LOGIN / SIGNUP) SCREEN ----------------

    def show_auth_screen(self, initial_mode="login"):
        """Display the modern Supabase Login / Sign Up authentication screen."""
        self.clear_root()
        self.root.title("Occupied — Log In or Create an Account")

        outer = tk.Frame(self.root, bg=COLORS["outer"])
        outer.pack(fill="both", expand=True)

        card_wrapper = tk.Frame(outer, bg=COLORS["outer"])
        card_wrapper.place(relx=0.5, rely=0.5, anchor="center", width=500, height=590)

        # Soft drop shadow underlay
        tk.Frame(card_wrapper, bg=COLORS["shadow"]).place(x=4, y=4, relwidth=1, relheight=1)

        card = tk.Frame(
            card_wrapper,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=34,
            pady=28
        )
        card.place(x=0, y=0, relwidth=1, relheight=1)

        # Header area
        header = tk.Frame(card, bg=COLORS["card"])
        header.pack(fill="x", pady=(0, 14))

        if getattr(self, "icon_image_small", None):
            tk.Label(header, image=self.icon_image_small, bg=COLORS["card"]).pack()
        else:
            tk.Label(header, text="⭐", bg=COLORS["card"], fg="#E9A600", font=("Segoe UI Emoji", 26)).pack()

        tk.Label(
            header,
            text="OCCUPIED",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 22, "bold")
        ).pack()

        tk.Label(
            header,
            text="A simple place to keep track of your time",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9, "italic")
        ).pack()

        # Tabs: Log In | Sign Up
        tabs = tk.Frame(card, bg=COLORS["card_subtle"], padx=3, pady=3, highlightbackground=COLORS["card_border"], highlightthickness=1)
        tabs.pack(fill="x", pady=(0, 16))

        self.auth_mode = initial_mode

        self.login_tab_btn = tk.Button(
            tabs,
            text="LOG IN",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda: self.switch_auth_mode("login")
        )
        self.login_tab_btn.pack(side="left", fill="x", expand=True)

        self.signup_tab_btn = tk.Button(
            tabs,
            text="SIGN UP",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            cursor="hand2",
            command=lambda: self.switch_auth_mode("signup")
        )
        self.signup_tab_btn.pack(side="right", fill="x", expand=True)

        self.auth_form_container = tk.Frame(card, bg=COLORS["card"])
        self.auth_form_container.pack(fill="both", expand=True)

        self.render_auth_form()

    def switch_auth_mode(self, mode):
        self.auth_mode = mode
        self.render_auth_form()

    def render_auth_form(self):
        for widget in self.auth_form_container.winfo_children():
            widget.destroy()

        if self.auth_mode == "login":
            self.login_tab_btn.config(bg=COLORS["purple"], fg=COLORS["white"])
            self.signup_tab_btn.config(bg=COLORS["card_subtle"], fg=COLORS["muted"])

            form = tk.Frame(self.auth_form_container, bg=COLORS["card"])
            form.pack(fill="both", expand=True)

            tk.Label(
                form, text="Email Address", bg=COLORS["card"],
                fg=COLORS["text"], font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(2, 2))

            self.login_email_entry = tk.Entry(form, font=("Segoe UI", 10), relief="solid", bd=1, bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
            self.login_email_entry.pack(fill="x", ipady=4, pady=(0, 10))
            self.login_email_entry.focus_set()

            tk.Label(
                form, text="Password", bg=COLORS["card"],
                fg=COLORS["text"], font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(0, 2))

            self.login_password_entry = tk.Entry(form, show="*", font=("Segoe UI", 10), relief="solid", bd=1, bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
            self.login_password_entry.pack(fill="x", ipady=4, pady=(0, 8))

            tk.Checkbutton(
                form,
                text="Remember me on this device",
                variable=self.remember_var,
                bg=COLORS["card"],
                fg=COLORS["muted"],
                activebackground=COLORS["card"],
                activeforeground=COLORS["text"],
                selectcolor=COLORS["white"],
                font=("Segoe UI", 9),
                anchor="w"
            ).pack(anchor="w", pady=(0, 8))

            self.login_email_entry.bind("<Return>", lambda e: self.handle_login())
            self.login_password_entry.bind("<Return>", lambda e: self.handle_login())

            self.auth_error_label = tk.Label(
                form, text="", bg=COLORS["card"], fg=COLORS["danger"],
                font=("Segoe UI", 9, "bold"), wraplength=420
            )
            self.auth_error_label.pack(fill="x", pady=(0, 6))

            self.login_submit_btn = self.make_button(
                form, "LOG IN", self.handle_login, bg=COLORS["green"], fg=COLORS["white"]
            )
            self.login_submit_btn.pack(fill="x", pady=(0, 12))

            switch_lbl = tk.Label(
                form, text="Don't have an account? Sign Up",
                bg=COLORS["card"], fg=COLORS["purple"], font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            switch_lbl.pack()
            switch_lbl.bind("<Button-1>", lambda e: self.switch_auth_mode("signup"))

        else:
            self.login_tab_btn.config(bg=COLORS["card_subtle"], fg=COLORS["muted"])
            self.signup_tab_btn.config(bg=COLORS["purple"], fg=COLORS["white"])

            form = tk.Frame(self.auth_form_container, bg=COLORS["card"])
            form.pack(fill="both", expand=True)

            tk.Label(
                form, text="Email Address", bg=COLORS["card"],
                fg=COLORS["text"], font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(0, 2))

            self.signup_email_entry = tk.Entry(form, font=("Segoe UI", 10), relief="solid", bd=1, bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
            self.signup_email_entry.pack(fill="x", ipady=4, pady=(0, 8))
            self.signup_email_entry.focus_set()

            tk.Label(
                form, text="Create Password (min 6 chars)", bg=COLORS["card"],
                fg=COLORS["text"], font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(0, 2))

            self.signup_password_entry = tk.Entry(form, show="*", font=("Segoe UI", 10), relief="solid", bd=1, bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
            self.signup_password_entry.pack(fill="x", ipady=4, pady=(0, 8))

            tk.Label(
                form, text="Confirm Password", bg=COLORS["card"],
                fg=COLORS["text"], font=("Segoe UI", 9, "bold")
            ).pack(anchor="w", pady=(0, 2))

            self.signup_confirm_entry = tk.Entry(form, show="*", font=("Segoe UI", 10), relief="solid", bd=1, bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
            self.signup_confirm_entry.pack(fill="x", ipady=4, pady=(0, 8))

            self.signup_email_entry.bind("<Return>", lambda e: self.handle_signup())
            self.signup_password_entry.bind("<Return>", lambda e: self.handle_signup())
            self.signup_confirm_entry.bind("<Return>", lambda e: self.handle_signup())

            self.auth_error_label = tk.Label(
                form, text="", bg=COLORS["card"], fg=COLORS["danger"],
                font=("Segoe UI", 9, "bold"), wraplength=420
            )
            self.auth_error_label.pack(fill="x", pady=(0, 6))

            self.signup_submit_btn = self.make_button(
                form, "SIGN UP", self.handle_signup, bg=COLORS["green"], fg=COLORS["white"]
            )
            self.signup_submit_btn.pack(fill="x", pady=(0, 12))

            switch_lbl = tk.Label(
                form, text="Already have an account? Log In",
                bg=COLORS["card"], fg=COLORS["purple"], font=("Segoe UI", 9, "underline"),
                cursor="hand2"
            )
            switch_lbl.pack()
            switch_lbl.bind("<Button-1>", lambda e: self.switch_auth_mode("login"))

    def handle_login(self):
        email = self.login_email_entry.get().strip()
        pwd = self.login_password_entry.get().strip()

        self.auth_error_label.config(text="")
        if hasattr(self, "login_submit_btn") and self.login_submit_btn.winfo_exists():
            self.login_submit_btn.config(text="SIGNING IN...", state="disabled")
            self.root.update_idletasks()

        success, user_or_err, canonical_name = self.authenticate_user(email, pwd)

        if hasattr(self, "login_submit_btn") and self.login_submit_btn.winfo_exists():
            self.login_submit_btn.config(text="LOG IN", state="normal")

        if not success:
            self.auth_error_label.config(text=str(user_or_err))
            return

        if self.remember_var.get():
            self.save_session_for_device(get_supabase().auth.get_session())
        else:
            self.clear_saved_session()
        self.start_session(user_or_err, canonical_name)

    def handle_signup(self):
        email = self.signup_email_entry.get().strip()
        pwd = self.signup_password_entry.get().strip()
        confirm = self.signup_confirm_entry.get().strip()

        self.auth_error_label.config(text="")
        if hasattr(self, "signup_submit_btn") and self.signup_submit_btn.winfo_exists():
            self.signup_submit_btn.config(text="CREATING YOUR ACCOUNT...", state="disabled")
            self.root.update_idletasks()

        success, user_or_err, canonical_name = self.register_user(email, pwd, confirm)

        if hasattr(self, "signup_submit_btn") and self.signup_submit_btn.winfo_exists():
            self.signup_submit_btn.config(text="SIGN UP", state="normal")

        if not success:
            self.auth_error_label.config(text=str(user_or_err))
            return

        messagebox.showinfo(
            "Account Created!",
            f"Your account for {email} is ready.\n"
            "Your profile and activities will be saved for you."
        )
        self.start_session(user_or_err, canonical_name)

    # ---------------- SESSION MANAGEMENT ----------------

    def start_session(self, user_obj, username: str):
        self.current_user = user_obj
        self.current_user_id = str(user_obj.id) if hasattr(user_obj, "id") else str(user_obj)
        self.current_user_email = user_obj.email if hasattr(user_obj, "email") else f"{username}@cloud.app"
        self.current_username = username
        self.load_settings()
        self.sync_reward_progress()

        self.clear_root()
        self.root.title(f"{self.user_name}'s Life Audit" if self.user_name else "Occupied")
        self.build_ui()
        self.refresh_all()

    def logout(self):
        """Log out user from Supabase session, reset state, and return to login screen."""
        if messagebox.askyesno("Log Out", "Are you sure you want to log out of Occupied?"):
            if self.timer_running:
                self.reset_timer()
            try:
                if is_configured():
                    get_supabase().auth.sign_out()
            except Exception:
                pass
            self.current_user = None
            self.current_user_id = None
            self.current_user_email = None
            self.current_username = None
            self.user_name = ""
            self.custom_categories = []
            self.custom_category_colors = {}
            self.clear_saved_session()
            self.remember_var.set(False)
            self.show_auth_screen(initial_mode="login")

    # ---------------- MAIN UI SHELL ----------------

    def build_ui(self):
        outer = tk.Frame(self.root, bg=COLORS["outer"], padx=14, pady=14)
        outer.pack(fill="both", expand=True)

        self.menu_width = 250
        self.menu_visible = False

        # Sliding Sidebar Menu
        self.menu_frame = tk.Frame(
            outer,
            bg="#C5B2DB",
            width=self.menu_width,
            padx=14,
            pady=16,
            highlightbackground=COLORS["shadow"],
            highlightthickness=1
        )
        self.menu_frame.place(x=-self.menu_width, y=0, relheight=1)
        self.menu_frame.lift()
        self.menu_frame.pack_propagate(False)

        menu_header = tk.Frame(self.menu_frame, bg="#C5B2DB")
        menu_header.pack(fill="x", pady=(0, 16))

        tk.Label(
            menu_header,
            text="⭐",
            bg="#C5B2DB",
            fg="#E9A600",
            font=("Segoe UI Emoji", 32)
        ).pack()

        tk.Label(
            menu_header,
            text="OCCUPIED MENU",
            bg="#C5B2DB",
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold")
        ).pack(pady=(4, 0))

        tk.Label(
            menu_header,
            text=f"Signed in as {self.current_username}",
            bg="#C5B2DB",
            fg=COLORS["muted"],
            font=("Segoe UI", 8, "italic")
        ).pack(pady=(2, 0))

        close_button = self.make_button(
            menu_header,
            "✕ Close Menu",
            self.toggle_menu,
            bg=COLORS["white"],
            fg=COLORS["text"],
            hover_bg=COLORS["header_bg"],
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=4
        )
        close_button.pack(pady=(8, 0))

        self.nav_buttons = {}
        for name, command in [
            ("HOME", self.show_dashboard),
            ("ADD AN ACTIVITY", self.show_add_activity),
            ("LITTLE ADVENTURES", self.show_interactive_activities),
            ("ACTIVITY HISTORY", self.show_history),
            ("WEEKLY GOALS", self.show_goals),
            ("INSIGHTS", self.show_analytics),
            ("MONTHLY REVIEW", self.show_monthly_audit),
            ("REWARDS", self.show_rewards),
        ]:
            b = self.make_button(
                self.menu_frame,
                name,
                command,
                bg=COLORS["purple"],
                fg=COLORS["white"],
                width=22,
                pady=7
            )
            b.pack(fill="x", pady=5)
            self.nav_buttons[name] = b

        settings_button = self.make_button(
            self.menu_frame,
            "SETTINGS",
            self.show_settings,
            bg=COLORS["white"],
            fg=COLORS["text"],
            width=22,
            pady=7
        )
        settings_button.pack(fill="x", pady=(10, 5))
        self.nav_buttons["SETTINGS"] = settings_button

        # Menu Log Out
        logout_btn = self.make_button(
            self.menu_frame,
            "LOG OUT",
            self.logout,
            bg=COLORS["danger"],
            fg=COLORS["white"],
            width=22,
            pady=7
        )
        logout_btn.pack(fill="x", pady=(4, 0))

        # Main Elevated Container
        self.main_wrapper = tk.Frame(outer, bg=COLORS["outer"])
        self.main_wrapper.pack(side="left", fill="both", expand=True, padx=(8, 0))

        # Outer Shadow
        tk.Frame(self.main_wrapper, bg=COLORS["shadow"]).place(x=3, y=3, relwidth=1, relheight=1)

        self.main = tk.Frame(
            self.main_wrapper,
            bg=COLORS["bg"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=20,
            pady=18
        )
        self.main.place(x=0, y=0, relwidth=1, relheight=1)
        self.menu_frame.lift(self.main_wrapper)

        # Top Header Bar
        header = tk.Frame(
            self.main,
            bg=COLORS["header_bg"],
            padx=12,
            pady=8,
            highlightbackground=COLORS["card_border"],
            highlightthickness=1
        )
        header.pack(fill="x", pady=(0, 14))

        self.menu_toggle_button = tk.Button(
            header,
            text="⭐",
            bg=COLORS["white"],
            fg=COLORS["text"],
            bd=1,
            relief="solid",
            activebackground=COLORS["white_soft"],
            cursor="hand2",
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            command=self.toggle_menu
        )
        self.menu_toggle_button.config(highlightbackground=COLORS["card_border"], highlightthickness=1)
        self.menu_toggle_button.pack(side="left")

        dashboard_title = f"{self.user_name.upper()}'S DASHBOARD" if self.user_name else "OCCUPIED DASHBOARD"
        self.dashboard_title_label = tk.Label(
            header,
            text=dashboard_title,
            bg=COLORS["header_bg"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 13, "bold")
        )
        self.dashboard_title_label.pack(side="left", padx=14)

        # Right Header Items: Date + User Tag + Visible Log Out Button
        right_header = tk.Frame(header, bg=COLORS["header_bg"])
        right_header.pack(side="right")

        top_logout_btn = self.make_button(
            right_header,
            "↪ Log Out",
            self.logout,
            bg=COLORS["danger_light"],
            fg=COLORS["danger"],
            hover_bg=COLORS["danger_border"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=4,
            bd=1,
            relief="solid"
        )
        top_logout_btn.config(highlightbackground=COLORS["danger_border"], highlightthickness=1)
        top_logout_btn.pack(side="right", padx=(10, 0))

        user_tag = tk.Label(
            right_header,
            text=f"👤 {self.current_username}",
            bg=COLORS["white"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=4,
            relief="solid",
            bd=1,
            highlightbackground=COLORS["card_border"],
            highlightthickness=1
        )
        user_tag.pack(side="right", padx=(10, 0))

        self.date_label = tk.Label(
            right_header,
            text="",
            bg=COLORS["header_bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9)
        )
        self.date_label.pack(side="right")

        # Subpage Container
        self.content = tk.Frame(self.main, bg=COLORS["bg"])
        self.content.pack(fill="both", expand=True)

    def toggle_menu(self):
        if self.menu_visible:
            self.menu_frame.place_forget()
        else:
            self.menu_frame.place(x=0, y=0, relheight=1)
            self.menu_frame.lift()
        self.menu_visible = not self.menu_visible

    def set_active_nav(self, active):
        for name, button in self.nav_buttons.items():
            if name == "SETTINGS":
                button.config(bg=COLORS["purple"] if active == "SETTINGS" else COLORS["white"])
            elif name == "LOG OUT":
                button.config(bg=COLORS["danger"])
            else:
                button.config(bg=COLORS["purple"] if name == active else COLORS["white"])
                button.config(fg=COLORS["white"] if name == active else COLORS["text"])

    # ---------------- REDESIGNED DASHBOARD MAIN CONTENT ----------------

    def show_dashboard(self):
        """Render the compact dashboard shown in the reference image."""
        self.clear_content()
        self.set_active_nav("HOME")

        left = tk.Frame(self.content, bg=COLORS["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))
        right = tk.Frame(self.content, bg=COLORS["bg"], width=520)
        right.pack(side="right", fill="both", expand=False, padx=(8, 0))
        right.pack_propagate(False)

        self.build_reminder_card(left)
        self.build_week_recap_card(left)

        self.build_timer_card(right)
        self.build_notes_dashboard_card(right)
        self.build_today_panel(right)

    def dashboard_card(self, parent, bg, height=None):
        card = tk.Frame(parent, bg=bg, highlightbackground=COLORS["muted"], highlightthickness=1)
        card.pack(fill="x", pady=(0, 10))
        if height:
            card.configure(height=height)
            card.pack_propagate(False)
        return card

    def build_reminder_card(self, parent):
        card = self.dashboard_card(parent, COLORS["yellow_card"], 145)
        tk.Label(card, text="RIGHT NOW  •  " + datetime.now().strftime("%A  •  %B %d  •  %I:%M %p"),
                 bg=COLORS["yellow_card"], fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w", padx=24, pady=(18, 5))
        tk.Label(card, text="Rest is part of the plan, not a break from it.",
             bg=COLORS["yellow_card"], fg=COLORS["text"], font=("Trebuchet MS", 16, "italic"),
             wraplength=430, justify="left").pack(anchor="w", padx=24)
        tk.Label(card, text="A little reminder for right now.", bg=COLORS["yellow_card"],
                 fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w", padx=24, pady=(5, 0))

    def build_week_recap_card(self, parent):
        card = self.dashboard_card(parent, COLORS["pink_card"], 350)
        start, end = self.current_week_range()
        rows = self.get_activities(start.isoformat(), end.isoformat())
        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]

        tk.Label(card, text="this week's recap", bg=COLORS["pink_card"], fg=COLORS["text"],
                 font=("Trebuchet MS", 14, "bold")).pack(anchor="w", padx=18, pady=(16, 8))
        consistency_days, points = self.consistency_days_and_points()
        tk.Label(
            card,
            text=f"consistency: day {consistency_days}/100  •  points: {points}",
            bg=COLORS["pink_card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", padx=18, pady=(0, 8))
        for category in self.get_category_options():
            minutes = totals.get(category, 0)
            goal = self.get_goal(category)
            value = self.format_minutes(minutes)
            if goal:
                value = f"{value}/{self.format_minutes(goal)}"
            row = tk.Frame(card, bg=COLORS["pink_card"])
            row.pack(fill="x", padx=18, pady=2)
            tk.Label(row, text=category.lower(), bg=COLORS["pink_card"], fg=COLORS["text"],
                     font=("Segoe UI", 8), anchor="w").pack(side="left")
            tk.Label(row, text=value, bg=COLORS["pink_card"], fg=COLORS["text"],
                     font=("Segoe UI", 8, "bold")).pack(side="right")
            track = tk.Frame(card, bg="#D92F93", height=5)
            track.pack(anchor="w", padx=18, pady=(0, 3), fill="x")
            progress = tk.Frame(track, bg=self.category_color(category), height=5)
            progress.place(relwidth=min(minutes / goal, 1) if goal and minutes else (0.08 if minutes else 0), relheight=1)

    def build_week_chart_card(self, parent):
        card = self.dashboard_card(parent, COLORS["card"], 142)
        tk.Label(card, text="THIS WEEK", bg=COLORS["card"], fg=COLORS["text"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=18, pady=(12, 0))

        start, end = self.current_week_range()
        rows = self.get_activities(start.isoformat(), end.isoformat())
        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]

        graph = tk.Canvas(card, bg=COLORS["card"], highlightthickness=0, height=100)
        graph.pack(fill="both", expand=True, padx=18, pady=(2, 8))
        graph.update_idletasks()
        width = max(graph.winfo_width(), 300)
        maximum = max(totals.values()) if totals else 1
        categories = self.get_category_options()
        row_height = 15
        for index, category in enumerate(categories):
            y = 8 + index * row_height
            minutes = totals.get(category, 0)
            graph.create_text(0, y + 5, text=category.lower(), anchor="w", fill=COLORS["muted"], font=("Segoe UI", 7))
            bar_start = 75
            bar_end = width - 34
            graph.create_rectangle(bar_start, y + 2, bar_end, y + 9, fill="#F0EAF4", outline="")
            if minutes:
                fill_end = bar_start + ((bar_end - bar_start) * minutes / maximum)
                graph.create_rectangle(bar_start, y + 2, fill_end, y + 9, fill=self.category_color(category), outline="")
            graph.create_text(width, y + 5, text=self.format_minutes(minutes), anchor="e", fill=COLORS["text"], font=("Segoe UI", 7, "bold"))

    def build_notes_dashboard_card(self, parent):
        card = self.dashboard_card(parent, COLORS["yellow_card"], 138)
        header = tk.Frame(card, bg=COLORS["yellow_card"])
        header.pack(fill="x", padx=18, pady=(10, 6))
        tk.Label(header, text="NOTES FOR LATER", bg=COLORS["yellow_card"], fg=COLORS["text"],
                 font=("Segoe UI", 8, "bold")).pack(side="left")
        self.make_button(header, "SAVE", self._save_note, bg=COLORS["white"], fg=COLORS["text"],
                         font=("Segoe UI", 8, "bold"), padx=10, pady=5).pack(side="right")
        self.notes_widget = tk.Text(card, height=3, font=("Segoe UI", 9), relief="solid", bd=1,
                                    bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"], wrap="word")
        self.notes_widget.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self._notes_feedback_label = tk.Label(card, text="", bg=COLORS["yellow_card"], fg=COLORS["green"],
                                              font=("Segoe UI", 8, "bold"))
        self._notes_feedback_label.place(x=110, y=12)
        self._load_note_into_widget()

    def build_timer_card(self, parent):
        card = self.dashboard_card(parent, COLORS["card"], 94)
        row = tk.Frame(card, bg=COLORS["card"])
        row.pack(fill="both", expand=True, padx=18)
        tk.Label(row, text="FOCUS TIMER", bg=COLORS["card"], fg=COLORS["text"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(14, 0))
        self.timer_label = tk.Label(row, text=self.format_timer(), bg=COLORS["card"], fg=COLORS["text"],
                                    font=("Trebuchet MS", 22, "bold"))
        self.timer_label.pack(side="left", anchor="center")
        self.make_button(row, "RESET", self.reset_timer, bg=COLORS["yellow_card"], fg=COLORS["text"],
                         font=("Segoe UI", 8, "bold"), padx=12, pady=6).pack(side="right", padx=(6, 0))
        self.timer_button = self.make_button(row, "START", self.toggle_timer, bg=COLORS["green"], fg=COLORS["text"],
                                             font=("Segoe UI", 8, "bold"), padx=12, pady=6)
        self.timer_button.pack(side="right")

    def format_timer(self):
        total = max(0, int(self.timer_elapsed))
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"

    def toggle_timer(self):
        if self.timer_running:
            self.timer_elapsed += time.time() - self.timer_started_at
            self.timer_running = False
            self.timer_button.config(text="START")
        else:
            self.timer_started_at = time.time()
            self.timer_running = True
            self.timer_button.config(text="PAUSE")
            self.update_timer_display()

    def update_timer_display(self):
        if not hasattr(self, "timer_label") or not self.timer_label.winfo_exists():
            return
        elapsed = self.timer_elapsed
        if self.timer_running:
            elapsed += time.time() - self.timer_started_at
        total = int(elapsed)
        self.timer_label.config(text=f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}")
        if self.timer_running:
            self.root.after(1000, self.update_timer_display)

    def reset_timer(self):
        self.timer_running = False
        self.timer_started_at = None
        self.timer_elapsed = 0
        if hasattr(self, "timer_label") and self.timer_label.winfo_exists():
            self.timer_label.config(text=self.format_timer())
        if hasattr(self, "timer_button") and self.timer_button.winfo_exists():
            self.timer_button.config(text="START")


    def build_stat_cards_row(self, parent):
        """Render 3 bold colored stat cards side-by-side at the top of the left column."""
        row_frame = tk.Frame(parent, bg=COLORS["bg"])
        row_frame.pack(fill="x", pady=(0, 12), padx=2)

        # 1. Hours This Week Metric
        start, end = self.current_week_range()
        week_rows = self.get_activities(start.isoformat(), end.isoformat())
        week_total_minutes = sum(r[3] for r in week_rows)
        hours_str = self.format_hours_short(week_total_minutes) if week_total_minutes else "0h"

        # 2. Current Streak Metric
        streak_days = self.calculate_current_streak()
        streak_str = f"{streak_days} days" if streak_days != 1 else "1 day"

        # 3. Goals On Track Metric
        on_track, total_goals = self.calculate_goals_on_track()
        goals_str = f"{on_track}/{total_goals}" if total_goals > 0 else "0/0"

        stat_cards = [
            ("HOURS THIS WEEK", hours_str, "⏱️", COLORS["pink_card"], COLORS["pink_border"], COLORS["white"]),
            ("CURRENT STREAK", streak_str, "🔥", COLORS["mauve_card"], COLORS["mauve_border"], COLORS["white"]),
            ("GOALS ON TRACK", goals_str, "🎯", COLORS["yellow_card"], COLORS["yellow_border"], COLORS["text"]),
        ]

        for title, value, icon, bg_col, border_col, text_col in stat_cards:
            card = self.build_rounded_card(
                row_frame,
                bg=bg_col,
                border=border_col,
                radius=14,
                shadow=True,
                padx=10,
                pady=8,
                side="left",
                expand=True,
                padx_outer=(5, 5)
            )

            # Top label
            tk.Label(
                card,
                text=title,
                bg=bg_col,
                fg=text_col,
                font=("Segoe UI", 7, "bold")
            ).pack(anchor="w")

            # Value & icon row
            val_row = tk.Frame(card, bg=bg_col)
            val_row.pack(fill="x", pady=(4, 0))

            tk.Label(
                val_row,
                text=value,
                bg=bg_col,
                fg=text_col,
                font=("Trebuchet MS", 14, "bold")
            ).pack(side="left")

            tk.Label(
                val_row,
                text=icon,
                bg=bg_col,
                font=("Segoe UI Emoji", 13)
            ).pack(side="right")

    def build_activity_chart_card(self, parent):
        """Render This Week's Activity (Hours) chart in a matching rounded card."""
        card = self.build_rounded_card(
            parent,
            bg=COLORS["card"],
            border=COLORS["card_border"],
            radius=14,
            shadow=True,
            padx=12,
            pady=10,
            expand=True,
            fill="both",
            canvas_expand=True,
            pady_outer=(0, 0)
        )

        top_bar = tk.Frame(card, bg=COLORS["card"])
        top_bar.pack(fill="x", pady=(0, 6))

        tk.Label(
            top_bar,
            text="THIS WEEK'S ACTIVITY (HOURS)",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        start, end = self.current_week_range()
        tk.Label(
            top_bar,
            text=f"{start.strftime('%b %d')} - {end.strftime('%b %d')}",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8)
        ).pack(side="right")

        canvas = tk.Canvas(
            card,
            bg=COLORS["card"],
            highlightthickness=0,
            height=110
        )
        canvas.pack(fill="both", expand=True)
        self.draw_week_graph(canvas)

    def build_notes_card(self, parent):
        """Render the 'Your Notes' card below the activity chart in the left column.

        Fetches the user's single saved note from Supabase on load and pre-fills the
        text box. Save upserts back to the notes table. Uses the soft yellow palette
        (COLORS["yellow_card"] / COLORS["yellow_border"]) for contrast against the
        white chart card above it.
        """
        card = self.build_rounded_card(
            parent,
            bg=COLORS["yellow_card"],
            border=COLORS["yellow_border"],
            radius=14,
            shadow=True,
            padx=12,
            pady=10,
            expand=True,           # fills remaining left-column vertical space
            fill="both",
            canvas_expand=True,
            pady_outer=(0, 0)
        )

        # ── Header row ────────────────────────────────────────────────────
        header_row = tk.Frame(card, bg=COLORS["yellow_card"])
        header_row.pack(fill="x", pady=(0, 6))

        tk.Label(
            header_row,
            text="YOUR NOTES",
            bg=COLORS["yellow_card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold")
        ).pack(side="left")

        tk.Label(
            header_row,
            text="✏️",
            bg=COLORS["yellow_card"],
            font=("Segoe UI Emoji", 11)
        ).pack(side="right")

        # ── Multi-line text box ───────────────────────────────────────────
        self.notes_widget = tk.Text(
            card,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            bg=COLORS["white"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"],
            wrap="word",
            highlightbackground=COLORS["yellow_border"],
            highlightthickness=1
        )
        self.notes_widget.pack(fill="both", expand=True, pady=(0, 8))

        # ── Feedback label (shows "Saved ✓" briefly) ─────────────────────
        self._notes_feedback_label = tk.Label(
            card,
            text="",
            bg=COLORS["yellow_card"],
            fg=COLORS["green"],
            font=("Segoe UI", 9, "bold")
        )
        self._notes_feedback_label.pack(anchor="w")

        # ── Save button ───────────────────────────────────────────────────
        self.make_button(
            card,
            "SAVE NOTE",
            self._save_note,
            bg=COLORS["yellow"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            padx=12,
            pady=5
        ).pack(anchor="w", pady=(4, 0))

        # ── Pre-fill from Supabase ────────────────────────────────────────
        self._load_note_into_widget()

    def _load_note_into_widget(self):
        """Fetch saved note from Supabase and pre-fill the text widget."""
        if not hasattr(self, "notes_widget") or not self.notes_widget.winfo_exists():
            return
        if not self.current_user_id or not is_configured():
            return
        try:
            client = get_supabase()
            res = (
                client.table("notes")
                .select("content")
                .eq("user_id", self.current_user_id)
                .limit(1)
                .execute()
            )
            if res.data:
                saved_text = res.data[0].get("content") or ""
                self.notes_widget.delete("1.0", tk.END)
                self.notes_widget.insert("1.0", saved_text)
        except Exception as ex:
            print("Notes load error:", ex)

    def _save_note(self):
        """Upsert the note content to Supabase (one row per user)."""
        if not hasattr(self, "notes_widget") or not self.notes_widget.winfo_exists():
            return

        if not self._notes_feedback_label.winfo_exists():
            return

        content = self.notes_widget.get("1.0", tk.END).strip()

        if not self.current_user_id or not is_configured():
            self._notes_feedback_label.config(
                text="⚠ Your note could not be saved. Please try again.",
                fg=COLORS["danger"]
            )
            return

        try:
            client = get_supabase()
            client.table("notes").upsert(
                {
                    "user_id": self.current_user_id,
                    "content": content,
                    "updated_at": datetime.utcnow().isoformat() + "Z"
                },
                on_conflict="user_id"
            ).execute()

            # Show "Saved ✓" then fade after 2.5 seconds
            self._notes_feedback_label.config(text="Saved ✓", fg=COLORS["green"])
            self.root.after(
                2500,
                lambda: self._notes_feedback_label.config(text="")
                if self._notes_feedback_label.winfo_exists() else None
            )

        except Exception as ex:
            err = str(ex).lower()
            if "network" in err or "connection" in err or "timeout" in err:
                msg = "⚠ No internet connection — note not saved."
            else:
                msg = f"⚠ Save failed: {ex}"
            self._notes_feedback_label.config(text=msg, fg=COLORS["danger"])

    def build_today_panel(self, parent):
        """Render the existing 'today :) / you are remarkable' panel."""
        card = self.build_rounded_card(
            parent,
            bg=COLORS["mint_card"],
            border=COLORS["mint_border"],
            radius=14,
            shadow=True,
            padx=12,
            pady=10,
            fill="x",
            canvas_expand=False,
            pady_outer=(0, 10)
        )

        tk.Label(
            card,
            text="today :)",
            bg=COLORS["mint_card"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 20, "bold")
        ).pack(anchor="w")

        tk.Label(
            card,
            text="YOU ARE REMARKABLE",
            bg=COLORS["mint_card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8, "italic")
        ).pack(anchor="w", pady=(0, 8))

        activities = self.get_today_activities()

        if not activities:
            tk.Label(
                card,
                text="No activities logged yet today.\nStart with one small thing.",
                bg=COLORS["mint_card"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9),
                justify="left"
            ).pack(anchor="w", pady=(4, 8))
        else:
            for row in activities[:3]:
                activity_id, activity, category, duration, activity_date, notes = row
                color = self.category_color(category)

                item = tk.Frame(
                    card,
                    bg=COLORS["white_soft"],
                    highlightbackground=COLORS["mint_border"],
                    highlightthickness=1,
                    padx=6,
                    pady=3
                )
                item.pack(fill="x", pady=2)

                tk.Label(
                    item,
                    text="●",
                    fg=color,
                    bg=COLORS["white_soft"],
                    font=("Segoe UI", 12)
                ).pack(side="left", padx=4)

                text_frame = tk.Frame(item, bg=COLORS["white_soft"])
                text_frame.pack(side="left", fill="x", expand=True)

                tk.Label(
                    text_frame,
                    text=activity.upper(),
                    bg=COLORS["white_soft"],
                    fg=COLORS["text"],
                    font=("Segoe UI", 9, "bold"),
                    anchor="w"
                ).pack(fill="x")

                tk.Label(
                    text_frame,
                    text=f"{category} • {self.format_minutes(duration)}",
                    bg=COLORS["white_soft"],
                    fg=COLORS["muted"],
                    font=("Segoe UI", 8),
                    anchor="w"
                ).pack(fill="x")

        self.make_button(
            card,
            "+ LOG NEW ACTIVITY",
            self.show_add_activity,
            bg=COLORS["white_soft"],
            fg=COLORS["text"],
            hover_bg=COLORS["mint_border"],
            font=("Segoe UI", 8, "bold"),
            padx=10,
            pady=5,
            bd=1,
            relief="solid"
        ).pack(anchor="w", pady=(8, 0))

    def build_recent_activity_card(self, parent):
        """Render the Recent Activity list with last 3-4 logged activities across all dates."""
        card = self.build_rounded_card(
            parent,
            bg=COLORS["card"],
            border=COLORS["card_border"],
            radius=14,
            shadow=True,
            padx=12,
            pady=10,
            fill="x",
            canvas_expand=False,
            pady_outer=(0, 10)
        )

        tk.Label(
            card,
            text="RECENT ACTIVITY",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))

        all_activities = self.get_activities()

        if not all_activities:
            tk.Label(
                card,
                text="No recent activity yet.\nLog your first activity above!",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9, "italic"),
                justify="left"
            ).pack(anchor="w", pady=4)
        else:
            for row in all_activities[:3]:
                activity_id, activity, category, duration, activity_date, notes = row
                color = self.category_color(category)

                item = tk.Frame(
                    card,
                    bg=COLORS["white_soft"],
                    highlightbackground=COLORS["card_border"],
                    highlightthickness=1,
                    padx=6,
                    pady=3
                )
                item.pack(fill="x", pady=2)

                tk.Label(
                    item,
                    text="●",
                    fg=color,
                    bg=COLORS["white_soft"],
                    font=("Segoe UI", 11)
                ).pack(side="left", padx=4)

                tf = tk.Frame(item, bg=COLORS["white_soft"])
                tf.pack(side="left", fill="x", expand=True)

                tk.Label(
                    tf,
                    text=activity,
                    bg=COLORS["white_soft"],
                    fg=COLORS["text"],
                    font=("Segoe UI", 9, "bold"),
                    anchor="w"
                ).pack(fill="x")

                tk.Label(
                    tf,
                    text=f"{activity_date} • {category} • {self.format_minutes(duration)}",
                    bg=COLORS["white_soft"],
                    fg=COLORS["muted"],
                    font=("Segoe UI", 8),
                    anchor="w"
                ).pack(fill="x")

    def build_top_categories_card(self, parent):
        """Render Top Categories cards showing user's top 2 most-logged categories this week."""
        card = self.build_rounded_card(
            parent,
            bg=COLORS["card"],
            border=COLORS["card_border"],
            radius=14,
            shadow=True,
            padx=12,
            pady=10,
            fill="x",
            canvas_expand=False,
            pady_outer=(0, 10)
        )

        tk.Label(
            card,
            text="TOP CATEGORIES THIS WEEK",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))

        top_cats = self.get_top_categories_this_week(limit=2)

        if not top_cats:
            tk.Label(
                card,
                text="No category time tracked this week yet.",
                bg=COLORS["card"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9, "italic")
            ).pack(anchor="w", pady=4)
        else:
            cats_row = tk.Frame(card, bg=COLORS["card"])
            cats_row.pack(fill="x", pady=(2, 0))

            for cat_name, cat_mins in top_cats:
                cat_color = self.category_color(cat_name)
                tint_bg = self.hex_to_pastel_bg(cat_color, factor=0.86)

                cat_box = tk.Frame(
                    cats_row,
                    bg=tint_bg,
                    highlightbackground=cat_color,
                    highlightthickness=1,
                    padx=10,
                    pady=8
                )
                cat_box.pack(side="left", fill="both", expand=True, padx=(0, 6))

                tk.Label(
                    cat_box,
                    text=cat_name.upper(),
                    bg=tint_bg,
                    fg=cat_color,
                    font=("Segoe UI", 8, "bold"),
                    anchor="w"
                ).pack(fill="x")

                tk.Label(
                    cat_box,
                    text=self.format_hours_short(cat_mins),
                    bg=tint_bg,
                    fg=COLORS["text"],
                    font=("Trebuchet MS", 14, "bold"),
                    anchor="w"
                ).pack(fill="x", pady=(2, 0))

    def show_interactive_activities(self):
        self.clear_content()
        self.set_active_nav("LITTLE ADVENTURES")
        self.build_subpage_header(
            "Little Adventures",
            "Choose something fun to focus on, then let the timer keep you company."
        )

        cards = tk.Frame(self.content, bg=COLORS["bg"])
        cards.pack(fill="both", expand=True)
        cards.columnconfigure(0, weight=1)
        cards.columnconfigure(1, weight=1)
        cards.rowconfigure(0, weight=1)
        self.build_adventure_card(cards, "study", "study till the ice melts", "A tiny study sprint with a cool reward.", 0)
        self.build_adventure_card(cards, "japan", "catch a flight to japan!", "Pack a little curiosity and go somewhere new.", 1)

    def build_adventure_card(self, parent, key, title, description, column):
        palette = COLORS["blue_card"] if key == "study" else COLORS["yellow_card"]
        accent = COLORS["blue"] if key == "study" else COLORS["pink"]
        card = tk.Frame(parent, bg=palette, highlightbackground=accent, highlightthickness=1, padx=14, pady=14)
        card.grid(row=0, column=column, sticky="nsew", padx=(0, 7) if column == 0 else (7, 0), pady=(0, 8))

        artwork = tk.Canvas(card, height=190, bg=palette, highlightthickness=0)
        artwork.pack(fill="x")
        self.activity_timers[key]["artwork"] = artwork
        self.draw_adventure_art(artwork, key, accent)
        artwork.bind("<Button-1>", lambda event: self.adventure_prompt(key))

        tk.Label(card, text=title, bg=palette, fg=COLORS["text"], font=("Trebuchet MS", 17, "bold"),
                 wraplength=330, justify="left").pack(anchor="w", pady=(10, 3))
        tk.Label(card, text=description, bg=palette, fg=COLORS["muted"], font=("Segoe UI", 9),
                 wraplength=330, justify="left").pack(anchor="w")

        timer = self.activity_timers[key]
        controls = tk.Frame(card, bg=palette)
        controls.pack(fill="x", pady=(18, 4))
        label = tk.Label(controls, text=self.activity_timer_text(key), bg=palette, fg=COLORS["text"],
                         font=("Trebuchet MS", 22, "bold"))
        label.pack(side="left")
        timer["label"] = label

        buttons = tk.Frame(card, bg=palette)
        buttons.pack(fill="x", pady=(4, 0))
        timer["button"] = self.make_button(buttons, "START", lambda: self.toggle_adventure_timer(key),
                                            bg=accent, fg=COLORS["white"], font=("Segoe UI", 8, "bold"), padx=12, pady=6)
        timer["button"].pack(side="left")
        self.make_button(buttons, "RESET", lambda: self.reset_adventure_timer(key), bg=COLORS["white"],
                         fg=COLORS["text"], font=("Segoe UI", 8, "bold"), padx=12, pady=6).pack(side="left", padx=6)
        tk.Label(buttons, text="minutes", bg=palette, fg=COLORS["muted"], font=("Segoe UI", 8)).pack(side="left", padx=(4, 3))
        target_var = tk.StringVar(value=str(timer["target"] // 60))
        timer["target_var"] = target_var
        tk.Entry(buttons, textvariable=target_var, width=5, font=("Segoe UI", 9), relief="solid", bd=1,
                 bg=COLORS["white"], fg=COLORS["text"]).pack(side="left")
        self.make_button(buttons, "SET", lambda: self.set_adventure_target(key), bg=COLORS["white"],
                         fg=COLORS["text"], font=("Segoe UI", 8, "bold"), padx=8, pady=5).pack(side="left", padx=5)

        timer["prompt"] = tk.Label(card, text="Click the picture for a little prompt.", bg=palette, fg=accent,
                                   font=("Segoe UI", 9, "italic"), wraplength=330, justify="left")
        timer["prompt"].pack(anchor="w", pady=(16, 0))

    def draw_adventure_art(self, canvas, key, accent):
        canvas.delete("all")
        frames = self.adventure_gifs.get(key, [])
        if frames:
            canvas.create_image(170, 95, image=frames[0], anchor="center", tags="adventure_gif")
            return
        width = 340
        canvas.create_oval(105, 18, 235, 148, fill=COLORS["white"], outline="")
        if key == "study":
            canvas.create_rectangle(118, 75, 222, 140, fill="#BFE8FA", outline=accent, width=2)
            canvas.create_oval(133, 54, 207, 104, fill="#F7FCFF", outline=accent, width=2)
            canvas.create_arc(147, 62, 194, 96, start=180, extent=180, outline=accent, width=2)
            canvas.create_text(170, 119, text="STUDY", fill=accent, font=("Segoe UI", 9, "bold"))
            canvas.create_text(170, 163, text="keep going, one page at a time", fill=COLORS["muted"], font=("Segoe UI", 8, "italic"))
        else:
            canvas.create_oval(126, 62, 214, 140, fill="#F8FBFF", outline=accent, width=2)
            canvas.create_rectangle(150, 40, 190, 77, fill="#DDF1FF", outline=accent, width=2)
            canvas.create_line(170, 40, 170, 24, fill=accent, width=2)
            canvas.create_oval(165, 19, 175, 29, fill=accent, outline="")
            canvas.create_text(170, 101, text="JAPAN", fill=accent, font=("Segoe UI", 9, "bold"))
            canvas.create_text(170, 163, text="where could you wander next?", fill=COLORS["muted"], font=("Segoe UI", 8, "italic"))

    def adventure_prompt(self, key):
        prompts = {
            "study": ["Find one fascinating fact before the timer ends.", "Underline one idea you want to remember.", "Take a sip of water, then choose the next page."],
            "japan": ["Pick one place in Japan you would visit first.", "Imagine the first meal you would try there.", "Choose one Japanese word to learn today."],
        }
        timer = self.activity_timers[key]
        timer["prompt"].config(text=random.choice(prompts[key]))

    def activity_timer_text(self, key):
        total = int(self.activity_timers[key]["elapsed"])
        return f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}"

    def toggle_adventure_timer(self, key):
        timer = self.activity_timers[key]
        if timer["running"]:
            timer["elapsed"] += time.time() - timer["started_at"]
            timer["running"] = False
            timer["button"].config(text="START")
        else:
            timer["started_at"] = time.time()
            timer["running"] = True
            timer["button"].config(text="PAUSE")
            self.update_adventure_timer(key)
            self.animate_adventure_gif(key)

    def animate_adventure_gif(self, key):
        timer = self.activity_timers[key]
        frames = self.adventure_gifs.get(key, [])
        artwork = timer.get("artwork")
        if not timer["running"] or not frames or not artwork or not artwork.winfo_exists():
            return
        timer["frame"] = (timer["frame"] + 1) % len(frames)
        artwork.itemconfig("adventure_gif", image=frames[timer["frame"]])
        self.root.after(140, lambda: self.animate_adventure_gif(key))

    def update_adventure_timer(self, key):
        timer = self.activity_timers[key]
        if "label" not in timer or not timer["label"].winfo_exists():
            return
        elapsed = timer["elapsed"] + (time.time() - timer["started_at"] if timer["running"] else 0)
        total = int(elapsed)
        timer["label"].config(text=f"{total // 3600:02d}:{(total % 3600) // 60:02d}:{total % 60:02d}")
        if timer["running"]:
            self.root.after(1000, lambda: self.update_adventure_timer(key))

    def reset_adventure_timer(self, key):
        timer = self.activity_timers[key]
        timer["running"] = False
        timer["started_at"] = None
        timer["elapsed"] = 0
        timer["frame"] = 0
        if "label" in timer and timer["label"].winfo_exists():
            timer["label"].config(text=self.activity_timer_text(key))
        if "button" in timer and timer["button"].winfo_exists():
            timer["button"].config(text="START")
        artwork = timer.get("artwork")
        frames = self.adventure_gifs.get(key, [])
        if artwork and frames and artwork.winfo_exists():
            artwork.itemconfig("adventure_gif", image=frames[0])

    def set_adventure_target(self, key):
        try:
            minutes = int(self.activity_timers[key]["target_var"].get())
            if minutes <= 0:
                raise ValueError
            self.activity_timers[key]["target"] = minutes * 60
            self.activity_timers[key]["prompt"].config(text=f"Your {minutes}-minute adventure is ready. Start when you are.")
        except ValueError:
            messagebox.showwarning("Choose a time", "Enter a whole number of minutes greater than zero.")

    # ---------------- ADD ACTIVITY SCREEN ----------------

    def show_add_activity(self):
        self.clear_content()
        self.set_active_nav("ADD AN ACTIVITY")

        self.build_subpage_header(
            "Add Activity",
            "Keep a simple record of what you did and how long it took."
        )

        card_wrapper = tk.Frame(self.content, bg=COLORS["bg"])
        card_wrapper.pack(fill="both", expand=True, pady=(4, 0))

        tk.Frame(card_wrapper, bg=COLORS["shadow"]).place(x=3, y=3, relwidth=1, relheight=1)

        card = tk.Frame(
            card_wrapper,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=28,
            pady=22
        )
        card.place(x=0, y=0, relwidth=1, relheight=1)

        form = tk.Frame(card, bg=COLORS["card"])
        form.pack(fill="both", expand=True)

        self.activity_entry = self.add_form_row(
            form,
            "Activity name",
            entry_width=48
        )
        self.activity_entry.insert(0, "")

        self.category_var = tk.StringVar(value=self.get_category_options()[0])
        self.add_form_row(
            form,
            "Category",
            combo=True,
            variable=self.category_var,
            combo_width=36,
            combo_values=self.get_category_options()
        )

        duration_frame = tk.Frame(form, bg=COLORS["card"])
        duration_frame.pack(anchor="w", pady=8, fill="x")

        tk.Label(
            duration_frame,
            text="Time spent",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            width=18,
            anchor="w"
        ).pack(side="left")

        self.hours_var = tk.StringVar(value="0")
        self.minutes_var = tk.StringVar(value="30")

        duration_input = tk.Frame(duration_frame, bg=COLORS["card"])
        duration_input.pack(side="left")

        tk.Entry(
            duration_input,
            textvariable=self.hours_var,
            width=5,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            bg=COLORS["white"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"]
        ).pack(side="left")

        tk.Label(
            duration_input,
            text=":",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 11, "bold")
        ).pack(side="left", padx=4)

        tk.Entry(
            duration_input,
            textvariable=self.minutes_var,
            width=5,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            bg=COLORS["white"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"]
        ).pack(side="left")

        tk.Label(
            duration_frame,
            text="hours and minutes",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8)
        ).pack(side="left", padx=10)

        notes_frame = tk.Frame(form, bg=COLORS["card"])
        notes_frame.pack(anchor="w", pady=8, fill="x")

        tk.Label(
            notes_frame,
            text="Notes",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            width=18,
            anchor="nw"
        ).pack(side="left")

        self.notes_text = tk.Text(
            notes_frame,
            height=5,
            width=50,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            bg=COLORS["white"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"]
        )
        self.notes_text.pack(side="left", padx=(0, 4))

        date_frame = tk.Frame(form, bg=COLORS["card"])
        date_frame.pack(anchor="w", pady=8, fill="x")

        tk.Label(
            date_frame,
            text="Date",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            width=18,
            anchor="w"
        ).pack(side="left")

        self.date_entry = tk.Entry(
            date_frame,
            width=24,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            bg=COLORS["white"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"]
        )
        self.date_entry.pack(side="left")
        self.date_entry.insert(0, date.today().isoformat())

        tk.Label(
            date_frame,
            text="  year-month-day",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8)
        ).pack(side="left")

        # Bottom Actions Bar: Clear + Save + Back
        buttons = tk.Frame(card, bg=COLORS["card"])
        buttons.pack(fill="x", pady=(16, 0))

        self.make_button(
            buttons,
            "SAVE ACTIVITY",
            self.save_activity,
            bg=COLORS["green"],
            fg=COLORS["white"],
            width=16
        ).pack(side="left")

        self.make_button(
            buttons,
            "CLEAR FORM",
            self.clear_activity_form,
            bg=COLORS["white"],
            fg=COLORS["text"],
            hover_bg=COLORS["header_bg"],
            width=14,
            bd=1,
            relief="solid"
        ).pack(side="left", padx=10)

        self.make_button(
            buttons,
            "← CANCEL",
            self.show_dashboard,
            bg=COLORS["white"],
            fg=COLORS["muted"],
            hover_bg=COLORS["header_bg"],
            width=12,
            bd=1,
            relief="solid"
        ).pack(side="right")

    def add_form_row(self, parent, label, combo=False, variable=None, entry_width=28, combo_width=25, combo_values=None):
        row = tk.Frame(parent, bg=COLORS["card"])
        row.pack(anchor="w", pady=8, fill="x")

        tk.Label(
            row,
            text=label,
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 9, "bold"),
            width=18,
            anchor="w"
        ).pack(side="left")

        if combo:
            combo_box = ttk.Combobox(
                row,
                textvariable=variable,
                values=combo_values if combo_values is not None else [x[0] for x in CATEGORIES],
                state="readonly",
                width=combo_width
            )
            combo_box.pack(side="left")
            return combo_box

        entry = tk.Entry(
            row,
            width=entry_width,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1,
            bg=COLORS["white"],
            fg=COLORS["text"],
            insertbackground=COLORS["text"]
        )
        entry.pack(side="left")
        return entry

    def clear_activity_form(self):
        self.activity_entry.delete(0, tk.END)
        self.hours_var.set("0")
        self.minutes_var.set("30")
        self.date_entry.delete(0, tk.END)
        self.date_entry.insert(0, date.today().isoformat())
        self.notes_text.delete("1.0", tk.END)

    def save_activity(self):
        activity = self.activity_entry.get().strip()
        category = self.category_var.get()

        try:
            hours = int(self.hours_var.get())
            minutes = int(self.minutes_var.get())
            duration = hours * 60 + minutes
        except ValueError:
            messagebox.showerror("Invalid duration", "Please enter whole numbers for hours and minutes.")
            return

        activity_date = self.date_entry.get().strip()

        try:
            datetime.strptime(activity_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Invalid date", "Enter the date as year-month-day, for example 2026-08-09.")
            return

        if not activity:
            messagebox.showwarning("Missing activity", "Give your activity a name first.")
            return

        if duration <= 0:
            messagebox.showwarning("Missing duration", "Duration must be greater than zero.")
            return

        notes = self.notes_text.get("1.0", tk.END).strip()
        self.add_activity_to_db(activity, category, duration, activity_date, notes)
        self.sync_reward_progress()
        messagebox.showinfo("Saved!", f"{activity} was added to your activities.")
        self.show_dashboard()

    # ---------------- ACTIVITY HISTORY SCREEN ----------------

    def show_history(self):
        self.clear_content()
        self.set_active_nav("ACTIVITY HISTORY")

        self.build_subpage_header(
            "Activity History",
            "Review, change, or remove any activity you have recorded."
        )

        card_wrapper = tk.Frame(self.content, bg=COLORS["bg"])
        card_wrapper.pack(fill="both", expand=True, pady=(4, 0))

        tk.Frame(card_wrapper, bg=COLORS["shadow"]).place(x=3, y=3, relwidth=1, relheight=1)

        card = tk.Frame(
            card_wrapper,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=14,
            pady=14
        )
        card.place(x=0, y=0, relwidth=1, relheight=1)

        columns = ("date", "activity", "category", "duration", "notes")
        self.history_tree = ttk.Treeview(card, columns=columns, show="headings", selectmode="browse")
        for column, label, width in [
            ("date", "Date", 100),
            ("activity", "Activity", 210),
            ("category", "Category", 130),
            ("duration", "Duration", 95),
            ("notes", "Notes", 320)
        ]:
            self.history_tree.heading(column, text=label)
            self.history_tree.column(column, width=width, anchor="w")

        for row in self.get_activities():
            self.history_tree.insert(
                "", "end", iid=str(row[0]),
                values=(row[4], row[1], row[2], self.format_minutes(row[3]), row[5] or "")
            )
        self.history_tree.pack(fill="both", expand=True)

        buttons = tk.Frame(card, bg=COLORS["card"])
        buttons.pack(fill="x", pady=(12, 0))

        self.make_button(
            buttons, "EDIT SELECTED", self.edit_selected_activity,
            bg=COLORS["yellow"], fg=COLORS["text"], width=16
        ).pack(side="left")

        self.make_button(
            buttons, "DELETE SELECTED", self.delete_selected_activity,
            bg=COLORS["danger"], fg=COLORS["white"], width=16
        ).pack(side="left", padx=10)

    def selected_activity_id(self):
        selected = self.history_tree.selection()
        if not selected:
            messagebox.showwarning("No selection", "Select an activity first.")
            return None
        return int(selected[0])

    def delete_selected_activity(self):
        activity_id = self.selected_activity_id()
        if activity_id is None:
            return
        if messagebox.askyesno("Delete activity", "Delete this activity permanently?"):
            self.delete_activity_from_db(activity_id)
            self.sync_reward_progress()
            self.show_history()

    def edit_selected_activity(self):
        activity_id = self.selected_activity_id()
        if activity_id is None:
            return

        rows = self.get_activities()
        row = next((r for r in rows if r[0] == activity_id), None)
        if not row:
            return

        dialog = tk.Toplevel(self.root)
        dialog.title("Edit activity")
        dialog.configure(bg=COLORS["bg"])
        dialog.resizable(False, False)

        form = tk.Frame(dialog, bg=COLORS["card"], padx=28, pady=24)
        form.pack()

        tk.Label(form, text="Edit activity", bg=COLORS["card"], fg=COLORS["text"], font=("Trebuchet MS", 18, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 14))

        fields = {}
        for index, (label, value) in enumerate([
            ("Activity", row[1]),
            ("Date (year-month-day)", row[4]),
            ("Hours", str(row[3] // 60)),
            ("Minutes", str(row[3] % 60))
        ], start=1):
            tk.Label(form, text=label, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=index, column=0, sticky="w", pady=4)
            entry = tk.Entry(form, width=32, font=("Segoe UI", 10), bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
            entry.insert(0, value)
            entry.grid(row=index, column=1, pady=4)
            fields[label] = entry

        tk.Label(form, text="Category", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=4)
        category = tk.StringVar(value=row[2])
        ttk.Combobox(form, textvariable=category, values=self.get_category_options(), state="readonly", width=30).grid(row=5, column=1, pady=4)

        tk.Label(form, text="Notes", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky="nw", pady=4)
        notes = tk.Text(form, width=32, height=4, font=("Segoe UI", 10), bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
        notes.insert("1.0", row[5] or "")
        notes.grid(row=6, column=1, pady=4)

        def save_edit():
            try:
                duration = int(fields["Hours"].get()) * 60 + int(fields["Minutes"].get())
                datetime.strptime(fields["Date (year-month-day)"].get().strip(), "%Y-%m-%d")
                if not fields["Activity"].get().strip() or duration <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid details", "Enter an activity, valid date, and positive duration.", parent=dialog)
                return
            self.update_activity_in_db(
                activity_id, fields["Activity"].get().strip(), category.get(), duration,
                fields["Date (year-month-day)"].get().strip(), notes.get("1.0", tk.END).strip()
            )
            self.sync_reward_progress()
            dialog.destroy()
            self.show_history()

        self.make_button(form, "SAVE CHANGES", save_edit, bg=COLORS["green"], fg=COLORS["white"]).grid(row=7, column=1, sticky="e", pady=(14, 0))

    # ---------------- WEEKLY GOALS SCREEN ----------------

    def show_goals(self):
        self.clear_content()
        self.set_active_nav("WEEKLY GOALS")

        self.build_subpage_header(
            "Weekly Goals",
            "Choose how many hours you would like to spend on each activity each week."
        )

        card_wrapper = tk.Frame(self.content, bg=COLORS["bg"])
        card_wrapper.pack(fill="both", expand=True, pady=(4, 0))

        tk.Frame(card_wrapper, bg=COLORS["shadow"]).place(x=3, y=3, relwidth=1, relheight=1)

        card = tk.Frame(
            card_wrapper,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=28,
            pady=22
        )
        card.place(x=0, y=0, relwidth=1, relheight=1)

        self.goal_vars = {}
        for category in self.get_category_options():
            row = tk.Frame(card, bg=COLORS["card"])
            row.pack(fill="x", pady=6)

            tk.Label(
                row, text=category, bg=COLORS["card"], fg=COLORS["text"],
                width=20, anchor="w", font=("Segoe UI", 10, "bold")
            ).pack(side="left")

            var = tk.StringVar(value=str(self.get_goal(category) // 60))
            self.goal_vars[category] = var

            tk.Entry(row, textvariable=var, width=6, font=("Segoe UI", 10), relief="solid", bd=1, bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"]).pack(side="left")
            tk.Label(row, text="hours / week", bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(side="left", padx=8)

        self.make_button(card, "SAVE GOALS", self.save_goals, bg=COLORS["green"], fg=COLORS["white"]).pack(anchor="w", pady=(20, 0))

    def save_goals(self):
        try:
            for category, variable in self.goal_vars.items():
                hours = float(variable.get().strip() or 0)
                if hours < 0:
                    raise ValueError
                self.save_goal(category, round(hours * 60))
        except ValueError:
            messagebox.showerror("Invalid goal", "Enter a positive number of hours, for example 5 or 2.5.")
            return
        messagebox.showinfo("Saved", "Your weekly goals have been saved.")
        self.show_dashboard()

    # ---------------- ANALYTICS SCREEN ----------------

    def show_analytics(self):
        self.clear_content()
        self.set_active_nav("INSIGHTS")

        total = self.total_current_month()
        self.build_subpage_header(
            "Your Time, Visualized",
            f"{self.format_hours(total)} total tracked this month across all categories."
        )

        body = tk.Frame(self.content, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, pady=(4, 0))

        # Left breakdown chart card
        left = self.build_styled_card(body, bg=COLORS["card"], border=COLORS["card_border"], side="left", expand=True, padx_outer=(0, 6))

        tk.Label(
            left, text="CATEGORY BREAKDOWN", bg=COLORS["card"],
            fg=COLORS["text"], font=("Segoe UI", 9, "bold")
        ).pack(anchor="w")

        canvas = tk.Canvas(left, bg=COLORS["card"], highlightthickness=0)
        canvas.pack(fill="both", expand=True, pady=(6, 0))
        self.draw_category_graph(canvas)

        # Right Quick Audit Card
        right = self.build_styled_card(body, bg=COLORS["mint_card"], border=COLORS["mint_border"], side="right", expand=True, padx_outer=(6, 0))

        tk.Label(
            right, text="your month at a glance", bg=COLORS["mint_card"],
            fg=COLORS["text"], font=("Trebuchet MS", 20, "bold")
        ).pack(anchor="w")

        total_minutes = self.total_current_month()
        most_used, most_minutes = self.most_used_category_current_month()

        stats = [
            ("Total tracked", self.format_hours(total_minutes)),
            ("Top category", most_used if most_used else "None yet"),
            ("Top category time", self.format_hours(most_minutes)),
            ("Active days this month", str(self.active_days_current_month())),
        ]

        for label, value in stats:
            box = tk.Frame(right, bg=COLORS["white"], highlightbackground=COLORS["mint_border"], highlightthickness=1, padx=10, pady=8)
            box.pack(fill="x", pady=5)

            tk.Label(box, text=label, bg=COLORS["white"], fg=COLORS["muted"], font=("Segoe UI", 8)).pack(anchor="w")
            tk.Label(box, text=value, bg=COLORS["white"], fg=COLORS["text"], font=("Segoe UI", 12, "bold")).pack(anchor="w", pady=(2, 0))

    # ---------------- MONTHLY REVIEW SCREEN ----------------

    def show_monthly_audit(self):
        self.clear_content()
        self.set_active_nav("MONTHLY REVIEW")

        self.build_subpage_header(
            "Monthly Review",
            "See how your time this month compares with last month."
        )

        top = tk.Frame(self.content, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 10))

        current_minutes = self.total_current_month()
        previous_minutes = self.total_previous_month()

        cards = [
            ("THIS MONTH", self.format_hours(current_minutes), COLORS["yellow_card"], COLORS["yellow_border"]),
            ("LAST MONTH", self.format_hours(previous_minutes), COLORS["pink_card"], COLORS["pink_border"]),
            ("CHANGE", self.month_change_text(current_minutes, previous_minutes), COLORS["mint_card"], COLORS["mint_border"]),
        ]

        for title, value, bg_col, b_col in cards:
            c = self.build_styled_card(top, bg=bg_col, border=b_col, side="left", expand=True, padx_outer=(0, 6))
            tk.Label(c, text=title, bg=bg_col, fg=COLORS["muted"], font=("Segoe UI", 8, "bold")).pack(anchor="w")
            tk.Label(c, text=value, bg=bg_col, fg=COLORS["text"], font=("Segoe UI", 16, "bold")).pack(anchor="w", pady=(4, 0))

        lower = tk.Frame(self.content, bg=COLORS["bg"])
        lower.pack(fill="both", expand=True)

        report = self.build_styled_card(lower, bg=COLORS["card"], border=COLORS["card_border"], expand=True)

        self.make_button(
            report, "DOWNLOAD MONTHLY REVIEW", self.download_monthly_review,
            bg=COLORS["green"], fg=COLORS["white"], font=("Segoe UI", 9, "bold"),
            padx=14, pady=7
        ).pack(anchor="w", pady=(0, 12))

        tk.Label(
            report, text="WHAT THE NUMBERS SAY", bg=COLORS["card"],
            fg=COLORS["text"], font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(0, 6))

        for insight in self.generate_insights():
            tk.Label(
                report, text="• " + insight, bg=COLORS["card"], fg=COLORS["text"],
                font=("Segoe UI", 10), wraplength=850, justify="left"
            ).pack(anchor="w", pady=4)

    def download_monthly_review(self):
        today = date.today()
        month_start = today.replace(day=1)
        activities = self.get_activities(month_start.isoformat(), today.isoformat())
        filename = f"monthly-review-{today.strftime('%Y-%m')}.csv"
        path = filedialog.asksaveasfilename(
            title="Save Monthly Review",
            initialfile=filename,
            defaultextension=".csv",
            filetypes=[("CSV file", "*.csv"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as output:
                writer = csv.writer(output)
                writer.writerow(["Activity", "Category", "Time", "Date"])
                for _, activity, category, duration, activity_date, _ in activities:
                    writer.writerow([activity, category, self.format_minutes(duration), activity_date])
        except OSError:
            messagebox.showerror("Couldn't Download Review", "The review could not be saved. Please try another location.")
            return

        messagebox.showinfo(
            "Monthly Review Ready",
            f"Your monthly review was saved with {len(activities)} activities."
        )

    def show_rewards(self):
        self.clear_content()
        self.set_active_nav("REWARDS")
        self.build_subpage_header(
            "Rewards",
            "Build a daily habit and earn points for staying consistent."
        )

        days, points = self.consistency_days_and_points()
        body = tk.Frame(self.content, bg=COLORS["bg"])
        body.pack(fill="both", expand=True)

        summary = self.build_styled_card(
            body, bg=COLORS["pink_card"], border=COLORS["pink_border"], expand=False,
            padx_outer=(0, 0), pady_outer=(0, 12)
        )
        tk.Label(summary, text="YOUR POINTS", bg=COLORS["pink_card"], fg=COLORS["text"],
                 font=("Segoe UI", 9, "bold")).pack(anchor="w")
        tk.Label(summary, text=str(points), bg=COLORS["pink_card"], fg=COLORS["text"],
                 font=("Trebuchet MS", 34, "bold")).pack(anchor="w", pady=(2, 0))
        tk.Label(summary, text=f"Day {days} of your current 100-day consistency cycle",
                 bg=COLORS["pink_card"], fg=COLORS["text"], font=("Segoe UI", 10)).pack(anchor="w")

        details = self.build_styled_card(
            body, bg=COLORS["card"], border=COLORS["card_border"], expand=True,
            padx_outer=(0, 0)
        )
        tk.Label(details, text="HOW TO EARN POINTS", bg=COLORS["card"], fg=COLORS["text"],
                 font=("Trebuchet MS", 18, "bold")).pack(anchor="w", pady=(0, 12))
        tk.Label(details, text="Log at least 60 minutes in a day to count that day toward your consistency.",
                 bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10),
                 wraplength=760, justify="left").pack(anchor="w", pady=(0, 14))

        for milestone, award in ((25, 3), (50, 5), (75, 7), (100, 10)):
            row = tk.Frame(details, bg=COLORS["white_soft"], padx=12, pady=9)
            row.pack(fill="x", pady=4)
            reached = days >= milestone or (milestone == 100 and points >= 25)
            status = "Earned" if reached else f"{milestone - days} days to go"
            tk.Label(row, text=f"{milestone} days", bg=COLORS["white_soft"], fg=COLORS["text"],
                     font=("Segoe UI", 10, "bold")).pack(side="left")
            tk.Label(row, text=f"+{award} points", bg=COLORS["white_soft"], fg=COLORS["purple"],
                     font=("Segoe UI", 10, "bold")).pack(side="left", padx=30)
            tk.Label(row, text=status, bg=COLORS["white_soft"], fg=COLORS["green"] if reached else COLORS["muted"],
                     font=("Segoe UI", 9, "bold")).pack(side="right")

        tk.Label(
            details,
            text="After 100 days, a new cycle starts at day 1. Your earned points stay with you.\n\nWith these points, you can claim vouchers on our website.",
            bg=COLORS["mint_card"], fg=COLORS["text"], font=("Segoe UI", 10, "bold"),
            wraplength=760, justify="left", padx=14, pady=12
        ).pack(fill="x", pady=(18, 0))

    # ---------------- SETTINGS SCREEN ----------------

    def show_settings(self):
        self.clear_content()
        self.set_active_nav("SETTINGS")

        self.build_subpage_header(
            "Settings & Preferences",
            f"Customize your profile display name, categories, and colors ({self.current_user_email or self.current_username})."
        )

        card_wrapper = tk.Frame(self.content, bg=COLORS["bg"])
        card_wrapper.pack(fill="both", expand=True, pady=(4, 0))

        tk.Frame(card_wrapper, bg=COLORS["shadow"]).place(x=3, y=3, relwidth=1, relheight=1)

        card = tk.Frame(
            card_wrapper,
            bg=COLORS["card"],
            highlightbackground=COLORS["card_border"],
            highlightthickness=1,
            padx=28,
            pady=20
        )
        card.place(x=0, y=0, relwidth=1, relheight=1)

        # Top Actions Bar
        top_btns = tk.Frame(card, bg=COLORS["card"])
        top_btns.pack(fill="x", pady=(0, 12))

        self.make_button(
            top_btns, "SAVE ALL SETTINGS", self.save_settings,
            bg=COLORS["green"], fg=COLORS["white"]
        ).pack(side="left")

        self.make_button(
            top_btns, "LOG OUT", self.logout,
            bg=COLORS["danger_light"], fg=COLORS["danger"], hover_bg=COLORS["danger_border"],
            bd=1, relief="solid"
        ).pack(side="right")

        form = tk.Frame(card, bg=COLORS["card"])
        form.pack(anchor="w", fill="x")

        self.name_entry = self.add_form_row(
            form, "Display name", entry_width=44
        )
        self.name_entry.insert(0, self.user_name or self.current_username)

        categories_row = tk.Frame(form, bg=COLORS["card"])
        categories_row.pack(anchor="w", pady=8, fill="x")
        tk.Label(
            categories_row, text="Categories", bg=COLORS["card"],
            fg=COLORS["text"], font=("Segoe UI", 9, "bold"), width=18, anchor="w"
        ).pack(side="left")

        self.categories_entry = tk.Entry(
            categories_row, width=44, font=("Segoe UI", 10), relief="solid", bd=1,
            bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"]
        )
        self.categories_entry.pack(side="left")
        self.categories_entry.insert(0, ", ".join(self.custom_categories))

        tk.Label(
            card, text="Category Colors", bg=COLORS["card"],
            fg=COLORS["text"], font=("Segoe UI", 9, "bold")
        ).pack(anchor="w", pady=(10, 4))

        color_canvas = tk.Canvas(card, height=130, bg=COLORS["card_subtle"], highlightthickness=1, highlightbackground=COLORS["card_border"])
        color_scroll = ttk.Scrollbar(card, orient="vertical", command=color_canvas.yview)
        color_rows = tk.Frame(color_canvas, bg=COLORS["card_subtle"])
        color_rows.bind("<Configure>", lambda event: color_canvas.configure(scrollregion=color_canvas.bbox("all")))
        color_canvas.create_window((0, 0), window=color_rows, anchor="nw")
        color_canvas.configure(yscrollcommand=color_scroll.set)
        color_canvas.pack(side="left", fill="x", expand=True)
        color_scroll.pack(side="right", fill="y")

        self.category_color_vars = {}
        for category in self.custom_categories:
            row = tk.Frame(color_rows, bg=COLORS["card_subtle"])
            row.pack(anchor="w", pady=2, padx=8)

            tk.Label(row, text=category, bg=COLORS["card_subtle"], fg=COLORS["text"], width=16, anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")

            variable = tk.StringVar(value=self.category_color(category))
            self.category_color_vars[category] = variable

            swatch = tk.Label(row, width=3, bg=variable.get(), relief="solid", bd=1)
            swatch.pack(side="left", padx=(0, 6))

            entry = tk.Entry(row, textvariable=variable, width=10, font=("Segoe UI", 9), bg=COLORS["white"], fg=COLORS["text"], insertbackground=COLORS["text"])
            entry.pack(side="left")

            self.make_button(
                row, "CHOOSE", lambda v=variable, s=swatch: self.pick_category_color(v, s),
                bg=COLORS["white"], fg=COLORS["text"], hover_bg=COLORS["header_bg"],
                font=("Segoe UI", 8, "bold"), padx=8, pady=2, bd=1, relief="solid"
            ).pack(side="left", padx=6)

    def save_settings(self):
        name = self.name_entry.get().strip() or self.current_username
        categories = [
            item.strip() for item in self.categories_entry.get().split(",") if item.strip()
        ]
        if not categories:
            messagebox.showwarning("Missing categories", "Enter at least one category, separated by commas.")
            return

        colors = {
            category: self.category_color_vars.get(
                category,
                tk.StringVar(value=self.category_color(category))
            ).get().strip()
            for category in categories
        }
        invalid = [color for color in colors.values() if not self.is_hex_color(color)]
        if invalid:
            messagebox.showwarning("Invalid colour", "Choose a color from the color picker or enter a valid color.")
            return

        # Save to Supabase
        if self.current_user_id and is_configured():
            try:
                client = get_supabase()
                # Delete removed categories
                client.table("categories").delete().eq("user_id", self.current_user_id).not_.in_("name", categories).execute()
                # Upsert current categories & colors
                for cat in categories:
                    client.table("categories").upsert({
                        "user_id": self.current_user_id,
                        "name": cat,
                        "color": colors[cat]
                    }, on_conflict="user_id,name").execute()
            except Exception as ex:
                messagebox.showerror("Couldn't Save Settings", "Your categories could not be saved. Please try again.")
                return

        self.user_name = name
        self.custom_categories = categories
        self.custom_category_colors = colors

        self.dashboard_title_label.config(
            text=f"{self.user_name.upper()}'S DASHBOARD" if self.user_name else "OCCUPIED DASHBOARD"
        )
        self.root.title(f"{self.user_name}'s Life Audit" if self.user_name else "Occupied")
        messagebox.showinfo("Saved", "Your settings have been saved.")
        self.show_dashboard()

    # ---------------- GRAPHS & VISUALIZATIONS ----------------

    def draw_week_graph(self, canvas):
        canvas.delete("all")

        start = date.today() - timedelta(days=6)
        data = []

        for i in range(7):
            d = start + timedelta(days=i)
            rows = self.get_activities(d.isoformat(), d.isoformat())
            total = sum(row[3] for row in rows)
            data.append((d.strftime("%a")[0], total))

        canvas.update_idletasks()
        width = max(canvas.winfo_width(), 340)
        height = max(canvas.winfo_height(), 70)

        left = 32
        bottom = height - 22
        graph_h = height - 48
        max_minutes = max([x[1] for x in data] + [60])

        for i in range(4):
            y = bottom - (graph_h * i / 3)
            canvas.create_line(left, y, width - 12, y, fill="#EFE8F6")

        bar_width = max(18, int((width - 70) / 9))

        for i, (label, minutes) in enumerate(data):
            x = left + 14 + i * ((width - 55) / 7)
            bar_h = (minutes / max_minutes) * graph_h if max_minutes else 0

            # Elevated bar
            canvas.create_rectangle(
                x, bottom - bar_h,
                x + bar_width, bottom,
                fill=COLORS["purple"],
                outline=""
            )

            canvas.create_text(
                x + bar_width / 2,
                bottom + 10,
                text=label,
                fill=COLORS["muted"],
                font=("Segoe UI", 8)
            )

            if minutes:
                canvas.create_text(
                    x + bar_width / 2,
                    bottom - bar_h - 7,
                    text=self.format_hours_short(minutes),
                    fill=COLORS["text"],
                    font=("Segoe UI", 7, "bold")
                )

    def draw_category_graph(self, canvas):
        canvas.delete("all")
        canvas.update_idletasks()

        width = max(canvas.winfo_width(), 360)
        height = max(canvas.winfo_height(), 260)

        today = date.today()
        month_start = today.replace(day=1)
        rows = self.get_activities(month_start.isoformat(), today.isoformat())

        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]

        max_value = max(totals.values()) if totals else 1
        y = 20

        for category in self.get_category_options():
            color = self.category_color(category)
            minutes = totals.get(category, 0)
            canvas.create_text(
                6, y + 8,
                text=category,
                anchor="w",
                fill=COLORS["text"],
                font=("Segoe UI", 9, "bold")
            )

            bar_start = 100
            bar_max = width - 150
            bar_width = (minutes / max_value) * bar_max if max_value else 0

            # Background bar lane
            canvas.create_rectangle(
                bar_start, y + 2,
                bar_start + bar_max, y + 14,
                fill=COLORS["card_subtle"],
                outline=""
            )

            # Active fill
            canvas.create_rectangle(
                bar_start, y + 2,
                bar_start + max(bar_width, 2), y + 14,
                fill=color,
                outline=""
            )

            canvas.create_text(
                width - 6, y + 8,
                text=self.format_hours_short(minutes),
                anchor="e",
                fill=COLORS["muted"],
                font=("Segoe UI", 8)
            )

            y += 34

    # ---------------- GENERAL HELPERS ----------------

    def get_today_activities(self):
        today = date.today().isoformat()
        return self.get_activities(today, today)

    def is_hex_color(self, color):
        if len(color) != 7 or not color.startswith("#"):
            return False
        try:
            int(color[1:], 16)
            return True
        except ValueError:
            return False

    def pick_category_color(self, variable, swatch):
        selected = colorchooser.askcolor(initialcolor=variable.get(), parent=self.root)[1]
        if selected:
            variable.set(selected.upper())
            swatch.config(bg=selected)

    def category_color(self, category):
        saved_color = getattr(self, "custom_category_colors", {}).get(category)
        if saved_color and self.is_hex_color(saved_color):
            return saved_color
        for name, color in CATEGORIES:
            if name == category:
                return color
        custom_colors = ["#8E5FE6", "#EA588C", "#36B37E", "#4E95E6", "#F7B928", "#FF7D6B"]
        return custom_colors[sum(ord(char) for char in category) % len(custom_colors)]

    def format_minutes(self, minutes):
        hours = minutes // 60
        mins = minutes % 60
        if hours and mins:
            return f"{hours}h {mins}m"
        if hours:
            return f"{hours}h"
        return f"{mins}m"

    def format_hours(self, minutes):
        return self.format_minutes(minutes)

    def format_hours_short(self, minutes):
        if minutes >= 60:
            hours = minutes / 60
            if hours.is_integer():
                return f"{int(hours)}h"
            return f"{hours:.1f}h"
        return f"{minutes}m"

    def current_week_range(self):
        today = date.today()
        start = today - timedelta(days=today.weekday())
        end = start + timedelta(days=6)
        return start, end

    def total_current_month(self):
        today = date.today()
        start = today.replace(day=1)
        return sum(row[3] for row in self.get_activities(start.isoformat(), today.isoformat()))

    def total_previous_month(self):
        today = date.today()
        if today.month == 1:
            year = today.year - 1
            month = 12
        else:
            year = today.year
            month = today.month - 1
        start = date(year, month, 1)
        end = date(year, month, calendar.monthrange(year, month)[1])
        return sum(row[3] for row in self.get_activities(start.isoformat(), end.isoformat()))

    def month_change_text(self, current, previous):
        if previous == 0:
            return "New baseline"
        change = round(((current - previous) / previous) * 100)
        if change > 0:
            return f"+{change}%"
        return f"{change}%"

    def active_days_current_month(self):
        today = date.today()
        start = today.replace(day=1)
        rows = self.get_activities(start.isoformat(), today.isoformat())
        return len(set(row[4] for row in rows))

    def most_used_category_current_month(self):
        today = date.today()
        start = today.replace(day=1)
        rows = self.get_activities(start.isoformat(), today.isoformat())
        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]
        if not totals:
            return None, 0
        category = max(totals, key=totals.get)
        return category, totals[category]

    def generate_insights(self):
        today = date.today()
        start = today.replace(day=1)
        rows = self.get_activities(start.isoformat(), today.isoformat())
        if not rows:
            return [
                "You haven't logged anything this month yet.",
                "Start recording your activities and your first overview will build itself.",
                "Remember: the goal is awareness, not perfection."
            ]
        total = sum(row[3] for row in rows)
        category, category_minutes = self.most_used_category_current_month()
        active_days = self.active_days_current_month()
        insights = [
            f"You have tracked {self.format_hours(total)} across {active_days} active day(s) this month."
        ]
        if category:
            percentage = round((category_minutes / total) * 100) if total else 0
            insights.append(
                f"{category} is currently your biggest category at {self.format_hours(category_minutes)} ({percentage}% of tracked time)."
            )
        today_rows = self.get_today_activities()
        if today_rows:
            today_total = sum(row[3] for row in today_rows)
            insights.append(
                f"Today you have logged {self.format_hours(today_total)}. Keep logging honestly — the pattern matters more than any single day."
            )
        return insights

    def refresh_all(self):
        self.date_label.config(
            text=datetime.now().strftime("%A • %d %B %Y")
        )
        self.show_dashboard()

    def close_app(self):
        self.root.destroy()


OccupiedApp = LifeAuditApp

if __name__ == "__main__":
    root = tk.Tk()
    app = LifeAuditApp(root)
    root.mainloop()
