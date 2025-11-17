import threading
import queue
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
import webbrowser
import os

from engine.pipeline import proxy_and_test, apply_single, apply_multi
from engine.validator import load_and_validate_recipes
from engine.ffmpeg_check import check_ffmpeg

BASE_DIR = Path(__file__).resolve().parent
# IMPORTANT: recipes.json is loaded from the current working directory
# (for the .exe this is the folder where the executable resides)
RECIPES_PATH = Path.cwd() / "recipes.json"


# ============================================================
#  MAIN APPLICATION
# ============================================================
class MainApp(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("FFmpeg Proxy Sandbox – GUI")
        self.geometry("960x690")
        self.minsize(900, 650)

        self.ffmpeg_ok = False
        self.busy = False
        self.default_status_bg = "#666666"
        self.banner_after_id = None

        self.log_queue = queue.Queue()
        self.status_queue = queue.Queue()

        self.recipes = {}
        self.recipe_ids = []

        self._build_ui()
        self._initial_env_check()
        self.after(100, self._poll_queues)

    # ============================================================
    #  TIME PARSER (NEW FIXED VERSION)
    # ============================================================
    def _time_to_seconds(self, s: str) -> int:
        """
        Converts time formats safely:
          - "90"         → 90
          - "02:10"      → 130
          - "00:07"      → 7
          - "01:02:10"   → 3730
        Handles leading zeros without errors.
        """
        s = s.strip()

        # simple seconds
        if ":" not in s:
            if not s.isdigit():
                raise ValueError("Invalid seconds format")
            return int(s)

        parts = s.split(":")
        norm = []

        for part in parts:
            part = part.strip()
            if not part.isdigit():
                raise ValueError("Invalid time segment")
            norm.append(int(part))

        if len(norm) == 2:       # mm:ss
            m, s = norm
            return m * 60 + s

        if len(norm) == 3:       # hh:mm:ss
            h, m, s = norm
            return h * 3600 + m * 60 + s

        raise ValueError("Invalid time format")

    # ============================================================
    #  UI STRUCTURE
    # ============================================================
    def _build_ui(self):

        # Notebook container
        top_frame = ttk.Frame(self)
        top_frame.pack(side="top", fill="both", expand=True)

        self.notebook = ttk.Notebook(top_frame)
        self.notebook.pack(side="top", fill="both", expand=True, padx=8, pady=(8, 4))

        self.tab_test_outer = ttk.Frame(self.notebook)
        self.tab_apply = ttk.Frame(self.notebook)
        self.tab_settings = ttk.Frame(self.notebook)

        self.notebook.add(self.tab_test_outer, text="Test")
        self.notebook.add(self.tab_apply, text="Apply")
        self.notebook.add(self.tab_settings, text="Settings")

        # ------------------ STATUS BANNER ------------------
        self.banner_container = tk.Frame(self, bg=self.default_status_bg)
        self.status_label = tk.Label(
            self.banner_container,
            text="",
            fg="white",
            bg=self.default_status_bg,
            anchor="w",
            padx=12,
            pady=6,
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.status_close = tk.Button(
            self.banner_container,
            text="✕",
            fg="white",
            bg=self.default_status_bg,
            bd=0,
            padx=10,
            pady=2,
            command=self._hide_status
        )
        self.status_close.pack(side="right")
        self.banner_container.pack_forget()

        # ------------------ LOG PANEL ------------------
        log_frame = ttk.Frame(self)
        log_frame.pack(side="bottom", fill="both", padx=8, pady=8)

        ttk.Label(log_frame, text="Log:").pack(anchor="w")

        text_frame = ttk.Frame(log_frame)
        text_frame.pack(fill="both", expand=True)

        self.log_text = tk.Text(
            text_frame,
            wrap="none",
            height=10,
            state="disabled",
            borderwidth=1,
            relief="solid"
        )
        self.log_text.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=self.log_text.yview)
        scrollbar.pack(side="right", fill="y")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        # Clear button right-aligned
        btn_frame = ttk.Frame(log_frame)
        btn_frame.pack(fill="x")
        ttk.Button(
            btn_frame,
            text="Clear Log",
            command=self._on_clear_log
        ).pack(side="right", padx=4, pady=4)

        # Build tabs
        self._build_tab_test()
        self._build_tab_apply()
        self._build_tab_settings()

    # ============================================================
    #  TEST TAB (scrollable)
    # ============================================================
    def _build_tab_test(self):

        canvas = tk.Canvas(self.tab_test_outer)
        canvas.pack(side="left", fill="both", expand=True)

        scrollbar = ttk.Scrollbar(self.tab_test_outer, orient="vertical", command=canvas.yview)
        scrollbar.pack(side="right", fill="y")

        canvas.configure(yscrollcommand=scrollbar.set)

        inner_frame = ttk.Frame(canvas)
        canvas.create_window((0, 0), window=inner_frame, anchor="nw", tags=("window",))

        def _on_frame_configure(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig("window", width=canvas.winfo_width())

        inner_frame.bind("<Configure>", _on_frame_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig("window", width=e.width))

        self.tab_test = inner_frame

        inner_frame.columnconfigure(0, weight=1)
        inner_frame.columnconfigure(1, weight=1)

        # LEFT SIDE
        left = ttk.Frame(inner_frame, padding=10)
        left.grid(row=0, column=0, sticky="nw")

        ttk.Label(left, text="Duration (seconds):").pack(anchor="w")
        self.test_duration_var = tk.StringVar(value="5")
        ttk.Entry(left, textvariable=self.test_duration_var, width=12).pack(anchor="w", pady=(0, 12))

        # Keep Proxy Checkbox
        self.keep_proxy_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            left,
            text="Keep proxy files (do not delete)",
            variable=self.keep_proxy_var
        ).pack(anchor="w", pady=(0, 12))

        ttk.Label(left, text="Start time (seconds or hh:mm:ss):").pack(anchor="w")

        self.start_entries_frame = ttk.Frame(left)
        self.start_entries_frame.pack(anchor="nw")

        self.start_entries = []
        self._add_start_entry("0")

        btn_row = ttk.Frame(left)
        btn_row.pack(anchor="w", pady=6)

        ttk.Button(btn_row, text="+", width=3, command=lambda: self._add_start_entry("")).pack(side="left")
        ttk.Button(btn_row, text="-", width=3, command=self._remove_last_start_entry).pack(side="left", padx=(6, 0))

        # RIGHT SIDE
        right = ttk.Frame(inner_frame, padding=10)
        right.grid(row=0, column=1, sticky="ne")
        right.columnconfigure(0, weight=1)

        ttk.Label(right, text="Input:").grid(row=0, column=0, sticky="w")
        input_row = ttk.Frame(right)
        input_row.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        input_row.columnconfigure(0, weight=1)

        self.test_input_var = tk.StringVar()
        ttk.Entry(input_row, textvariable=self.test_input_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(input_row, text="Browse...", command=self._on_browse_test_input).grid(row=0, column=1, padx=6)

        ttk.Label(right, text="Output folder (test_out):").grid(row=2, column=0, sticky="w")
        out_row = ttk.Frame(right)
        out_row.grid(row=3, column=0, sticky="ew")
        out_row.columnconfigure(0, weight=1)

        self.test_outdir_var = tk.StringVar(value=str(BASE_DIR / "test_output"))
        ttk.Entry(out_row, textvariable=self.test_outdir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(out_row, text="Browse...", command=self._on_browse_test_outdir).grid(row=0, column=1, padx=6)

        # RECIPES
        ttk.Label(inner_frame, text="Recipes (select at least one):").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=20
        )
        self.test_recipe_frame = ttk.Frame(inner_frame)
        self.test_recipe_frame.grid(row=2, column=0, columnspan=2, sticky="w", padx=20, pady=(0, 12))
        self.test_recipe_vars = {}

        # BUTTONS
        btn_row = ttk.Frame(inner_frame)
        btn_row.grid(row=3, column=0, columnspan=2, sticky="ew", padx=20, pady=(12, 16))

        self.btn_run_test = ttk.Button(btn_row, text="Run Test", command=self._on_run_test)
        self.btn_run_test.pack(side="left", expand=True, fill="x")

        self.btn_test_open = ttk.Button(btn_row, text="Open Folder", command=self._on_test_open_folder)
        self.btn_test_open.pack(side="right", padx=(8, 0))
        self.btn_test_open.config(state="disabled")

    def _add_start_entry(self, value):
        e = ttk.Entry(self.start_entries_frame, width=10)
        e.insert(0, value)
        e.pack(anchor="w", pady=2)
        self.start_entries.append(e)

    def _remove_last_start_entry(self):
        if len(self.start_entries) > 1:
            e = self.start_entries.pop()
            e.destroy()

    def _on_browse_test_input(self):
        p = filedialog.askopenfilename(
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi"), ("All Files", "*.*")]
        )
        if p:
            self.test_input_var.set(p)

    def _on_browse_test_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.test_outdir_var.set(p)

    # ============================================================
    #  RUN TEST
    # ============================================================
    def _on_run_test(self):
        if self.busy:
            return

        input_file = self.test_input_var.get().strip()
        if not input_file:
            messagebox.showerror("Error", "No input video selected.")
            return

        raw_starts = [e.get().strip() for e in self.start_entries if e.get().strip()]
        if not raw_starts:
            messagebox.showerror("Error", "At least one start value is required.")
            return

        converted = []
        for val in raw_starts:
            try:
                converted.append(str(self._time_to_seconds(val)))
            except:
                messagebox.showerror("Error", f"Invalid time format: {val}")
                return

        start_list = ",".join(converted)

        duration = self.test_duration_var.get().strip()

        recipes = [rid for rid, var in self.test_recipe_vars.items() if var.get()]
        if not recipes:
            messagebox.showerror("Error", "Select at least one recipe.")
            return

        pick = ",".join(recipes)
        outdir = self.test_outdir_var.get().strip()

        self._set_busy(True)
        self._push_status("info", "Running Test...")

        def worker():
            res = proxy_and_test(
                input_file=input_file,
                start_list=start_list,
                duration=duration,
                recipes_json=str(RECIPES_PATH),
                pick=pick,
                outdir=outdir,
                log=self._log_callback,
                keep_proxy=self.keep_proxy_var.get()
            )
            if not res.get("ok"):
                self._push_status("error", res.get("error"))
                self.btn_test_open.config(state="disabled")
            else:
                self._push_status("ok", "Test completed.")
                self.btn_test_open.config(state="normal")

            self._set_busy(False)

        threading.Thread(target=worker, daemon=True).start()

    def _on_test_open_folder(self):
        self._open_folder(self.test_outdir_var.get().strip())

    # ============================================================
    #  APPLY TAB
    # ============================================================
    def _build_tab_apply(self):
        f = self.tab_apply

        f.columnconfigure(0, weight=3)
        f.columnconfigure(1, weight=2)

        ttk.Label(f, text="Input files:").grid(row=0, column=0, sticky="w", padx=16, pady=4)

        left = ttk.Frame(f)
        left.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        left.rowconfigure(0, weight=1)
        left.columnconfigure(0, weight=1)

        self.apply_listbox = tk.Listbox(left, height=7)
        self.apply_listbox.grid(row=0, column=0, sticky="nsew")

        btns = ttk.Frame(left)
        btns.grid(row=0, column=1, sticky="ns", padx=(6, 0))

        ttk.Button(btns, text="+", width=4, command=self._on_add_apply_files).pack(pady=3)
        ttk.Button(btns, text="-", width=4, command=self._on_remove_apply_selected).pack(pady=3)

        ttk.Label(f, text="Output folder:").grid(row=0, column=1, sticky="w", padx=16)

        right = ttk.Frame(f)
        right.grid(row=1, column=1, sticky="nsew", padx=16, pady=4)
        right.columnconfigure(0, weight=1)

        self.apply_outdir_var = tk.StringVar(value=str(BASE_DIR / "output"))
        ttk.Entry(right, textvariable=self.apply_outdir_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(right, text="Browse...", command=self._on_browse_apply_outdir).grid(row=0, column=1, padx=6)

        ttk.Label(f, text="Recipe (select one):").grid(
            row=2, column=0, columnspan=2, sticky="w", padx=16, pady=(12, 4)
        )

        self.apply_recipe_frame = ttk.Frame(f)
        self.apply_recipe_frame.grid(row=3, column=0, columnspan=2, sticky="w", padx=16, pady=4)
        self.apply_recipe_var = tk.StringVar()

        btn_row = ttk.Frame(f)
        btn_row.grid(row=4, column=0, columnspan=2, sticky="ew", padx=16, pady=12)

        self.btn_apply = ttk.Button(btn_row, text="Apply", command=self._on_apply)
        self.btn_apply.pack(side="left", expand=True, fill="x")

        self.btn_apply_open = ttk.Button(btn_row, text="Open Folder", command=self._on_apply_open_folder)
        self.btn_apply_open.pack(side="right", padx=(8, 0))
        self.btn_apply_open.config(state="disabled")

    def _on_add_apply_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Video Files", "*.mp4 *.mkv *.mov *.avi"), ("All Files", "*.*")]
        )
        for p in paths:
            if p not in self.apply_listbox.get(0, tk.END):
                self.apply_listbox.insert(tk.END, p)
        self._update_buttons_state()

    def _on_remove_apply_selected(self):
        sel = list(self.apply_listbox.curselection())
        sel.reverse()
        for i in sel:
            self.apply_listbox.delete(i)
        self._update_buttons_state()

    def _on_browse_apply_outdir(self):
        p = filedialog.askdirectory()
        if p:
            self.apply_outdir_var.set(p)

    def _on_apply(self):
        if self.busy:
            return

        files = list(self.apply_listbox.get(0, tk.END))
        if not files:
            messagebox.showerror("Error", "At least one input file is required.")
            return

        recipe_id = self.apply_recipe_var.get().strip()
        if not recipe_id:
            messagebox.showerror("Error", "Select one recipe.")
            return

        outdir = self.apply_outdir_var.get().strip()

        self._set_busy(True)
        self._push_status("info", "Running Apply...")

        # Single file
        if len(files) == 1:
            infile = Path(files[0])
            Path(outdir).mkdir(parents=True, exist_ok=True)
            outfile = str(Path(outdir) / f"{infile.stem}_{recipe_id}.mp4")

            def worker_single():
                res = apply_single(
                    input_file=str(infile),
                    recipe_id=recipe_id,
                    recipes_json=str(RECIPES_PATH),
                    output_file=outfile,
                    log=self._log_callback
                )

                if not res.get("ok"):
                    self._push_status("error", res.get("error"))
                else:
                    self._push_status("ok", "Apply completed.")
                    self.btn_apply_open.config(state="normal")

                self._set_busy(False)

            threading.Thread(target=worker_single, daemon=True).start()

        # Multi-file batch
        else:
            def worker_multi():
                res = apply_multi(
                    input_files=files,
                    recipe_id=recipe_id,
                    recipes_json=str(RECIPES_PATH),
                    output_dir=outdir,
                    log=self._log_callback,
                )

                if not res.get("ok"):
                    self._push_status("error", res.get("error"))
                else:
                    self._push_status("ok", "Batch apply completed.")
                    self.btn_apply_open.config(state="normal")

                self._set_busy(False)

            threading.Thread(target=worker_multi, daemon=True).start()

    def _on_apply_open_folder(self):
        self._open_folder(self.apply_outdir_var.get().strip())

    # ============================================================
    #  SETTINGS TAB
    # ============================================================
    def _build_tab_settings(self):
        f = self.tab_settings

        ttk.Label(f, text="About this Program").pack(anchor="w", padx=16, pady=(16, 4))
        ttk.Label(f, text="FFmpeg Proxy Sandbox GUI.").pack(anchor="w", padx=32)

        ttk.Label(f, text="License").pack(anchor="w", padx=16, pady=(16, 4))
        mit_link = tk.Label(
            f,
            text="MIT License (click to open)",
            fg="blue",
            cursor="hand2"
        )
        mit_link.pack(anchor="w", padx=32)
        mit_link.bind("<Button-1>", lambda e: webbrowser.open("https://opensource.org/licenses/MIT"))

        ttk.Label(f, text="Links").pack(anchor="w", padx=16, pady=(16, 4))

        links = ttk.Frame(f)
        links.pack(anchor="w", padx=32, pady=6)

        ttk.Button(
            links, text="FFmpeg Download",
            command=lambda: webbrowser.open("https://ffmpeg.org/download.html")
        ).pack(anchor="w", pady=2)

        ttk.Button(
            links, text="GitHub Repository",
            command=lambda: webbrowser.open("https://github.com/V3RC0/Proxy-Sanbox-FFMPEG.git")
        ).pack(anchor="w", pady=2)

        env = ttk.LabelFrame(f, text="Environment Check")
        env.pack(fill="x", padx=16, pady=20)

        ttk.Button(env, text="Check FFmpeg", command=self._on_check_ffmpeg).pack(side="left", padx=8, pady=8)
        ttk.Button(env, text="Reload Recipes", command=self._on_reload_recipes).pack(side="left", padx=8, pady=8)

    # ============================================================
    #  ENVIRONMENT CHECK
    # ============================================================
    def _initial_env_check(self):
        self._load_recipes()
        self._refresh_recipe_widgets()
        self._on_check_ffmpeg(update_status_only=True)
        self._update_buttons_state()

    def _on_check_ffmpeg(self, update_status_only=False):
        res = check_ffmpeg()
        if res.get("ok"):
            self.ffmpeg_ok = True
            self._push_status("ok", "FFmpeg OK (found in PATH).")
        else:
            self.ffmpeg_ok = False
            self._push_status("error", res.get("error"))

        self._update_buttons_state()

    def _load_recipes(self):
        if not RECIPES_PATH.exists():
            self._push_status("error", "recipes.json not found.")
            self.recipes = {}
            self.recipe_ids = []
            return

        v = load_and_validate_recipes(RECIPES_PATH)
        if not v.get("ok"):
            self._push_status("error", v.get("error"))
            self.recipes = {}
            self.recipe_ids = []
            return

        self.recipes = v["data"]
        self.recipe_ids = list(self.recipes.keys())
        self._push_status("ok", f"{len(self.recipe_ids)} recipes loaded.")

    def _on_reload_recipes(self):
        self._load_recipes()
        self._refresh_recipe_widgets()
        self._update_buttons_state()

    def _refresh_recipe_widgets(self):
        # TEST
        for w in self.test_recipe_frame.winfo_children():
            w.destroy()
        self.test_recipe_vars = {}

        for rid in self.recipe_ids:
            var = tk.BooleanVar(value=False)
            ttk.Checkbutton(
                self.test_recipe_frame,
                text=rid,
                variable=var,
                command=self._update_buttons_state
            ).pack(side="left", padx=8, pady=6)
            self.test_recipe_vars[rid] = var

        # APPLY
        for w in self.apply_recipe_frame.winfo_children():
            w.destroy()
        self.apply_recipe_var.set("")

        for rid in self.recipe_ids:
            ttk.Radiobutton(
                self.apply_recipe_frame,
                text=rid,
                variable=self.apply_recipe_var,
                value=rid,
                command=self._update_buttons_state
            ).pack(side="left", padx=8, pady=6)

    # ============================================================
    #  LOG & STATUS HANDLING
    # ============================================================
    def _log_callback(self, msg: str):
        self._push_log(msg)

    def _push_log(self, msg: str):
        self.log_queue.put(msg)

    def _push_status(self, kind: str, msg: str):
        self.status_queue.put((kind, msg))

    def _poll_queues(self):
        while True:
            try:
                msg = self.log_queue.get_nowait()
            except queue.Empty:
                break
            self._append_log(msg)

        while True:
            try:
                kind, msg = self.status_queue.get_nowait()
            except queue.Empty:
                break
            self._set_status(kind, msg)

        self.after(100, self._poll_queues)

    def _append_log(self, msg: str):
        self.log_text.configure(state="normal")
        self.log_text.insert("end", msg + "\n")
        self.log_text.see("end")
        self.log_text.configure(state="disabled")

    def _on_clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    # ------------------ STATUS BANNER ------------------
    def _set_status(self, kind: str, msg: str):

        self.banner_container.pack(side="top", fill="x")

        if kind == "error":
            bg = "#b00020"
        elif kind == "ok":
            bg = "#2e7d32"
        else:
            bg = self.default_status_bg

        self.banner_container.config(bg=bg)
        self.status_label.config(text=msg, bg=bg)
        self.status_close.config(bg=bg)

        if self.banner_after_id:
            self.after_cancel(self.banner_after_id)

        self.banner_after_id = self.after(4000, self._hide_status)

    def _hide_status(self):
        self.banner_container.pack_forget()

    # ============================================================
    #  STATE CONTROL
    # ============================================================
    def _set_busy(self, state: bool):
        self.busy = state
        self._update_buttons_state()

    def _update_buttons_state(self):
        any_recipe_test = any(v.get() for v in self.test_recipe_vars.values())
        if self.ffmpeg_ok and any_recipe_test and not self.busy:
            self.btn_run_test.config(state="normal")
        else:
            self.btn_run_test.config(state="disabled")

        has_files = self.apply_listbox.size() > 0
        has_recipe_apply = bool(self.apply_recipe_var.get())
        if self.ffmpeg_ok and has_files and has_recipe_apply and not self.busy:
            self.btn_apply.config(state="normal")
        else:
            self.btn_apply.config(state="disabled")

    # ============================================================
    #  UTILITY
    # ============================================================
    def _open_folder(self, path):
        try:
            os.startfile(path)
        except:
            messagebox.showerror("Error", f"Failed to open folder:\n{path}")


# ============================================================
#  MAIN
# ============================================================
def main():
    app = MainApp()
    app.mainloop()


if __name__ == "__main__":
    main()
