import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import dataclass, field

try:
    from brevo_client import send_brevo_email
except ImportError:
    def send_brevo_email(recipient: str, body: str, subject: str = "") -> str:
        raise RuntimeError("brevo_client module not found — email sending is unavailable.")

GRADES_FILE = "limbus_grades.txt"
RECORD_MARK = "=="

# ------------------------------ palette ------------------------------
# Limbus Company: black-and-crimson corporate menace, sharp white
# accents like a ledger stamped in blood-red ink.
VOID = "#0C0A0D"
PANEL = "#1A1518"
LINE = "#3D2229"
CRIMSON = "#9E1B32"
CRIMSON_HOVER = "#BE2440"
IVORY = "#E9E4DD"
MUTED = "#7A6E72"
LOG_BG = "#060505"
LOG_TEXT = "#D9A0AC"

FONT_HEADER = ("Georgia", 17, "bold")
FONT_SUBTITLE = ("Georgia", 9, "italic")
FONT_LABEL = ("Consolas", 9, "bold")
FONT_VALUE = ("Georgia", 11, "bold")
FONT_MONO = ("Consolas", 10)
FONT_MONO_SMALL = ("Consolas", 9)
FONT_BTN = ("Georgia", 9, "bold")


# ==============================================================================
# DATA LAYER
# ==============================================================================

@dataclass
class Grade:
    course_code: str
    course_title: str
    units: float
    grade: float

    def __post_init__(self) -> None:
        self.course_code = self.course_code.strip()
        self.course_title = self.course_title.strip()
        self.units = float(self.units)
        self.grade = float(self.grade)

    @property
    def grade_points(self) -> float:
        return self.units * self.grade

    def as_row(self) -> tuple:
        return (self.course_code, self.course_title, f"{self.units:g}", f"{self.grade:.2f}")

    def as_line(self) -> str:
        return f"{self.course_code}, {self.course_title}, {self.units:g}, {self.grade}"


@dataclass
class Student:
    student_id: str = ""
    student_name: str = ""
    course_year: str = ""
    subjects: list = field(default_factory=list)

    @property
    def key(self) -> str:
        return self.student_id.strip()

    def display_name(self) -> str:
        label = self.student_name or "(unnamed)"
        if self.course_year:
            label = f"{label} ({self.course_year})"
        if self.student_id:
            label = f"[{self.student_id}] {label}"
        return label

    def total_units(self) -> float:
        return sum(s.units for s in self.subjects)

    def weighted_average(self) -> float:
        total = self.total_units()
        if total == 0:
            return 0.0
        weighted_sum = sum(s.grade_points for s in self.subjects)
        return round(weighted_sum / total, 2)

    def report_html(self) -> str:
        rows = "\n".join(
            f'<tr><td style="padding:8px 12px;border:1px solid #9E1B32;">{s.course_code}</td>'
            f'<td style="padding:8px 12px;border:1px solid #9E1B32;">{s.course_title}</td>'
            f'<td style="padding:8px 12px;border:1px solid #9E1B32;text-align:center;">{s.units:g}</td>'
            f'<td style="padding:8px 12px;border:1px solid #9E1B32;text-align:center;">{s.grade:.2f}</td></tr>'
            for s in self.subjects
        )
        return f"""
<div style="font-family:Georgia,serif;color:#0C0A0D;background:#E9E4DD;padding:20px;border:2px solid #9E1B32;">
  <h2 style="color:#9E1B32;margin-bottom:4px;">LIMBUS COMPANY — PERSONNEL GRADE FILE</h2>
  <p style="margin:4px 0;"><b>Student:</b> {self.student_name}</p>
  <p style="margin:4px 0 16px;"><b>Program &amp; Year:</b> {self.course_year}</p>
  <table style="border-collapse:collapse;width:100%;">
    <thead><tr style="background:#9E1B32;color:#E9E4DD;">
      <th style="padding:8px 12px;">Course Code</th><th style="padding:8px 12px;">Course Title</th>
      <th style="padding:8px 12px;">Units</th><th style="padding:8px 12px;">Grade</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="margin-top:16px;"><b>Total Units:</b> {self.total_units():g}</p>
  <p><b>Weighted Average:</b> {self.weighted_average():.2f}</p>
</div>
""".strip()


def honors_status(average: float) -> str:
    """Pure function, no tkinter/Student dependency. Lower is better."""
    if average <= 1.75:
        return "With Honors"
    return "Regular"


class GradeManager:
    """Holds every student record loaded from limbus_grades.txt, plus
    full CRUD for students and their subjects."""

    def __init__(self) -> None:
        self.students: list[Student] = []
        self.active_index: int = -1
        self.skipped_lines: int = 0

    @property
    def active(self):
        if 0 <= self.active_index < len(self.students):
            return self.students[self.active_index]
        return None

    @property
    def subjects(self) -> list:
        return self.active.subjects if self.active else []

    def total_units(self) -> float:
        return self.active.total_units() if self.active else 0.0

    def weighted_average(self) -> float:
        return self.active.weighted_average() if self.active else 0.0

    def load(self, path: str = GRADES_FILE) -> None:
        self.students.clear()
        self.skipped_lines = 0
        self.active_index = -1
        try:
            with open(path, "r", encoding="utf-8") as f:
                raw_lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            return
        if not raw_lines:
            return

        current = None
        for line in raw_lines:
            if line.startswith(RECORD_MARK):
                header = line[len(RECORD_MARK):].strip()
                parts = [p.strip() for p in header.split("|")]
                if len(parts) >= 3:
                    sid, name, year = parts[0], parts[1], parts[2]
                else:
                    sid, name, year = "", parts[0] if parts else "", ""
                current = Student(student_id=sid, student_name=name, course_year=year)
                self.students.append(current)
                continue
            if current is None:
                self.skipped_lines += 1
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 4:
                self.skipped_lines += 1
                continue
            code, name, units, grade = parts
            try:
                current.subjects.append(Grade(code, name, float(units), float(grade)))
            except ValueError:
                self.skipped_lines += 1

        if self.students:
            self.active_index = 0

    def save(self, path: str = GRADES_FILE) -> None:
        with open(path, "w", encoding="utf-8") as f:
            for student in self.students:
                f.write(f"{RECORD_MARK} {student.student_id} | {student.student_name} | {student.course_year}\n")
                for s in student.subjects:
                    f.write(s.as_line() + "\n")

    # ------------------------- student management -------------------------

    def add_student(self, student_id: str, name: str, course_year: str,
                     initial_subjects=None) -> None:
        student_id, name, course_year = student_id.strip(), name.strip(), course_year.strip()
        if not student_id:
            raise ValueError("Student ID is required.")
        if not name:
            raise ValueError("Student name is required.")
        if any(s.key == student_id for s in self.students):
            raise ValueError(f"A student with ID '{student_id}' already exists.")
        student = Student(student_id=student_id, student_name=name, course_year=course_year,
                           subjects=list(initial_subjects) if initial_subjects else [])
        self.students.append(student)
        self.active_index = len(self.students) - 1

    def remove_active_student(self) -> None:
        if self.active is None:
            return
        del self.students[self.active_index]
        self.active_index = 0 if self.students else -1

    def set_active_by_index(self, index: int) -> None:
        if 0 <= index < len(self.students):
            self.active_index = index

    def student_labels(self) -> list:
        return [s.display_name() for s in self.students]

    # ------------------------- subject editing (active student) -------------------------

    def _require_active(self) -> Student:
        if self.active is None:
            raise ValueError("No student selected. Add a student first.")
        return self.active

    def add_subject(self, code: str, name: str, units: float, grade: float) -> None:
        student = self._require_active()
        code, name = code.strip(), name.strip()
        if not code or not name:
            raise ValueError("Subject code and name are required.")
        if units <= 0:
            raise ValueError("Units must be greater than zero.")
        if not (1.0 <= grade <= 5.0):
            raise ValueError("Grade must be between 1.00 and 5.00.")
        student.subjects.append(Grade(code, name, units, grade))

    def update_subject(self, index: int, code: str, name: str, units: float, grade: float) -> None:
        student = self._require_active()
        if not (0 <= index < len(student.subjects)):
            raise IndexError("No subject at that position.")
        code, name = code.strip(), name.strip()
        if not code or not name:
            raise ValueError("Subject code and name are required.")
        if units <= 0:
            raise ValueError("Units must be greater than zero.")
        if not (1.0 <= grade <= 5.0):
            raise ValueError("Grade must be between 1.00 and 5.00.")
        student.subjects[index] = Grade(code, name, units, grade)

    def remove_subject(self, index: int) -> None:
        student = self._require_active()
        if 0 <= index < len(student.subjects):
            student.subjects.pop(index)


# ==============================================================================
# PRESENTATION LAYER
# ==============================================================================

def styled_button(parent, text, command, *, bg, fg, hover_bg=None, font=FONT_MONO_SMALL,
                   border=None, **pack_kwargs):
    btn = tk.Button(
        parent, text=text, command=command, font=font, bg=bg, fg=fg,
        activebackground=hover_bg or bg, activeforeground=fg,
        relief="flat", padx=12, pady=7, cursor="hand2", bd=0,
        highlightthickness=1, highlightbackground=border or LINE,
    )
    if hover_bg:
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def labeled_field(parent, label_text, row, *, value_font=FONT_VALUE):
    tk.Label(parent, text=label_text, font=FONT_LABEL, fg=MUTED, bg=VOID,
              anchor="w").grid(row=row, column=0, sticky="w", pady=(6 if row else 0, 0))
    value = tk.Label(parent, text="—", font=value_font, fg=IVORY, bg=VOID, anchor="w")
    value.grid(row=row, column=1, sticky="w", padx=(16, 0), pady=(6 if row else 0, 0))
    return value


class SubjectDialog(tk.Toplevel):
    def __init__(self, master, *, title, initial=None, on_submit):
        super().__init__(master, bg=PANEL)
        self.title(title)
        self.configure(padx=24, pady=20)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_submit = on_submit

        fields = [("Course code", "code"), ("Course title", "name"), ("Units", "units"), ("Grade", "grade")]
        self.vars: dict = {}
        for i, (label, key) in enumerate(fields):
            tk.Label(self, text=label.upper(), font=FONT_LABEL, fg=MUTED,
                      bg=PANEL, anchor="w").grid(row=i, column=0, sticky="w", pady=(0 if i == 0 else 10, 0))
            var = tk.StringVar(value=str(initial[key]) if initial else "")
            entry = tk.Entry(self, textvariable=var, width=30, font=FONT_MONO,
                              bg=VOID, fg=IVORY, insertbackground=IVORY, relief="flat",
                              highlightthickness=1, highlightbackground=LINE, highlightcolor=CRIMSON)
            entry.grid(row=i, column=1, sticky="w", padx=(14, 0), pady=(0 if i == 0 else 10, 0))
            self.vars[key] = var

        btn_row = tk.Frame(self, bg=PANEL)
        btn_row.grid(row=len(fields), column=0, columnspan=2, sticky="e", pady=(18, 0))
        styled_button(btn_row, "CANCEL", self.destroy, bg=PANEL, fg=MUTED).pack(side="left", padx=(0, 8))
        styled_button(btn_row, "SAVE", self._submit, bg=CRIMSON, fg=IVORY,
                      hover_bg=CRIMSON_HOVER, font=FONT_BTN).pack(side="left")

    def _submit(self) -> None:
        try:
            code = self.vars["code"].get()
            name = self.vars["name"].get()
            units = float(self.vars["units"].get())
            grade = float(self.vars["grade"].get())
        except ValueError:
            messagebox.showerror("Invalid input", "Units and Grade must be numbers.", parent=self)
            return
        try:
            self.on_submit(code, name, units, grade)
        except (ValueError, IndexError) as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
            return
        self.destroy()


class AddStudentDialog(tk.Toplevel):
    """Add New Student: identity fields plus a staged course list."""

    def __init__(self, master, *, on_create):
        super().__init__(master, bg=PANEL)
        self.title("Add New Student")
        self.configure(padx=26, pady=22)
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()
        self.on_create = on_create
        self.staged: list = []

        tk.Label(self, text="ADD NEW STUDENT", font=("Georgia", 12, "bold"),
                  fg=IVORY, bg=PANEL, anchor="w").grid(row=0, column=0, columnspan=4, sticky="w")
        tk.Frame(self, bg=LINE, height=1).grid(row=1, column=0, columnspan=4, sticky="ew", pady=(8, 14))

        tk.Label(self, text="STUDENT ID", font=FONT_LABEL, fg=MUTED, bg=PANEL,
                  anchor="w").grid(row=2, column=0, sticky="w")
        self.id_var = tk.StringVar()
        tk.Entry(self, textvariable=self.id_var, width=40, font=FONT_MONO, bg=VOID, fg=IVORY,
                  insertbackground=IVORY, relief="flat", highlightthickness=1,
                  highlightbackground=LINE, highlightcolor=CRIMSON
                  ).grid(row=2, column=1, columnspan=3, sticky="w", padx=(14, 0))

        tk.Label(self, text="FULL NAME", font=FONT_LABEL, fg=MUTED, bg=PANEL,
                  anchor="w").grid(row=3, column=0, sticky="w", pady=(10, 0))
        self.name_var = tk.StringVar()
        tk.Entry(self, textvariable=self.name_var, width=40, font=FONT_MONO, bg=VOID, fg=IVORY,
                  insertbackground=IVORY, relief="flat", highlightthickness=1,
                  highlightbackground=LINE, highlightcolor=CRIMSON
                  ).grid(row=3, column=1, columnspan=3, sticky="w", padx=(14, 0), pady=(10, 0))

        tk.Label(self, text="PROGRAM & YEAR", font=FONT_LABEL, fg=MUTED, bg=PANEL,
                  anchor="w").grid(row=4, column=0, sticky="w", pady=(10, 0))
        self.program_var = tk.StringVar()
        tk.Entry(self, textvariable=self.program_var, width=40, font=FONT_MONO, bg=VOID, fg=IVORY,
                  insertbackground=IVORY, relief="flat", highlightthickness=1,
                  highlightbackground=LINE, highlightcolor=CRIMSON
                  ).grid(row=4, column=1, columnspan=3, sticky="w", padx=(14, 0), pady=(10, 0))

        entry_labels = ["CODE", "TITLE", "UNITS", "GRADE"]
        self.course_vars: list = []
        widths = [10, 22, 8, 8]
        for col, (label, w) in enumerate(zip(entry_labels, widths)):
            tk.Label(self, text=label, font=FONT_LABEL, fg=MUTED, bg=PANEL,
                      anchor="w").grid(row=6, column=col, sticky="w", pady=(14, 0))
            var = tk.StringVar()
            tk.Entry(self, textvariable=var, width=w, font=FONT_MONO, bg=VOID, fg=IVORY,
                      insertbackground=IVORY, relief="flat", highlightthickness=1,
                      highlightbackground=LINE, highlightcolor=CRIMSON
                      ).grid(row=7, column=col, sticky="w", padx=(0, 8), pady=(2, 0))
            self.course_vars.append(var)

        course_btns = tk.Frame(self, bg=PANEL)
        course_btns.grid(row=8, column=0, columnspan=4, sticky="w", pady=(10, 14))
        styled_button(course_btns, "+ ADD COURSE", self._add_course_to_list,
                      bg=VOID, fg=IVORY).pack(side="left")
        styled_button(course_btns, "REMOVE SELECTED", self._remove_selected_course,
                      bg=VOID, fg=CRIMSON, border=CRIMSON).pack(side="left", padx=(8, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Stage.Treeview", background=VOID, fieldbackground=VOID,
                         foreground=IVORY, rowheight=24, borderwidth=0, font=FONT_MONO_SMALL)
        style.configure("Stage.Treeview.Heading", background=PANEL, foreground=IVORY,
                         font=FONT_MONO_SMALL, relief="flat")
        style.map("Stage.Treeview", background=[("selected", CRIMSON)], foreground=[("selected", IVORY)])

        self.stage_tree = ttk.Treeview(self, columns=("code", "title", "units", "grade"),
                                        show="headings", height=5, style="Stage.Treeview",
                                        selectmode="browse")
        for col, label, w in [("code", "CODE", 90), ("title", "TITLE", 220),
                               ("units", "UNITS", 60), ("grade", "GRADE", 60)]:
            self.stage_tree.heading(col, text=label)
            self.stage_tree.column(col, width=w, anchor="w")
        self.stage_tree.grid(row=9, column=0, columnspan=4, sticky="ew")

        btn_row = tk.Frame(self, bg=PANEL)
        btn_row.grid(row=10, column=0, columnspan=4, sticky="e", pady=(18, 0))
        styled_button(btn_row, "CANCEL", self.destroy, bg=PANEL, fg=MUTED).pack(side="left", padx=(0, 8))
        styled_button(btn_row, "CREATE STUDENT", self._create_student, bg=CRIMSON, fg=IVORY,
                      hover_bg=CRIMSON_HOVER, font=FONT_BTN).pack(side="left")

    def _add_course_to_list(self) -> None:
        code, title, units, grade = (v.get().strip() for v in self.course_vars)
        if not code or not title:
            messagebox.showerror("Invalid input", "Course code and title are required.", parent=self)
            return
        try:
            units_f = float(units)
            grade_f = float(grade)
        except ValueError:
            messagebox.showerror("Invalid input", "Units and Grade must be numbers.", parent=self)
            return
        if units_f <= 0:
            messagebox.showerror("Invalid input", "Units must be greater than zero.", parent=self)
            return
        if not (1.0 <= grade_f <= 5.0):
            messagebox.showerror("Invalid input", "Grade must be between 1.00 and 5.00.", parent=self)
            return
        self.staged.append((code, title, f"{units_f:g}", f"{grade_f}"))
        self.stage_tree.insert("", "end", values=(code, title, f"{units_f:g}", f"{grade_f:.2f}"))
        for v in self.course_vars:
            v.set("")

    def _remove_selected_course(self) -> None:
        sel = self.stage_tree.selection()
        if not sel:
            return
        index = self.stage_tree.index(sel[0])
        self.stage_tree.delete(sel[0])
        del self.staged[index]

    def _create_student(self) -> None:
        student_id = self.id_var.get()
        name = self.name_var.get()
        program = self.program_var.get()
        try:
            subjects = [Grade(code, title, units, grade) for code, title, units, grade in self.staged]
        except ValueError:
            messagebox.showerror("Invalid input", "One of the staged courses has bad data.", parent=self)
            return
        try:
            self.on_create(student_id, name, program, subjects)
        except (ValueError, IndexError) as exc:
            messagebox.showerror("Invalid input", str(exc), parent=self)
            return
        self.destroy()


class GradeReportApp(tk.Frame):
    """Limbus Company console — full CRUD over multiple student
    ('student') records: add/remove students, add/edit/remove subjects."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=VOID)
        self.manager = GradeManager()

        self._build_header()
        self._build_selector()
        self._build_student_info()
        self._build_table()
        self._build_table_actions()
        self._build_email_section()
        self._build_log()

        self.on_reload()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=VOID, padx=28, pady=20)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="† LIMBUS COMPANY — PERSONNEL GRADE FILE",
                 font=FONT_HEADER, fg=IVORY, bg=VOID, anchor="w").pack(anchor="w")
        tk.Label(header, text="Every student's academic record, managed and dispatched from one desk.",
                 font=FONT_SUBTITLE, fg=MUTED, bg=VOID, anchor="w").pack(anchor="w", pady=(2, 0))
        tk.Frame(header, bg=CRIMSON, height=2).pack(fill="x", pady=(14, 0))

    def _build_selector(self) -> None:
        wrap = tk.Frame(self, bg=VOID, padx=28, pady=14)
        wrap.grid(row=1, column=0, sticky="ew")
        tk.Label(wrap, text="STUDENT RECORD", font=FONT_LABEL, fg=MUTED, bg=VOID, anchor="w").pack(anchor="w")

        row = tk.Frame(wrap, bg=VOID)
        row.pack(anchor="w", fill="x", pady=(6, 0))

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Limbus.TCombobox", fieldbackground=PANEL, background=PANEL,
                         foreground=IVORY, arrowcolor=CRIMSON, bordercolor=LINE, relief="flat")
        style.map("Limbus.TCombobox", fieldbackground=[("readonly", PANEL)])

        self.student_var = tk.StringVar(value="")
        self.student_combo = ttk.Combobox(row, textvariable=self.student_var, state="readonly",
                                           width=38, font=FONT_MONO, style="Limbus.TCombobox")
        self.student_combo.pack(side="left")
        self.student_combo.bind("<<ComboboxSelected>>", self.on_student_selected)

        styled_button(row, "+ ADD STUDENT", self.on_add_student,
                      bg=PANEL, fg=IVORY).pack(side="left", padx=(10, 0))
        styled_button(row, "REMOVE STUDENT", self.on_remove_student,
                      bg=PANEL, fg=CRIMSON, border=CRIMSON).pack(side="left", padx=(8, 0))

    def _build_student_info(self) -> None:
        info = tk.Frame(self, bg=VOID, padx=28, pady=14)
        info.grid(row=2, column=0, sticky="ew")
        self.id_value = labeled_field(info, "STUDENT ID", 0)
        self.student_value = labeled_field(info, "STUDENT", 1)
        self.program_value = labeled_field(info, "PROGRAM & YEAR", 2)
        self.honors_value = labeled_field(info, "HONORS STATUS", 3)

    def _build_table(self) -> None:
        table_wrap = tk.Frame(self, bg=VOID, padx=28)
        table_wrap.grid(row=3, column=0, sticky="ew")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Limbus.Treeview", background=PANEL, fieldbackground=PANEL,
                         foreground=IVORY, rowheight=26, borderwidth=0, font=FONT_MONO)
        style.configure("Limbus.Treeview.Heading", background=VOID, foreground=IVORY,
                         font=FONT_MONO_SMALL, relief="flat")
        style.map("Limbus.Treeview", background=[("selected", CRIMSON)], foreground=[("selected", IVORY)])

        columns = ("code", "name", "units", "grade")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings",
                                  height=8, style="Limbus.Treeview", selectmode="browse")
        for col, label, w in [("code", "COURSE CODE", 100), ("name", "COURSE TITLE", 260),
                               ("units", "UNITS", 70), ("grade", "GRADE", 70)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="x", pady=(0, 12))
        self.tree.bind("<Double-1>", lambda e: self.on_edit())

        self.totals_label = tk.Label(
            self, text="Total Units: 0  |  Weighted Average: 0.00",
            font=FONT_MONO, fg=CRIMSON, bg=VOID, anchor="w", padx=28)
        self.totals_label.grid(row=4, column=0, sticky="ew", pady=(0, 14))

    def _build_table_actions(self) -> None:
        actions = tk.Frame(self, bg=VOID, padx=28)
        actions.grid(row=5, column=0, sticky="w", pady=(0, 18))
        styled_button(actions, "+ ADD SUBJECT", self.on_add, bg=VOID, fg=IVORY).pack(side="left")
        styled_button(actions, "EDIT SELECTED", self.on_edit, bg=VOID, fg=MUTED).pack(side="left", padx=(8, 0))
        styled_button(actions, "REMOVE SELECTED", self.on_remove, bg=VOID, fg=MUTED).pack(side="left", padx=(8, 0))
        styled_button(actions, "RELOAD limbus_grades.txt", self.on_reload,
                      bg=VOID, fg=MUTED).pack(side="left", padx=(8, 0))

    def _build_email_section(self) -> None:
        email_wrap = tk.Frame(self, bg=VOID, padx=28)
        email_wrap.grid(row=6, column=0, sticky="ew")

        tk.Label(email_wrap, text="EMAIL RECIPIENT", font=FONT_LABEL,
                 fg=MUTED, bg=VOID, anchor="w").pack(anchor="w")
        self.recipient_var = tk.StringVar(value="")
        tk.Entry(email_wrap, textvariable=self.recipient_var, width=48,
                 font=FONT_MONO, bg=PANEL, fg=IVORY, insertbackground=IVORY, relief="flat",
                 highlightthickness=1, highlightbackground=LINE, highlightcolor=CRIMSON
                 ).pack(anchor="w", pady=(4, 12))

        actions = tk.Frame(email_wrap, bg=VOID)
        actions.pack(anchor="w", fill="x")
        styled_button(actions, "† SEND GRADE REPORT", self.on_send,
                      bg=CRIMSON, fg=IVORY, hover_bg=CRIMSON_HOVER, font=FONT_BTN).pack(side="left")
        styled_button(actions, "CLEAR LOG", self.on_clear, bg=VOID, fg=MUTED).pack(side="left", padx=(10, 0))

    def _build_log(self) -> None:
        log_wrap = tk.Frame(self, bg=VOID, padx=28)
        log_wrap.grid(row=7, column=0, sticky="ew", pady=(18, 24))
        tk.Label(log_wrap, text="DELIVERY LOG", font=FONT_LABEL, fg=IVORY, bg=VOID).pack(anchor="w", pady=(0, 6))
        self.log = tk.Text(log_wrap, height=8, width=76, font=FONT_MONO,
                            bg=LOG_BG, fg=LOG_TEXT, relief="flat", padx=10, pady=8,
                            insertbackground=LOG_TEXT, highlightthickness=1,
                            highlightbackground=LINE, state="disabled")
        self.log.pack(fill="x")

    # -------------------------- data refresh --------------------------

    def refresh_combo(self) -> None:
        self.student_combo["values"] = self.manager.student_labels()
        if self.manager.active is not None:
            self.student_combo.current(self.manager.active_index)
        else:
            self.student_var.set("")

    def refresh_info(self) -> None:
        self.id_value.configure(text=self.manager.active.student_id if self.manager.active else "—")
        self.student_value.configure(text=self.manager.active.student_name if self.manager.active else "—")
        self.program_value.configure(text=self.manager.active.course_year if self.manager.active else "—")
        status = honors_status(self.manager.weighted_average()) if self.manager.active else "—"
        self.honors_value.configure(text=status)

    def refresh_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        for s in self.manager.subjects:
            self.tree.insert("", "end", values=s.as_row())
        self.totals_label.configure(
            text=f"Total Units: {self.manager.total_units():g}  |  "
                 f"Weighted Average: {self.manager.weighted_average():.2f}")

    def refresh_all(self) -> None:
        self.refresh_combo()
        self.refresh_info()
        self.refresh_table()

    def selected_index(self):
        sel = self.tree.selection()
        if not sel:
            return None
        return self.tree.index(sel[0])

    def on_reload(self) -> None:
        self.manager.load()
        self.refresh_all()
        if self.manager.skipped_lines:
            self.write(f"NOTE -> skipped {self.manager.skipped_lines} malformed line(s)")
        self.write(f"LOADED -> {len(self.manager.students)} student record(s)")

    def on_student_selected(self, event=None) -> None:
        self.manager.set_active_by_index(self.student_combo.current())
        self.refresh_info()
        self.refresh_table()

    # -------------------------- student CRUD --------------------------

    def on_add_student(self) -> None:
        def create(student_id, name, program, subjects):
            self.manager.add_student(student_id, name, program, subjects)
            self.manager.save()
            self.refresh_all()
            self.write(f"ADDED STUDENT -> [{student_id.strip()}] {name.strip()}")

        AddStudentDialog(self, on_create=create)

    def on_remove_student(self) -> None:
        if self.manager.active is None:
            messagebox.showinfo("No student", "No student record is selected.")
            return
        s = self.manager.active
        if not messagebox.askyesno("Remove student", f"Remove {s.display_name()} and all their subjects?"):
            return
        self.manager.remove_active_student()
        self.manager.save()
        self.refresh_all()
        self.write(f"REMOVED STUDENT -> [{s.student_id}] {s.student_name}")

    # -------------------------- subject CRUD --------------------------

    def on_add(self) -> None:
        def submit(code, name, units, grade):
            self.manager.add_subject(code, name, units, grade)
            self.manager.save()
            self.refresh_table()
            self.refresh_info()
            self.write(f"ADDED -> {code.strip()} ({name.strip()})")

        SubjectDialog(self, title="Add Subject", on_submit=submit)

    def on_edit(self) -> None:
        index = self.selected_index()
        if index is None:
            messagebox.showinfo("No selection", "Select a subject in the table first.")
            return
        s = self.manager.subjects[index]
        initial = {"code": s.course_code, "name": s.course_title, "units": s.units, "grade": s.grade}

        def submit(code, name, units, grade):
            self.manager.update_subject(index, code, name, units, grade)
            self.manager.save()
            self.refresh_table()
            self.refresh_info()
            self.write(f"EDITED -> {code.strip()} ({name.strip()})")

        SubjectDialog(self, title="Edit Subject", initial=initial, on_submit=submit)

    def on_remove(self) -> None:
        index = self.selected_index()
        if index is None:
            messagebox.showinfo("No selection", "Select a subject in the table first.")
            return
        s = self.manager.subjects[index]
        if not messagebox.askyesno("Remove subject", f"Remove {s.course_code} — {s.course_title}?"):
            return
        self.manager.remove_subject(index)
        self.manager.save()
        self.refresh_table()
        self.refresh_info()
        self.write(f"REMOVED -> {s.course_code} ({s.course_title})")

    # -------------------------- email + log --------------------------

    def on_send(self) -> None:
        recipient = self.recipient_var.get().strip()
        if not recipient:
            messagebox.showwarning("Missing recipient", "Enter an email recipient first.")
            return
        if self.manager.active is None or not self.manager.subjects:
            messagebox.showwarning("Nothing to send", "Select a student with at least one subject first.")
            return
        try:
            line = send_brevo_email(
                recipient,
                self.manager.active.report_html(),
                subject=f"Limbus Company Grade Report — {self.manager.student_name if self.manager.active else 'Student'}",
            )
        except Exception as exc:
            self.write(f"FAILED -> {recipient}: {exc}")
            messagebox.showerror("Email failed", str(exc))
            return
        self.write(line)

    def on_clear(self) -> None:
        self.log.configure(state="normal")
        self.log.delete("1.0", "end")
        self.log.configure(state="disabled")

    def write(self, text: str) -> None:
        self.log.configure(state="normal")
        self.log.insert("end", text + "\n")
        self.log.see("end")
        self.log.configure(state="disabled")


def main() -> None:
    root = tk.Tk()
    root.title("Limbus Company — Personnel Grade File")
    root.configure(bg=VOID)
    root.resizable(False, False)
    GradeReportApp(root).pack()
    root.mainloop()


if __name__ == "__main__":
    main()