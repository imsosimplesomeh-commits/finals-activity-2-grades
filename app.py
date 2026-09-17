import tkinter as tk
from tkinter import messagebox, ttk
from dataclasses import dataclass

try:
    from brevo_client import send_brevo_email
except ImportError:
    def send_brevo_email(recipient: str, body: str, subject: str = "") -> str:
        raise RuntimeError("brevo_client module not found — email sending is unavailable.")

GRADES_FILE = "lobcorp_grades.txt"

VOID = "#0A0F0E"
PANEL = "#141C1B"
LINE = "#2C3E3B"
TEAL = "#3E8E7E"
TEAL_HOVER = "#4FA894"
WARNING = "#D6B32C"
BONE = "#D8E0DC"
MUTED = "#6E7C78"
LOG_BG = "#050807"
LOG_TEXT = "#8FCBBB"

FONT_HEADER = ("Consolas", 16, "bold")
FONT_SUBTITLE = ("Consolas", 9, "italic")
FONT_LABEL = ("Consolas", 9, "bold")
FONT_VALUE = ("Consolas", 11, "bold")
FONT_MONO = ("Consolas", 10)
FONT_MONO_SMALL = ("Consolas", 9)
FONT_BTN = ("Consolas", 9, "bold")


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


def honors_status(average: float) -> str:
    """Pure function, no tkinter/Grade dependency. Lower is better."""
    if average <= 1.75:
        return "With Honors"
    return "Regular"


class GradeManager:
    """Single-student manager: reads lobcorp_grades.txt (one header
    line, then subject lines) and computes totals."""

    def __init__(self) -> None:
        self.student_name = ""
        self.course_year = ""
        self.subjects: list = []
        self.skipped_lines = 0

    def load(self, path: str = GRADES_FILE) -> None:
        self.subjects.clear()
        self.skipped_lines = 0
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.strip() for line in f if line.strip()]
        except FileNotFoundError:
            self.student_name = ""
            self.course_year = ""
            return
        if not lines:
            return

        header_parts = [p.strip() for p in lines[0].split(",")]
        self.student_name = header_parts[0] if len(header_parts) > 0 else ""
        self.course_year = header_parts[1] if len(header_parts) > 1 else ""

        for line in lines[1:]:
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 4:
                self.skipped_lines += 1
                continue
            code, name, units, grade = parts
            try:
                self.subjects.append(Grade(code, name, float(units), float(grade)))
            except ValueError:
                self.skipped_lines += 1

    def save(self, path: str = GRADES_FILE) -> None:
        with open(path, "w", encoding="utf-8") as f:
            f.write(f"{self.student_name}, {self.course_year}\n")
            for s in self.subjects:
                f.write(s.as_line() + "\n")

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
            f'<tr><td style="padding:8px 12px;border:1px solid #3E8E7E;">{s.course_code}</td>'
            f'<td style="padding:8px 12px;border:1px solid #3E8E7E;">{s.course_title}</td>'
            f'<td style="padding:8px 12px;border:1px solid #3E8E7E;text-align:center;">{s.units:g}</td>'
            f'<td style="padding:8px 12px;border:1px solid #3E8E7E;text-align:center;">{s.grade:.2f}</td></tr>'
            for s in self.subjects
        )
        return f"""
<div style="font-family:Consolas,monospace;color:#0A0F0E;background:#D8E0DC;padding:20px;border:2px solid #3E8E7E;">
  <h2 style="color:#1f4d43;margin-bottom:4px;">LOBOTOMY CORPORATION — GRADE CONTAINMENT REPORT</h2>
  <p style="margin:4px 0;"><b>Employee:</b> {self.student_name}</p>
  <p style="margin:4px 0 16px;"><b>Program &amp; Year:</b> {self.course_year}</p>
  <table style="border-collapse:collapse;width:100%;">
    <thead><tr style="background:#3E8E7E;color:#0A0F0E;">
      <th style="padding:8px 12px;">Course Code</th><th style="padding:8px 12px;">Course Title</th>
      <th style="padding:8px 12px;">Units</th><th style="padding:8px 12px;">Grade</th>
    </tr></thead>
    <tbody>{rows}</tbody>
  </table>
  <p style="margin-top:16px;"><b>Total Units:</b> {self.total_units():g}</p>
  <p><b>Weighted Average:</b> {self.weighted_average():.2f}</p>
</div>
""".strip()


# ==============================================================================
# PRESENTATION LAYER
# ==============================================================================

def styled_button(parent, text, command, *, bg, fg, hover_bg=None, font=FONT_MONO_SMALL, **pack_kwargs):
    btn = tk.Button(
        parent, text=text, command=command, font=font, bg=bg, fg=fg,
        activebackground=hover_bg or bg, activeforeground=fg,
        relief="flat", padx=12, pady=7, cursor="hand2", bd=0,
        highlightthickness=1, highlightbackground=LINE,
    )
    if hover_bg:
        btn.bind("<Enter>", lambda e: btn.configure(bg=hover_bg))
        btn.bind("<Leave>", lambda e: btn.configure(bg=bg))
    return btn


def labeled_field(parent, label_text, row, *, value_font=FONT_VALUE):
    tk.Label(parent, text=label_text, font=FONT_LABEL, fg=MUTED, bg=VOID,
              anchor="w").grid(row=row, column=0, sticky="w", pady=(6 if row else 0, 0))
    value = tk.Label(parent, text="—", font=value_font, fg=BONE, bg=VOID, anchor="w")
    value.grid(row=row, column=1, sticky="w", padx=(16, 0), pady=(6 if row else 0, 0))
    return value


class GradeReportApp(tk.Frame):
    """LobCorp console — single-student, always reads lobcorp_grades.txt's
    one record. No selector needed."""

    def __init__(self, master: tk.Misc) -> None:
        super().__init__(master, bg=VOID)
        self.manager = GradeManager()

        self._build_header()
        self._build_student_info()
        self._build_table()
        self._build_table_actions()
        self._build_email_section()
        self._build_log()

        self.on_reload()

    def _build_header(self) -> None:
        header = tk.Frame(self, bg=VOID, padx=28, pady=20)
        header.grid(row=0, column=0, sticky="ew")
        tk.Label(header, text="◈ LOBOTOMY CORPORATION — GRADE MANAGEMENT TERMINAL",
                 font=FONT_HEADER, fg=WARNING, bg=VOID, anchor="w").pack(anchor="w")
        tk.Label(header, text="Containment record loaded from lobcorp_grades.txt. Handle with caution.",
                 font=FONT_SUBTITLE, fg=MUTED, bg=VOID, anchor="w").pack(anchor="w", pady=(2, 0))
        tk.Frame(header, bg=TEAL, height=2).pack(fill="x", pady=(14, 0))

    def _build_student_info(self) -> None:
        info = tk.Frame(self, bg=VOID, padx=28, pady=14)
        info.grid(row=1, column=0, sticky="ew")
        self.student_value = labeled_field(info, "EMPLOYEE", 0)
        self.program_value = labeled_field(info, "PROGRAM & YEAR", 1)
        self.honors_value = labeled_field(info, "CLEARANCE STATUS", 2)

    def _build_table(self) -> None:
        table_wrap = tk.Frame(self, bg=VOID, padx=28)
        table_wrap.grid(row=2, column=0, sticky="ew")

        style = ttk.Style()
        style.theme_use("default")
        style.configure("Lob.Treeview", background=PANEL, fieldbackground=PANEL,
                         foreground=BONE, rowheight=26, borderwidth=0, font=FONT_MONO)
        style.configure("Lob.Treeview.Heading", background=VOID, foreground=WARNING,
                         font=FONT_MONO_SMALL, relief="flat")
        style.map("Lob.Treeview", background=[("selected", TEAL)], foreground=[("selected", VOID)])

        columns = ("code", "name", "units", "grade")
        self.tree = ttk.Treeview(table_wrap, columns=columns, show="headings",
                                  height=8, style="Lob.Treeview", selectmode="browse")
        for col, label, w in [("code", "COURSE CODE", 100), ("name", "COURSE TITLE", 260),
                               ("units", "UNITS", 70), ("grade", "GRADE", 70)]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=w, anchor="w")
        self.tree.pack(fill="x", pady=(0, 12))

        self.totals_label = tk.Label(
            self, text="Total Units: 0  |  Weighted Average: 0.00",
            font=FONT_MONO, fg=WARNING, bg=VOID, anchor="w", padx=28)
        self.totals_label.grid(row=3, column=0, sticky="ew", pady=(0, 14))

    def _build_table_actions(self) -> None:
        actions = tk.Frame(self, bg=VOID, padx=28)
        actions.grid(row=4, column=0, sticky="w", pady=(0, 18))
        styled_button(actions, "RELOAD lobcorp_grades.txt", self.on_reload,
                      bg=VOID, fg=MUTED).pack(side="left")

    def _build_email_section(self) -> None:
        email_wrap = tk.Frame(self, bg=VOID, padx=28)
        email_wrap.grid(row=5, column=0, sticky="ew")

        tk.Label(email_wrap, text="TRANSMISSION RECIPIENT", font=FONT_LABEL,
                 fg=MUTED, bg=VOID, anchor="w").pack(anchor="w")
        self.recipient_var = tk.StringVar(value="")
        tk.Entry(email_wrap, textvariable=self.recipient_var, width=48,
                 font=FONT_MONO, bg=PANEL, fg=BONE, insertbackground=BONE, relief="flat",
                 highlightthickness=1, highlightbackground=LINE, highlightcolor=TEAL
                 ).pack(anchor="w", pady=(4, 12))

        actions = tk.Frame(email_wrap, bg=VOID)
        actions.pack(anchor="w", fill="x")
        styled_button(actions, "◈ TRANSMIT REPORT", self.on_send,
                      bg=TEAL, fg=VOID, hover_bg=TEAL_HOVER, font=FONT_BTN).pack(side="left")
        styled_button(actions, "CLEAR LOG", self.on_clear, bg=VOID, fg=MUTED).pack(side="left", padx=(10, 0))

    def _build_log(self) -> None:
        log_wrap = tk.Frame(self, bg=VOID, padx=28)
        log_wrap.grid(row=6, column=0, sticky="ew", pady=(18, 24))
        tk.Label(log_wrap, text="CONTAINMENT LOG", font=FONT_LABEL, fg=WARNING, bg=VOID).pack(anchor="w", pady=(0, 6))
        self.log = tk.Text(log_wrap, height=8, width=76, font=FONT_MONO,
                            bg=LOG_BG, fg=LOG_TEXT, relief="flat", padx=10, pady=8,
                            insertbackground=LOG_TEXT, highlightthickness=1,
                            highlightbackground=LINE, state="disabled")
        self.log.pack(fill="x")

    # -------------------------- data refresh --------------------------

    def refresh_table(self) -> None:
        for row in self.tree.get_children():
            self.tree.delete(row)
        for s in self.manager.subjects:
            self.tree.insert("", "end", values=s.as_row())
        self.totals_label.configure(
            text=f"Total Units: {self.manager.total_units():g}  |  "
                 f"Weighted Average: {self.manager.weighted_average():.2f}")

    def on_reload(self) -> None:
        self.manager.load()
        self.student_value.configure(text=self.manager.student_name or "—")
        self.program_value.configure(text=self.manager.course_year or "—")
        status = honors_status(self.manager.weighted_average())
        self.honors_value.configure(text=status)
        self.refresh_table()
        if self.manager.skipped_lines:
            self.write(f"NOTE -> skipped {self.manager.skipped_lines} malformed line(s)")
        self.write(f"LOADED -> {len(self.manager.subjects)} course(s) for "
                   f"{self.manager.student_name or 'unknown employee'}")

    def on_send(self) -> None:
        recipient = self.recipient_var.get().strip()
        if not recipient:
            messagebox.showwarning("Missing recipient", "Enter a transmission recipient first.")
            return
        if not self.manager.subjects:
            messagebox.showwarning("Nothing to send", "No courses loaded.")
            return
        try:
            line = send_brevo_email(
                recipient,
                self.manager.report_html(),
                subject=f"LobCorp Grade Report — {self.manager.student_name or 'Employee'}",
            )
        except Exception as exc:
            self.write(f"FAILED -> {recipient}: {exc}")
            messagebox.showerror("Transmission failed", str(exc))
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
    root.title("Lobotomy Corporation — Grade Management Terminal")
    root.configure(bg=VOID)
    root.resizable(False, False)
    GradeReportApp(root).pack()
    root.mainloop()


if __name__ == "__main__":
    main()
