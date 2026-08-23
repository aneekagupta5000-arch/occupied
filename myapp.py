import tkinter as tk
from tkinter import ttk, messagebox, colorchooser
import sqlite3
import json
import random
from datetime import datetime, date, timedelta
import calendar
from pathlib import Path
import time

# ============================================================
# PERSONAL TIME AUDIT
# Version 1 - Tkinter + SQLite
# ============================================================

# Keep the database next to this program, so settings persist regardless of
# which folder the app is launched from.
DB_NAME = str(Path(__file__).with_name("life_audit.db"))

COLORS = {
    "bg": "#E1D0E3",
    "outer": "#B895F4",
    "card": "#F3E2F0",
    "pink": "#F23BBE",
    "pink_dark": "#A9438B",
    "mint": "#C8DEDA",
    "yellow": "#FFE7A3",
    "green": "#55C86A",
    "green_dark": "#39A94D",
    "text": "#24202A",
    "muted": "#6F6574",
    "white": "#FFFFFF",
    "line": "#7B7180",
    "blue": "#5AA9E6",
    "orange": "#F5B82E",
}

CATEGORIES = [
    ("Work", COLORS["green"]),
    ("Gym", COLORS["orange"]),
    ("Study", COLORS["blue"]),
    ("Project", "#A978E8"),
    ("Design", "#E58CC2"),
    ("Entertainment", "#FF8B7B"),
    ("Other", "#9B9B9B"),
]


class LifeAuditApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Life Audit")
        self.root.geometry("1180x760")
        self.root.minsize(1000, 680)
        self.root.configure(bg=COLORS["outer"])

        self.conn = sqlite3.connect(DB_NAME)
        self.timer_running = False
        self.timer_started_at = None
        self.timer_elapsed = 0
        self.create_database()

        self.setup_styles()
        self.load_settings()
        self.root.title(f"{self.user_name}'s Life Audit")
        self.build_ui()
        if not self.user_name or not self.custom_categories:
            self.show_settings()
        else:
            self.refresh_all()

        self.root.protocol("WM_DELETE_WINDOW", self.close_app)

    # ---------------- DATABASE ----------------

    def create_database(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS activities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity TEXT NOT NULL,
                category TEXT NOT NULL,
                duration INTEGER NOT NULL,
                activity_date TEXT NOT NULL,
                notes TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS goals (
                category TEXT PRIMARY KEY,
                weekly_minutes INTEGER NOT NULL
            )
        """)
        self.conn.commit()

    def add_activity_to_db(self, activity, category, duration, activity_date, notes):
        self.conn.execute(
            """INSERT INTO activities
               (activity, category, duration, activity_date, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (activity, category, duration, activity_date, notes)
        )
        self.conn.commit()

    def get_activities(self, start_date=None, end_date=None):
        query = "SELECT * FROM activities"
        params = []

        if start_date and end_date:
            query += " WHERE activity_date BETWEEN ? AND ?"
            params = [start_date, end_date]

        query += " ORDER BY activity_date DESC, id DESC"
        return self.conn.execute(query, params).fetchall()

    def update_activity_in_db(self, activity_id, activity, category, duration, activity_date, notes):
        self.conn.execute("""UPDATE activities SET activity=?, category=?, duration=?,
                           activity_date=?, notes=? WHERE id=?""",
                          (activity, category, duration, activity_date, notes, activity_id))
        self.conn.commit()

    def delete_activity_from_db(self, activity_id):
        self.conn.execute("DELETE FROM activities WHERE id = ?", (activity_id,))
        self.conn.commit()

    def get_goal(self, category):
        row = self.conn.execute("SELECT weekly_minutes FROM goals WHERE category = ?", (category,)).fetchone()
        return row[0] if row else 0

    def save_goal(self, category, minutes):
        self.conn.execute("INSERT OR REPLACE INTO goals (category, weekly_minutes) VALUES (?, ?)",
                          (category, minutes))
        self.conn.commit()

    # ---------------- UI STYLE ----------------

    def setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        style.configure(
            "TCombobox",
            fieldbackground=COLORS["white"],
            background=COLORS["white"],
            foreground=COLORS["text"],
            padding=7
        )

        style.configure(
            "Treeview",
            background=COLORS["white"],
            fieldbackground=COLORS["white"],
            foreground=COLORS["text"],
            rowheight=32,
            font=("Segoe UI", 10)
        )

        style.configure(
            "Treeview.Heading",
            background=COLORS["pink"],
            foreground=COLORS["text"],
            font=("Segoe UI", 10, "bold")
        )

    def make_button(self, parent, text, command, bg=COLORS["pink"], width=None):
        button = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg=COLORS["text"],
            activebackground=bg,
            activeforeground=COLORS["text"],
            relief="flat",
            bd=0,
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=16,
            pady=9
        )
        if width:
            button.config(width=width)
        return button

    def make_card(self, parent, bg=COLORS["card"], padx=18, pady=15):
        return tk.Frame(
            parent,
            bg=bg,
            highlightbackground=COLORS["line"],
            highlightthickness=1,
            padx=padx,
            pady=pady
        )

    # ---------------- MAIN UI ----------------

    def build_ui(self):
        outer = tk.Frame(self.root, bg=COLORS["outer"], padx=18, pady=18)  # lavender app frame
        outer.pack(fill="both", expand=True)

        self.menu_width = 260  # width for the side menu panel
        self.menu_visible = False  # menu starts hidden offscreen

        self.menu_frame = tk.Frame(
            outer,
            bg="#B895F4",  # purple menu background
            width=self.menu_width,
            padx=16,
            pady=20
        )
        self.menu_frame.place(x=-self.menu_width, y=0, relheight=1)  # hide menu off-left edge
        self.menu_frame.lift()  # ensure menu sits above content
        self.menu_frame.pack_propagate(False)

        menu_header = tk.Frame(self.menu_frame, bg="#B895F4")  # header area inside the menu
        menu_header.pack(fill="x", pady=(0, 24))

        tk.Label(
            menu_header,
            text="⭐",
            bg="#B895F4",
            fg="#E9A600",
            font=("Segoe UI Emoji", 36)
        ).pack()  # star icon in menu header

        tk.Label(
            menu_header,
            text="MENU",
            bg="#B895F4",
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold")
        ).pack(pady=(8, 0))  # menu title text

        close_button = tk.Button(
            menu_header,
            text="✕",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            bd=0,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            command=self.toggle_menu
        )
        close_button.pack(pady=(12, 0))  # close button to hide menu

        self.nav_buttons = {}
        for name, command in [
            ("HOME", self.show_dashboard),
            ("ADD A ACTIVITY", self.show_add_activity),
            ("ACTIVITY HISTORY", self.show_history),
            ("WEEKLY GOALS", self.show_goals),
            ("ANALYTICS", self.show_analytics),
            ("MONTHLY AUDIT", self.show_monthly_audit),
        ]:
            b = self.make_button(
                self.menu_frame,
                name,
                command,
                bg=COLORS["pink"],
                width=24
            )
            b.pack(fill="x", pady=8)
            self.nav_buttons[name] = b  # keep reference for active state

        settings_button = self.make_button(
            self.menu_frame,
            "SETTINGS",
            self.show_settings,
            bg=COLORS["white"],
            width=24
        )
        settings_button.pack(fill="x", pady=12)  # extra CTA button
        self.nav_buttons["SETTINGS"] = settings_button

        self.main = tk.Frame(
            outer,
            bg=COLORS["bg"],
            highlightbackground="#8056D8",
            highlightthickness=3,
            padx=24,
            pady=24
        )
        self.main.pack(side="left", fill="both", expand=True, padx=(12, 0))  # main content panel
        self.menu_frame.lift(self.main)  # keep menu on top of main content

        header = tk.Frame(self.main, bg=COLORS["bg"])  # top bar in main panel
        header.pack(fill="x", pady=(0, 12))

        self.menu_toggle_button = tk.Button(
            header,
            text="⭐",
            bg=COLORS["bg"],
            fg="#E9A600",
            bd=0,
            relief="flat",
            activebackground=COLORS["bg"],
            cursor="hand2",
            font=("Segoe UI Emoji", 18),
            command=self.toggle_menu
        )
        self.menu_toggle_button.pack(side="left")  # open/close menu toggle

        dashboard_title = f"{self.user_name.upper()}'S DASHBOARD" if self.user_name else "DASHBOARD"
        self.dashboard_title_label = tk.Label(
            header,
            text=dashboard_title,
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 11, "bold")
        )
        self.dashboard_title_label.pack(side="left", padx=12)  # page title

        self.date_label = tk.Label(
            header,
            text="",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10)
        )
        self.date_label.pack(side="right")  # date text on header

        self.content = tk.Frame(self.main, bg=COLORS["bg"])  # body container for pages
        self.content.pack(fill="both", expand=True)

    def toggle_menu(self):
        if self.menu_visible:
            self.menu_frame.place_forget()  # hide menu immediately and clean up any imprint
        else:
            self.menu_frame.place(x=0, y=0, relheight=1)  # show menu instantly
            self.menu_frame.lift()  # keep menu above other content
        self.menu_visible = not self.menu_visible

    def animate_menu(self, target_x):
        # legacy helper kept for compatibility, not used in current implementation
        pass

    def talk_to_ai(self):
        messagebox.showinfo(
            "Talk to AI",
            "AI chat integration is not implemented yet."
        )

    def load_setting(self, key, default=None):
        row = self.conn.execute(
            "SELECT value FROM settings WHERE key = ?",
            (key,)
        ).fetchone()
        return row[0] if row else default

    def save_setting(self, key, value):
        self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value)
        )
        self.conn.commit()

    def load_settings(self):
        self.user_name = self.load_setting("username", "Aneeka")

        categories_raw = self.load_setting(
            "categories",
            ", ".join(name for name, _ in CATEGORIES)
        )
        self.custom_categories = [
            item.strip() for item in categories_raw.split(",") if item.strip()
        ]
        if not self.custom_categories:
            self.custom_categories = [name for name, _ in CATEGORIES]
        try:
            self.custom_category_colors = json.loads(self.load_setting("category_colors", "{}"))
        except json.JSONDecodeError:
            self.custom_category_colors = {}

    def get_category_options(self):
        return self.custom_categories or [name for name, _ in CATEGORIES]

    def save_settings(self):
        name = self.name_entry.get().strip() or "Aneeka"
        categories = [
            item.strip() for item in self.categories_entry.get().split(",") if item.strip()
        ]
        if not categories:
            messagebox.showwarning(
                "Missing categories",
                "Enter at least one category, separated by commas."
            )
            return

        # A category edited in Settings should also rename existing activity records.
        old_categories = list(self.custom_categories)
        for old_name, new_name in zip(old_categories, categories):
            if old_name != new_name:
                self.conn.execute("UPDATE activities SET category = ? WHERE category = ?", (new_name, old_name))
                old_goal = self.get_goal(old_name)
                if old_goal and new_name not in old_categories:
                    self.save_goal(new_name, old_goal)
                self.conn.execute("DELETE FROM goals WHERE category = ?", (old_name,))
        self.conn.commit()

        self.save_setting("username", name)
        self.save_setting("categories", ", ".join(categories))
        colors = {
            category: self.category_color_vars.get(category, tk.StringVar(value=self.category_color(category))).get().strip()
            for category in categories
        }
        invalid = [color for color in colors.values() if not self.is_hex_color(color)]
        if invalid:
            messagebox.showwarning("Invalid colour", "Use a colour such as #E48AC4, or choose one using the picker.")
            return
        self.save_setting("category_colors", json.dumps(colors))
        self.load_settings()
        self.dashboard_title_label.config(
            text=f"{self.user_name.upper()}'S DASHBOARD" if self.user_name else "DASHBOARD"
        )
        self.root.title(f"{self.user_name}'s Life Audit")
        messagebox.showinfo("Saved", "Settings updated successfully.")
        self.show_dashboard()

    def show_settings(self):
        self.clear_content()
        self.set_active_nav("SETTINGS")

        card = self.make_card(self.content, bg=COLORS["card"], padx=28, pady=25)
        card.pack(fill="both", expand=True)

        tk.Label(
            card,
            text="App settings",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 24, "bold")
        ).pack(anchor="w")

        tk.Label(
            card,
            text="Choose your name and categories here. You can edit them anytime.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(0, 20))

        # This stays at the top, so saving is always easy even with many categories.
        self.make_button(
            card,
            "SAVE ALL SETTINGS",
            self.save_settings,
            bg=COLORS["green"]
        ).pack(anchor="e", pady=(0, 10))

        form = tk.Frame(card, bg=COLORS["card"])
        form.pack(anchor="w", fill="x")

        self.name_entry = self.add_form_row(
            form,
            "Your name",
            row_bg=COLORS["card"],
            entry_width=50
        )
        self.name_entry.insert(0, self.user_name or "Aneeka")

        categories_row = tk.Frame(form, bg=COLORS["card"])
        categories_row.pack(anchor="w", pady=10, fill="x")
        tk.Label(
            categories_row,
            text="Categories",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold"),
            width=16,
            anchor="w"
        ).pack(side="left")

        self.categories_entry = tk.Entry(
            categories_row,
            width=50,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1
        )
        self.categories_entry.pack(side="left")
        self.categories_entry.insert(0, ", ".join(self.custom_categories))

        tk.Label(
            card,
            text="Enter category names separated by commas. Then choose a colour for each category.",
            bg=COLORS["card"],
            fg=COLORS["muted"],
            font=("Segoe UI", 9)
        ).pack(anchor="w", pady=(6, 0))

        self.category_color_vars = {}
        color_card = tk.Frame(card, bg=COLORS["card"])
        color_card.pack(anchor="w", fill="x", pady=(18, 0))
        tk.Label(color_card, text="Category colours", bg=COLORS["card"], fg=COLORS["text"],
                 font=("Segoe UI", 10, "bold")).pack(anchor="w", pady=(0, 5))
        tk.Label(color_card, text="Scroll to see every category. Add new names above, save, then return here to choose their colours.",
                 bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w", pady=(0, 6))

        color_canvas = tk.Canvas(color_card, height=155, bg=COLORS["card"], highlightthickness=1,
                                 highlightbackground=COLORS["line"])
        color_scroll = ttk.Scrollbar(color_card, orient="vertical", command=color_canvas.yview)
        color_rows = tk.Frame(color_canvas, bg=COLORS["card"])
        color_rows.bind("<Configure>", lambda event: color_canvas.configure(scrollregion=color_canvas.bbox("all")))
        color_canvas.create_window((0, 0), window=color_rows, anchor="nw")
        color_canvas.configure(yscrollcommand=color_scroll.set)
        color_canvas.pack(side="left", fill="x", expand=True)
        color_scroll.pack(side="right", fill="y")
        color_canvas.bind("<MouseWheel>", lambda event: color_canvas.yview_scroll(int(-event.delta / 120), "units"))

        for category in self.custom_categories:
            row = tk.Frame(color_rows, bg=COLORS["card"])
            row.pack(anchor="w", pady=3)
            tk.Label(row, text=category, bg=COLORS["card"], fg=COLORS["text"], width=18,
                     anchor="w", font=("Segoe UI", 9, "bold")).pack(side="left")
            variable = tk.StringVar(value=self.category_color(category))
            self.category_color_vars[category] = variable
            swatch = tk.Label(row, width=3, bg=variable.get(), relief="solid", bd=1)
            swatch.pack(side="left", padx=(0, 6))
            entry = tk.Entry(row, textvariable=variable, width=10, font=("Segoe UI", 9))
            entry.pack(side="left")
            self.make_button(row, "PICK", lambda v=variable, s=swatch: self.pick_category_color(v, s),
                             bg=COLORS["mint"]).pack(side="left", padx=7)

        buttons = tk.Frame(card, bg=COLORS["card"])
        buttons.pack(anchor="w", pady=(22, 0))

        self.make_button(
            buttons,
            "SAVE ALL SETTINGS",
            self.save_settings,
            bg=COLORS["green"]
        ).pack(side="left")

    def clear_content(self):
        for widget in self.content.winfo_children():
            widget.destroy()

    # ---------------- GOALS + HISTORY ----------------

    def show_goals(self):
        self.clear_content()
        self.set_active_nav("WEEKLY GOALS")
        card = self.make_card(self.content, bg=COLORS["card"], padx=28, pady=24)
        card.pack(fill="both", expand=True)
        tk.Label(card, text="weekly goals", bg=COLORS["card"], fg=COLORS["text"],
                 font=("Trebuchet MS", 25, "bold")).pack(anchor="w")
        tk.Label(card, text="Set the time you want to give each category every week. Leave at 0 to hide it.",
                 bg=COLORS["card"], fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 18))
        self.goal_vars = {}
        for category in self.get_category_options():
            row = tk.Frame(card, bg=COLORS["card"])
            row.pack(fill="x", pady=6)
            tk.Label(row, text=category, bg=COLORS["card"], fg=COLORS["text"], width=22,
                     anchor="w", font=("Segoe UI", 10, "bold")).pack(side="left")
            var = tk.StringVar(value=str(self.get_goal(category) // 60))
            self.goal_vars[category] = var
            tk.Entry(row, textvariable=var, width=8, font=("Segoe UI", 10)).pack(side="left")
            tk.Label(row, text="hours per week", bg=COLORS["card"], fg=COLORS["muted"],
                     font=("Segoe UI", 9)).pack(side="left", padx=8)
        self.make_button(card, "SAVE GOALS", self.save_goals, bg=COLORS["green"]).pack(anchor="w", pady=(20, 0))

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

    def show_history(self):
        self.clear_content()
        self.set_active_nav("ACTIVITY HISTORY")
        tk.Label(self.content, text="activity history", bg=COLORS["bg"], fg=COLORS["text"],
                 font=("Trebuchet MS", 25, "bold")).pack(anchor="w")
        tk.Label(self.content, text="Select an activity, then edit or delete it.", bg=COLORS["bg"],
                 fg=COLORS["muted"], font=("Segoe UI", 10)).pack(anchor="w", pady=(0, 15))
        card = self.make_card(self.content, bg=COLORS["card"], padx=12, pady=12)
        card.pack(fill="both", expand=True)
        columns = ("date", "activity", "category", "duration", "notes")
        self.history_tree = ttk.Treeview(card, columns=columns, show="headings", selectmode="browse")
        for column, label, width in [("date", "Date", 100), ("activity", "Activity", 190),
                                     ("category", "Category", 120), ("duration", "Duration", 90), ("notes", "Notes", 340)]:
            self.history_tree.heading(column, text=label)
            self.history_tree.column(column, width=width, anchor="w")
        for row in self.get_activities():
            self.history_tree.insert("", "end", iid=str(row[0]), values=(row[4], row[1], row[2], self.format_minutes(row[3]), row[5] or ""))
        self.history_tree.pack(fill="both", expand=True)
        buttons = tk.Frame(card, bg=COLORS["card"])
        buttons.pack(fill="x", pady=(12, 0))
        self.make_button(buttons, "EDIT SELECTED", self.edit_selected_activity, bg=COLORS["yellow"]).pack(side="left")
        self.make_button(buttons, "DELETE SELECTED", self.delete_selected_activity, bg=COLORS["orange"]).pack(side="left", padx=10)

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
            self.show_history()

    def edit_selected_activity(self):
        activity_id = self.selected_activity_id()
        if activity_id is None:
            return
        row = self.conn.execute("SELECT * FROM activities WHERE id = ?", (activity_id,)).fetchone()
        if not row:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title("Edit activity")
        dialog.configure(bg=COLORS["card"])
        dialog.resizable(False, False)
        form = tk.Frame(dialog, bg=COLORS["card"], padx=24, pady=22)
        form.pack()
        tk.Label(form, text="Edit activity", bg=COLORS["card"], fg=COLORS["text"], font=("Trebuchet MS", 20, "bold")).grid(row=0, column=0, columnspan=2, sticky="w", pady=(0, 16))
        fields = {}
        for index, (label, value) in enumerate([("Activity", row[1]), ("Date (YYYY-MM-DD)", row[4]), ("Hours", str(row[3] // 60)), ("Minutes", str(row[3] % 60))], start=1):
            tk.Label(form, text=label, bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=index, column=0, sticky="w", pady=5)
            entry = tk.Entry(form, width=35)
            entry.insert(0, value)
            entry.grid(row=index, column=1, pady=5)
            fields[label] = entry
        tk.Label(form, text="Category", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=5, column=0, sticky="w", pady=5)
        category = tk.StringVar(value=row[2])
        ttk.Combobox(form, textvariable=category, values=self.get_category_options(), state="readonly", width=32).grid(row=5, column=1, pady=5)
        tk.Label(form, text="Notes", bg=COLORS["card"], fg=COLORS["text"], font=("Segoe UI", 9, "bold")).grid(row=6, column=0, sticky="nw", pady=5)
        notes = tk.Text(form, width=35, height=5)
        notes.insert("1.0", row[5] or "")
        notes.grid(row=6, column=1, pady=5)
        def save_edit():
            try:
                duration = int(fields["Hours"].get()) * 60 + int(fields["Minutes"].get())
                datetime.strptime(fields["Date (YYYY-MM-DD)"].get().strip(), "%Y-%m-%d")
                if not fields["Activity"].get().strip() or duration <= 0:
                    raise ValueError
            except ValueError:
                messagebox.showerror("Invalid details", "Enter an activity, valid date, and positive whole-number duration.", parent=dialog)
                return
            self.update_activity_in_db(activity_id, fields["Activity"].get().strip(), category.get(), duration,
                                       fields["Date (YYYY-MM-DD)"].get().strip(), notes.get("1.0", tk.END).strip())
            dialog.destroy()
            self.show_history()
        self.make_button(form, "SAVE CHANGES", save_edit, bg=COLORS["green"]).grid(row=7, column=1, sticky="e", pady=(15, 0))

    def set_active_nav(self, active):
        for name, button in self.nav_buttons.items():
            button.config(bg=COLORS["pink"] if name == active else COLORS["white"])

    # ---------------- DASHBOARD ----------------

    def show_dashboard(self):
        self.clear_content()
        self.set_active_nav("HOME")

        left = tk.Frame(self.content, bg=COLORS["bg"])
        left.pack(side="left", fill="both", expand=True, padx=(0, 12))

        right = tk.Frame(self.content, bg=COLORS["bg"], width=420)
        right.pack(side="right", fill="both", expand=True, padx=(12, 0))

        # Live quote card
        self.build_live_quote_card(left)

        # Recap cards
        recap_row = tk.Frame(left, bg=COLORS["bg"])
        recap_row.pack(fill="x", pady=(0, 12))

        weekly_card = self.make_card(recap_row, bg=COLORS["pink"], padx=14, pady=12)
        weekly_card.pack(side="left", fill="both", expand=True, padx=(0, 6))

        monthly_card = self.make_card(recap_row, bg="#D884BB", padx=14, pady=12)
        monthly_card.pack(side="right", fill="both", expand=True, padx=(6, 0))

        self.build_weekly_recap(weekly_card)
        self.build_monthly_recap(monthly_card)

        # Graph
        graph_card = self.make_card(left, bg=COLORS["card"], padx=12, pady=10)
        graph_card.pack(fill="both", expand=True)

        tk.Label(
            graph_card,
            text="THIS WEEK",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w", padx=5)

        canvas = tk.Canvas(
            graph_card,
            bg=COLORS["card"],
            highlightthickness=0,
            height=175
        )
        canvas.pack(fill="both", expand=True)
        self.draw_week_graph(canvas)

        self.build_task_timer(right)

        # Today card
        today = self.make_card(right, bg=COLORS["mint"], padx=18, pady=18)
        today.pack(fill="both", expand=True)

        tk.Label(
            today,
            text="today :)",
            bg=COLORS["mint"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 25, "bold")
        ).pack(anchor="w")

        tk.Label(
            today,
            text="YOU ARE REMARKABLE",
            bg=COLORS["mint"],
            fg=COLORS["muted"],
            font=("Segoe UI", 8, "italic")
        ).pack(anchor="w", pady=(0, 14))

        activities = self.get_today_activities()

        if not activities:
            tk.Label(
                today,
                text="No activities logged yet.\nStart with one small thing.",
                bg=COLORS["mint"],
                fg=COLORS["muted"],
                font=("Segoe UI", 11),
                justify="left"
            ).pack(anchor="w", pady=25)
        else:
            for row in activities[:6]:
                activity_id, activity, category, duration, activity_date, notes = row
                color = self.category_color(category)

                item = tk.Frame(
                    today,
                    bg=COLORS["white"],
                    highlightbackground=COLORS["line"],
                    highlightthickness=1
                )
                item.pack(fill="x", pady=5)

                tk.Label(
                    item,
                    text="●",
                    fg=color,
                    bg=COLORS["white"],
                    font=("Segoe UI", 18)
                ).pack(side="left", padx=10)

                text_frame = tk.Frame(item, bg=COLORS["white"])
                text_frame.pack(side="left", fill="x", expand=True, pady=8)

                tk.Label(
                    text_frame,
                    text=activity.upper(),
                    bg=COLORS["white"],
                    fg=COLORS["text"],
                    font=("Segoe UI", 10, "bold"),
                    anchor="w"
                ).pack(fill="x")

                tk.Label(
                    text_frame,
                    text=f"{category} • {self.format_minutes(duration)}",
                    bg=COLORS["white"],
                    fg=COLORS["muted"],
                    font=("Segoe UI", 8),
                    anchor="w"
                ).pack(fill="x")

                if notes:
                    tk.Label(
                        text_frame,
                        text=notes,
                        bg=COLORS["white"],
                        fg=COLORS["muted"],
                        font=("Segoe UI", 8),
                        anchor="w",
                        justify="left",
                        wraplength=260
                    ).pack(fill="x", pady=(2, 0))

        self.make_button(
            today,
            "+ ADD ACTIVITY",
            self.show_add_activity,
            bg=COLORS["white"]
        ).pack(anchor="w", pady=(16, 0))

    def build_task_timer(self, parent):
        timer = self.make_card(parent, bg=COLORS["card"], padx=16, pady=13)
        timer.pack(fill="x", pady=(0, 12))
        tk.Label(timer, text="FOCUS TIMER", bg=COLORS["card"], fg=COLORS["muted"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w")
        row = tk.Frame(timer, bg=COLORS["card"])
        row.pack(fill="x", pady=(3, 0))
        self.timer_label = tk.Label(row, text="00:00:00", bg=COLORS["card"], fg=COLORS["text"],
                                    font=("Trebuchet MS", 22, "bold"))
        self.timer_label.pack(side="left")
        controls = tk.Frame(row, bg=COLORS["card"])
        controls.pack(side="right")
        self.timer_start_button = self.make_button(controls, "START", self.toggle_timer, bg=COLORS["green"])
        self.timer_start_button.pack(side="left")
        self.make_button(controls, "RESET", self.reset_timer, bg=COLORS["yellow"]).pack(side="left", padx=(6, 0))
        self.update_timer_display()

    def timer_seconds(self):
        elapsed = self.timer_elapsed
        if self.timer_running and self.timer_started_at is not None:
            elapsed += time.monotonic() - self.timer_started_at
        return int(elapsed)

    def toggle_timer(self):
        if self.timer_running:
            self.timer_elapsed = self.timer_seconds()
            self.timer_started_at = None
            self.timer_running = False
            if hasattr(self, "timer_start_button") and self.timer_start_button.winfo_exists():
                self.timer_start_button.config(text="START")
        else:
            self.timer_started_at = time.monotonic()
            self.timer_running = True
            if hasattr(self, "timer_start_button") and self.timer_start_button.winfo_exists():
                self.timer_start_button.config(text="PAUSE")
        self.update_timer_display()

    def reset_timer(self):
        self.timer_running = False
        self.timer_started_at = None
        self.timer_elapsed = 0
        if hasattr(self, "timer_start_button") and self.timer_start_button.winfo_exists():
            self.timer_start_button.config(text="START")
        self.update_timer_display()

    def update_timer_display(self):
        if not hasattr(self, "timer_label") or not self.timer_label.winfo_exists():
            return
        seconds = self.timer_seconds()
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        self.timer_label.config(text=f"{hours:02}:{minutes:02}:{seconds:02}")
        if self.timer_running:
            self.root.after(250, self.update_timer_display)

    def build_live_quote_card(self, parent):
        quote_card = self.make_card(parent, bg=COLORS["yellow"], padx=20, pady=16)
        quote_card.pack(fill="x", pady=(0, 12))
        self.live_time_label = tk.Label(quote_card, bg=COLORS["yellow"], fg=COLORS["muted"],
                                        font=("Segoe UI", 8, "bold"))
        self.live_time_label.pack(anchor="w")
        quotes = [
            "Small steps still move you forward.",
            "You do not need a perfect day to make progress.",
            "Track your life with curiosity, not criticism.",
            "Rest is part of the plan, not a break from it.",
            "One honest entry is better than no entry.",
            "Your time is yours to shape, one choice at a time.",
            "Consistency grows quietly before it becomes visible."
        ]
        tk.Label(quote_card, text=random.choice(quotes), bg=COLORS["yellow"], fg=COLORS["text"],
                 font=("Trebuchet MS", 15, "italic"), wraplength=520, justify="left").pack(anchor="w", pady=(7, 3))
        tk.Label(quote_card, text="A little reminder for right now.", bg=COLORS["yellow"],
                 fg=COLORS["muted"], font=("Segoe UI", 9)).pack(anchor="w")
        self.update_live_clock()

    def update_live_clock(self):
        if not hasattr(self, "live_time_label") or not self.live_time_label.winfo_exists():
            return
        self.live_time_label.config(text=datetime.now().strftime("RIGHT NOW  •  %A, %d %B  •  %I:%M:%S %p"))
        self.root.after(1000, self.update_live_clock)

    def build_weekly_recap(self, parent):
        tk.Label(
            parent,
            text="this week's recap",
            bg=COLORS["pink"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 11, "bold")
        ).pack(anchor="w")

        start = date.today() - timedelta(days=6)
        end = date.today()
        rows = self.get_activities(start.isoformat(), end.isoformat())

        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]

        for category in self.get_category_options()[:5]:
            minutes = totals.get(category, 0)
            line = tk.Frame(parent, bg=COLORS["pink"])
            line.pack(fill="x", pady=3)

            tk.Label(
                line,
                text=category.lower(),
                bg=COLORS["pink"],
                fg=COLORS["text"],
                font=("Segoe UI", 8)
            ).pack(side="left")

            tk.Label(
                line,
                text=self.format_hours_short(minutes),
                bg=COLORS["pink"],
                fg=COLORS["text"],
                font=("Segoe UI", 8)
            ).pack(side="right")

            self.small_bar(parent, minutes, totals)

        self.build_goal_progress(parent, totals)

    def build_goal_progress(self, parent, totals):
        goals = [(category, self.get_goal(category)) for category in self.get_category_options()]
        goals = [(category, goal) for category, goal in goals if goal > 0]
        if not goals:
            return

        tk.Label(parent, text="weekly goals", bg=COLORS["pink"], fg=COLORS["text"],
                 font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(8, 2))
        for category, goal in goals:
            minutes = totals.get(category, 0)
            progress = min(minutes / goal, 1)
            line = tk.Frame(parent, bg=COLORS["pink"])
            line.pack(fill="x", pady=2)
            tk.Label(line, text=f"{category.lower()}  {self.format_hours_short(minutes)}/{self.format_hours_short(goal)}",
                     bg=COLORS["pink"], fg=COLORS["text"], font=("Segoe UI", 8)).pack(side="left")
            tk.Label(line, text=f"{round(progress * 100)}%", bg=COLORS["pink"], fg=COLORS["text"],
                     font=("Segoe UI", 8, "bold")).pack(side="right")
            bar = tk.Canvas(parent, bg=COLORS["pink"], height=7, highlightthickness=0)
            bar.pack(fill="x", pady=(0, 2))
            bar.create_rectangle(1, 1, max(3, int(120 * progress)), 6,
                                 fill=COLORS["green"] if progress >= 1 else COLORS["blue"], outline="")

    def small_bar(self, parent, minutes, totals):
        max_value = max(totals.values()) if totals and max(totals.values()) > 0 else 1
        canvas = tk.Canvas(
            parent,
            bg=COLORS["pink"],
            height=8,
            highlightthickness=0
        )
        canvas.pack(fill="x", pady=(0, 2), padx=1)
        width = int(120 * minutes / max_value) if minutes else 3
        canvas.create_rectangle(
            1, 1, max(width, 3), 7,
            fill=COLORS["green"] if minutes == max_value else COLORS["blue"],
            outline=""
        )

    def build_monthly_recap(self, parent):
        tk.Label(
            parent,
            text=f"{date.today().strftime('%B').lower()} recap",
            bg="#D884BB",
            fg=COLORS["text"],
            font=("Trebuchet MS", 11, "bold")
        ).pack(anchor="w")

        today = date.today()
        month_start = today.replace(day=1)
        rows = self.get_activities(month_start.isoformat(), today.isoformat())

        active_days = len(set(row[4] for row in rows))
        total_minutes = sum(row[3] for row in rows)
        category_count = len(set(row[2] for row in rows))

        for label, value in [
            ("active days", active_days),
            ("hours tracked", self.format_hours_short(total_minutes)),
            ("categories", category_count),
        ]:
            line = tk.Frame(parent, bg="#D884BB")
            line.pack(fill="x", pady=5)

            tk.Label(
                line, text=label,
                bg="#D884BB", fg=COLORS["text"],
                font=("Segoe UI", 8)
            ).pack(side="left")

            tk.Label(
                line, text=str(value),
                bg="#D884BB", fg=COLORS["text"],
                font=("Segoe UI", 8, "bold")
            ).pack(side="right")

    # ---------------- ADD ACTIVITY ----------------

    def show_add_activity(self):
        self.clear_content()
        self.set_active_nav("ADD A ACTIVITY")

        card = tk.Frame(
            self.content,
            bg=COLORS["pink"],
            highlightbackground=COLORS["pink_dark"],
            highlightthickness=4,
            bd=0,
            padx=28,
            pady=22
        )
        card.place(relx=0.5, rely=0.5, anchor="center", width=940, height=520)

        header = tk.Frame(card, bg=COLORS["pink"])
        header.pack(fill="x", pady=(0, 18))

        tk.Label(
            header,
            text="ADD ACTIVITY",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 20, "bold")
        ).pack(side="left", anchor="w")

        tk.Label(
            header,
            text="log what you actually did.",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 10, "italic")
        ).pack(side="right", anchor="e")

        form = tk.Frame(card, bg=COLORS["pink"])
        form.pack(fill="both", expand=True)

        self.activity_entry = self.add_form_row(
            form,
            "Activity name",
            row_bg=COLORS["pink"],
            entry_width=52
        )
        self.activity_entry.insert(0, "")

        self.category_var = tk.StringVar(value=self.get_category_options()[0])
        self.add_form_row(
            form,
            "Category",
            combo=True,
            variable=self.category_var,
            row_bg=COLORS["pink"],
            combo_width=38,
            combo_values=self.get_category_options()
        )

        duration_frame = tk.Frame(form, bg=COLORS["pink"])
        duration_frame.pack(anchor="w", pady=14, fill="x")

        tk.Label(
            duration_frame,
            text="Duration (HH:MM)",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 10, "bold"),
            width=20,
            anchor="w"
        ).pack(side="left")

        self.hours_var = tk.StringVar(value="0")
        self.minutes_var = tk.StringVar(value="30")

        duration_input = tk.Frame(duration_frame, bg=COLORS["pink"])
        duration_input.pack(side="left")

        tk.Entry(
            duration_input,
            textvariable=self.hours_var,
            width=6,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1
        ).pack(side="left")

        tk.Label(
            duration_input,
            text=":",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 12, "bold")
        ).pack(side="left", padx=4)

        tk.Entry(
            duration_input,
            textvariable=self.minutes_var,
            width=6,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1
        ).pack(side="left")

        tk.Label(
            duration_frame,
            text="hours : minutes",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 9)
        ).pack(side="left", padx=12)

        notes_frame = tk.Frame(form, bg=COLORS["pink"])
        notes_frame.pack(anchor="w", pady=12, fill="x")

        tk.Label(
            notes_frame,
            text="Notes?",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 10, "bold"),
            width=20,
            anchor="nw"
        ).pack(side="left")

        self.notes_text = tk.Text(
            notes_frame,
            height=8,
            width=62,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1
        )
        self.notes_text.pack(side="left", padx=(0, 4))

        date_frame = tk.Frame(form, bg=COLORS["pink"])
        date_frame.pack(anchor="w", pady=10, fill="x")

        tk.Label(
            date_frame,
            text="Date",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 10, "bold"),
            width=20,
            anchor="w"
        ).pack(side="left")

        self.date_entry = tk.Entry(
            date_frame,
            width=28,
            font=("Segoe UI", 10),
            relief="solid",
            bd=1
        )
        self.date_entry.pack(side="left")
        self.date_entry.insert(0, date.today().isoformat())

        tk.Label(
            date_frame,
            text="  YYYY-MM-DD",
            bg=COLORS["pink"],
            fg=COLORS["white"],
            font=("Segoe UI", 9)
        ).pack(side="left")

        buttons = tk.Frame(card, bg=COLORS["pink"])
        buttons.pack(fill="x", pady=(22, 0))

        self.make_button(
            buttons,
            "DELETE",
            self.clear_activity_form,
            bg=COLORS["yellow"],
            width=12
        ).pack(side="right", padx=(0, 10))

        self.make_button(
            buttons,
            "SAVE",
            self.save_activity,
            bg=COLORS["yellow"],
            width=12
        ).pack(side="right")

    def add_form_row(self, parent, label, combo=False, variable=None, row_bg=None, entry_width=28, combo_width=25, combo_values=None):
        bg = row_bg if row_bg is not None else COLORS["card"]
        fg = COLORS["white"] if row_bg is not None else COLORS["text"]

        row = tk.Frame(parent, bg=bg)
        row.pack(anchor="w", pady=10, fill="x")

        tk.Label(
            row,
            text=label,
            bg=bg,
            fg=fg,
            font=("Segoe UI", 10, "bold"),
            width=20,
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
            bd=1
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
            messagebox.showerror("Invalid date", "Use YYYY-MM-DD, for example 2026-08-09.")
            return

        if not activity:
            messagebox.showwarning("Missing activity", "Give your activity a name first.")
            return

        if duration <= 0:
            messagebox.showwarning("Missing duration", "Duration must be greater than zero.")
            return

        notes = self.notes_text.get("1.0", tk.END).strip()

        self.add_activity_to_db(
            activity, category, duration, activity_date, notes
        )

        messagebox.showinfo("Saved!", f"{activity} was added to your audit.")
        self.show_dashboard()

    # ---------------- ANALYTICS ----------------

    def show_analytics(self):
        self.clear_content()
        self.set_active_nav("ANALYTICS")

        top = tk.Frame(self.content, bg=COLORS["bg"])
        top.pack(fill="x")

        tk.Label(
            top,
            text="your time, visualized.",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 24, "bold")
        ).pack(side="left")

        total = self.total_current_month()
        tk.Label(
            top,
            text=f"{self.format_hours(total)} tracked this month",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10)
        ).pack(side="right", pady=10)

        body = tk.Frame(self.content, bg=COLORS["bg"])
        body.pack(fill="both", expand=True, pady=(18, 0))

        left = self.make_card(body, bg=COLORS["card"], padx=14, pady=14)
        left.pack(side="left", fill="both", expand=True, padx=(0, 8))

        right = self.make_card(body, bg=COLORS["mint"], padx=18, pady=18)
        right.pack(side="right", fill="both", expand=True, padx=(8, 0))

        tk.Label(
            left,
            text="CATEGORY BREAKDOWN",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        canvas = tk.Canvas(
            left, bg=COLORS["card"], highlightthickness=0
        )
        canvas.pack(fill="both", expand=True)
        self.draw_category_graph(canvas)

        tk.Label(
            right,
            text="quick audit",
            bg=COLORS["mint"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 22, "bold")
        ).pack(anchor="w")

        total_minutes = self.total_current_month()
        most_used, most_minutes = self.most_used_category_current_month()

        stats = [
            ("Total tracked", self.format_hours(total_minutes)),
            ("Top category", most_used if most_used else "None yet"),
            ("Top category time", self.format_hours(most_minutes)),
            ("Active days", str(self.active_days_current_month())),
        ]

        for label, value in stats:
            box = tk.Frame(right, bg=COLORS["white"])
            box.pack(fill="x", pady=6)

            tk.Label(
                box, text=label,
                bg=COLORS["white"],
                fg=COLORS["muted"],
                font=("Segoe UI", 9)
            ).pack(anchor="w", padx=12, pady=(8, 0))

            tk.Label(
                box, text=value,
                bg=COLORS["white"],
                fg=COLORS["text"],
                font=("Segoe UI", 13, "bold")
            ).pack(anchor="w", padx=12, pady=(0, 8))

    # ---------------- MONTHLY AUDIT ----------------

    def show_monthly_audit(self):
        self.clear_content()
        self.set_active_nav("MONTHLY AUDIT")

        tk.Label(
            self.content,
            text="monthly audit",
            bg=COLORS["bg"],
            fg=COLORS["text"],
            font=("Trebuchet MS", 25, "bold")
        ).pack(anchor="w")

        tk.Label(
            self.content,
            text="Look at the numbers. Then decide what you want to change.",
            bg=COLORS["bg"],
            fg=COLORS["muted"],
            font=("Segoe UI", 10)
        ).pack(anchor="w", pady=(0, 15))

        top = tk.Frame(self.content, bg=COLORS["bg"])
        top.pack(fill="x", pady=(0, 12))

        current_minutes = self.total_current_month()
        previous_minutes = self.total_previous_month()

        cards = [
            ("THIS MONTH", self.format_hours(current_minutes), COLORS["yellow"]),
            ("LAST MONTH", self.format_hours(previous_minutes), COLORS["pink"]),
            ("CHANGE", self.month_change_text(current_minutes, previous_minutes), COLORS["mint"]),
        ]

        for title, value, color in cards:
            card = self.make_card(top, bg=color, padx=15, pady=12)
            card.pack(side="left", fill="both", expand=True, padx=5)

            tk.Label(
                card, text=title,
                bg=color, fg=COLORS["muted"],
                font=("Segoe UI", 9, "bold")
            ).pack(anchor="w")

            tk.Label(
                card, text=value,
                bg=color, fg=COLORS["text"],
                font=("Segoe UI", 17, "bold")
            ).pack(anchor="w", pady=(5, 0))

        lower = tk.Frame(self.content, bg=COLORS["bg"])
        lower.pack(fill="both", expand=True)

        report = self.make_card(lower, bg=COLORS["card"], padx=20, pady=18)
        report.pack(fill="both", expand=True)

        tk.Label(
            report,
            text="WHAT THE NUMBERS SAY",
            bg=COLORS["card"],
            fg=COLORS["text"],
            font=("Segoe UI", 10, "bold")
        ).pack(anchor="w")

        insights = self.generate_insights()

        for insight in insights:
            tk.Label(
                report,
                text="• " + insight,
                bg=COLORS["card"],
                fg=COLORS["text"],
                font=("Segoe UI", 11),
                wraplength=900,
                justify="left"
            ).pack(anchor="w", pady=8)

    # ---------------- GRAPHS ----------------

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
        width = max(canvas.winfo_width(), 350)
        height = max(canvas.winfo_height(), 150)

        left = 35
        bottom = height - 25
        graph_h = height - 55
        max_minutes = max([x[1] for x in data] + [60])

        # guide lines
        for i in range(5):
            y = bottom - (graph_h * i / 4)
            canvas.create_line(
                left, y, width - 15, y,
                fill="#D4C9D8"
            )

        bar_width = max(20, int((width - 75) / 10))

        for i, (label, minutes) in enumerate(data):
            x = left + 20 + i * ((width - 65) / 7)
            bar_h = (minutes / max_minutes) * graph_h if max_minutes else 0

            canvas.create_rectangle(
                x, bottom - bar_h,
                x + bar_width, bottom,
                fill=COLORS["pink_dark"],
                outline=""
            )

            canvas.create_text(
                x + bar_width / 2,
                bottom + 12,
                text=label,
                fill=COLORS["muted"],
                font=("Segoe UI", 8)
            )

            if minutes:
                canvas.create_text(
                    x + bar_width / 2,
                    bottom - bar_h - 8,
                    text=self.format_hours_short(minutes),
                    fill=COLORS["text"],
                    font=("Segoe UI", 7)
                )

    def draw_category_graph(self, canvas):
        canvas.delete("all")
        canvas.update_idletasks()

        width = max(canvas.winfo_width(), 400)
        height = max(canvas.winfo_height(), 300)

        today = date.today()
        month_start = today.replace(day=1)
        rows = self.get_activities(month_start.isoformat(), today.isoformat())

        totals = {}
        for row in rows:
            totals[row[2]] = totals.get(row[2], 0) + row[3]

        max_value = max(totals.values()) if totals else 1

        y = 30

        for category in self.get_category_options():
            color = self.category_color(category)
            minutes = totals.get(category, 0)
            canvas.create_text(
                5, y + 8,
                text=category,
                anchor="w",
                fill=COLORS["text"],
                font=("Segoe UI", 9)
            )

            bar_start = 105
            bar_max = width - 160
            bar_width = (minutes / max_value) * bar_max if max_value else 0

            canvas.create_rectangle(
                bar_start, y,
                bar_start + max(bar_width, 2), y + 18,
                fill=color,
                outline=""
            )

            canvas.create_text(
                width - 5, y + 8,
                text=self.format_hours_short(minutes),
                anchor="e",
                fill=COLORS["muted"],
                font=("Segoe UI", 8)
            )

            y += 36

    # ---------------- HELPERS ----------------

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
        custom_colors = ["#A978E8", "#E58CC2", "#FF8B7B", "#5AA9E6", "#F5B82E", "#55C86A"]
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

    def calculate_week_improvement(self):
        today = date.today()
        current_start = today - timedelta(days=6)
        current_end = today

        previous_end = current_start - timedelta(days=1)
        previous_start = previous_end - timedelta(days=6)

        current = sum(
            row[3] for row in self.get_activities(
                current_start.isoformat(), current_end.isoformat()
            )
        )

        previous = sum(
            row[3] for row in self.get_activities(
                previous_start.isoformat(), previous_end.isoformat()
            )
        )

        if previous == 0:
            return 100 if current > 0 else 0

        return round(((current - previous) / previous) * 100)

    def total_current_month(self):
        today = date.today()
        start = today.replace(day=1)
        return sum(
            row[3] for row in self.get_activities(
                start.isoformat(), today.isoformat()
            )
        )

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

        return sum(
            row[3] for row in self.get_activities(
                start.isoformat(), end.isoformat()
            )
        )

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
                "Start recording your activities and your first audit will build itself.",
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
        self.conn.close()
        self.root.destroy()


if __name__ == "__main__":
    root = tk.Tk()
    app = LifeAuditApp(root)
    root.mainloop()
