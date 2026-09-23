import os
import queue
import subprocess
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from pathlib import Path
from core import Runner, Settings, Cancelled, youtube_url, configure_runtime_tools

configure_runtime_tools()


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Acapella Downloader · Thermal")
        self.geometry("1180x860")
        self.minsize(1120, 840)
        self.configure(bg="#0d1c21")
        self.events = queue.Queue()
        self.runner = None
        self.busy = False
        self.results = []
        self.settings = Settings()
        self.output = tk.StringVar(value=self.settings.load()["output"])
        self.query, self.url, self.song, self.key, self.bpm = [tk.StringVar() for _ in range(5)]
        self.status = tk.StringVar(value="Ready when you are.")
        self.track_name = tk.StringVar(value="Your next acapella.")
        self.configure_styles()

        shell = ttk.Frame(self, padding=24)
        shell.pack(fill="both", expand=True)
        header = ttk.Frame(shell)
        header.pack(fill="x", pady=(0, 22))
        ttk.Label(header, text="ACAPELLA /", style="Brand.TLabel").pack(side="left")
        ttk.Label(header, text="THERMAL EDITION", style="Micro.TLabel").pack(side="left", padx=16)
        ttk.Label(header, text="●  LOCAL VOCAL EXTRACTION", style="Accent.TLabel").pack(side="right")

        body = ttk.Frame(shell)
        body.pack(fill="both", expand=True)
        left = ttk.Frame(body, width=401)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)
        ttk.Label(left, text="KEEP THE VOICE.", style="Hero.TLabel").pack(anchor="w")
        ttk.Label(left, text="MAKE IT YOURS.", style="HeroAccent.TLabel").pack(anchor="w")
        ttk.Label(left, text="A little heat for your next session.", style="Muted.TLabel").pack(anchor="w", pady=(6,18))
        self.cover = tk.Canvas(left, width=401, height=396, bg="#14252b", highlightthickness=0)
        self.cover.pack(anchor="w")
        self.draw_thermal()
        ttk.Label(left, textvariable=self.track_name, style="Track.TLabel", wraplength=390).pack(anchor="w", pady=(18,6))
        ttk.Label(left, text="VOCALS ONLY    /    MP3    /    320 KB/S", style="Micro.TLabel").pack(anchor="w")
        spectrum = tk.Canvas(left, width=390, height=38, bg="#0d1c21", highlightthickness=0)
        spectrum.pack(anchor="w", pady=(18,8))
        # Decorative thermal spectrum, not an audio waveform or progress meter.
        colors = ["#657666", "#9ba45f", "#ced77b", "#d7c770", "#cd9662", "#c86555", "#983e65"]
        for index in range(65):
            height = 4 + ((index * 17 + index * index * 3) % 29)
            spectrum.create_rectangle(index*6, 19-height/2, index*6+3, 19+height/2, fill=colors[min(index//10,6)], outline="")
        ttk.Label(left, text="Select a track. Find the voice underneath.", style="Muted.TLabel").pack(anchor="w")

        separator = tk.Frame(body, bg="#2a3b3d", width=1)
        separator.pack(side="left", fill="y", padx=24)
        right = ttk.Frame(body)
        right.pack(side="left", fill="both", expand=True)
        self.section(right, "01", "FIND YOUR TRACK")
        row = ttk.Frame(right)
        row.pack(fill="x", pady=(10,10))
        entry = ttk.Entry(row, textvariable=self.query)
        entry.pack(side="left", fill="x", expand=True)
        entry.bind("<Return>", lambda event: self.search())
        self.search_button = ttk.Button(row, text="Search YouTube", command=self.search)
        self.search_button.pack(side="left", padx=(8,0))
        table_frame = ttk.Frame(right)
        table_frame.pack(fill="x")
        self.table = ttk.Treeview(table_frame, columns=("title", "channel", "duration"), show="headings", height=4, selectmode="browse")
        for name, width in [("title", 280), ("channel", 130), ("duration", 65)]:
            self.table.heading(name, text={"title":"TRACK", "channel":"CHANNEL", "duration":"TIME"}[name])
            self.table.column(name, width=width, minwidth=50, stretch=name != "duration")
        self.table.pack(side="left", fill="x", expand=True)
        scrollbar = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        scrollbar.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scrollbar.set)
        self.table.bind("<<TreeviewSelect>>", self.select)
        self.empty_hint = ttk.Label(table_frame, text="Search by artist + song to get started.", style="Empty.TLabel")
        self.empty_hint.place(relx=.5, rely=.6, anchor="center")
        ttk.Label(right, text="Or paste a YouTube video link", style="Muted.TLabel").pack(anchor="w", pady=(10,4))
        ttk.Entry(right, textvariable=self.url).pack(fill="x")

        self.section(right, "02", "SHAPE YOUR EXPORT", top=20)
        ttk.Label(right, text="Song title · leave blank to use the video title", style="Muted.TLabel").pack(anchor="w", pady=(10,4))
        ttk.Entry(right, textvariable=self.song).pack(fill="x")
        row = ttk.Frame(right)
        row.pack(fill="x", pady=(8,0))
        for index, (label, variable) in enumerate([("Key · blank = detect", self.key), ("BPM · blank = detect", self.bpm)]):
            field = ttk.Frame(row)
            field.pack(side="left", fill="x", expand=True, padx=(0,10) if index == 0 else (0,0))
            ttk.Label(field, text=label, style="Muted.TLabel").pack(anchor="w", pady=(0,4))
            ttk.Entry(field, textvariable=variable, width=12).pack(fill="x")
        ttk.Label(right, text="Automatic key and tempo are estimates.", style="Muted.TLabel").pack(anchor="w", pady=(5,0))

        self.section(right, "03", "SAVE TO YOUR COLLECTION", top=18)
        ttk.Entry(right, textvariable=self.output, state="readonly").pack(fill="x", pady=(10,6))
        row = ttk.Frame(right)
        row.pack(fill="x")
        self.folder_button = ttk.Button(row, text="Choose folder", command=self.choose)
        self.folder_button.pack(side="left")
        ttk.Button(row, text="Open folder ↗", command=self.open_folder).pack(side="left", padx=8)
        ttk.Label(row, text="Saved for next time", style="Muted.TLabel").pack(side="right")
        row = ttk.Frame(right)
        row.pack(fill="x", pady=(16,10))
        self.start_button = ttk.Button(row, text="↓  Download acapella", style="Primary.TButton", command=self.start)
        self.start_button.pack(side="left", fill="x", expand=True)
        self.local_button = ttk.Button(row, text="Use local audio", command=self.local)
        self.local_button.pack(side="left", padx=(8,0))
        self.cancel_button = ttk.Button(row, text="Cancel", command=self.cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(8,0))
        ttk.Label(right, textvariable=self.status, style="Muted.TLabel", wraplength=610).pack(anchor="w")
        self.progress = ttk.Progressbar(right, mode="indeterminate")
        self.progress.pack(fill="x", pady=(8,8))
        self.log = tk.Text(right, height=2, bg="#11252a", fg="#9cafa9", relief="flat", bd=0,
            font=("Consolas", 9), state="disabled", wrap="word", padx=10, pady=8)
        self.log.pack(fill="both", expand=True)
        self.after(100, self.poll)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure(".", font=("Segoe UI", 10), background="#0d1c21", foreground="#e4e7d9")
        style.configure("TFrame", background="#0d1c21")
        style.configure("TLabel", background="#0d1c21", foreground="#e4e7d9")
        style.configure("Brand.TLabel", font=("Segoe UI", 18, "bold"), foreground="#e8edcb")
        style.configure("Hero.TLabel", font=("Segoe UI", 30, "bold"), foreground="#e6e9d5")
        style.configure("HeroAccent.TLabel", font=("Segoe UI", 30, "bold"), foreground="#ced77b")
        style.configure("Track.TLabel", font=("Segoe UI", 15, "bold"), foreground="#e6e9d5")
        style.configure("Micro.TLabel", font=("Segoe UI", 9), foreground="#96aaa1")
        style.configure("Accent.TLabel", font=("Segoe UI", 9, "bold"), foreground="#ced77b")
        style.configure("Muted.TLabel", font=("Segoe UI", 9), foreground="#a4b5ae")
        style.configure("Section.TLabel", font=("Segoe UI", 10, "bold"), foreground="#e6e9d5")
        style.configure("Empty.TLabel", background="#12272d", foreground="#879e98", font=("Segoe UI", 10))
        style.configure("TEntry", fieldbackground="#183036", foreground="#edf0df", bordercolor="#34494b", lightcolor="#34494b", darkcolor="#34494b", insertcolor="#d4df8a", padding=8)
        style.map("TEntry", fieldbackground=[("readonly", "#152a30")], foreground=[("readonly", "#abbeb5")], bordercolor=[("focus", "#bdc873")])
        style.configure("TButton", background="#20383c", foreground="#e1e6d7", bordercolor="#34494b", lightcolor="#34494b", darkcolor="#34494b", padding=(10,8), focusthickness=1, focuscolor="#b9c77e")
        style.map("TButton", background=[("disabled", "#162b30"), ("active", "#304c4b")], foreground=[("disabled", "#647c77")])
        style.configure("Primary.TButton", background="#d1d985", foreground="#142328", bordercolor="#d1d985", lightcolor="#d1d985", darkcolor="#d1d985", font=("Segoe UI", 10, "bold"))
        style.map("Primary.TButton", background=[("disabled", "#66734f"), ("active", "#e3eaa3")], foreground=[("disabled", "#b7c39a"), ("active", "#142328")])
        style.configure("Treeview", background="#12272d", fieldbackground="#12272d", foreground="#d9e2d5", borderwidth=0, rowheight=25)
        style.configure("Treeview.Heading", background="#1b3338", foreground="#9eb2a6", font=("Segoe UI", 8, "bold"), relief="flat", padding=6)
        style.map("Treeview", background=[("selected", "#465445")], foreground=[("selected", "#f0f2cf")])
        style.map("Treeview.Heading", background=[("active", "#294347")])
        style.configure("Horizontal.TProgressbar", troughcolor="#1c3539", background="#ccd67d", borderwidth=0, thickness=4)
        style.configure("Vertical.TScrollbar", background="#34504e", troughcolor="#12272d", bordercolor="#12272d", arrowcolor="#b7c4a3")

    def section(self, parent, number, title, top=0):
        row = ttk.Frame(parent)
        row.pack(fill="x", pady=(top,0))
        ttk.Label(row, text=number, style="Accent.TLabel").pack(side="left", padx=(0,10))
        ttk.Label(row, text=title, style="Section.TLabel").pack(side="left")

    def draw_thermal(self):
        # Procedural interface artwork: soft thermal contours with subtle grain.
        # Decorative only; does not pretend to show analysis of the current song.
        import math
        import random
        rng = random.Random(27)
        palette = [(14,31,37), (26,47,51), (76,101,97), (130,148,114),
                   (177,185,95), (207,208,104), (205,153,83), (188,101,66),
                   (158,57,75), (123,39,78), (199,122,116)]
        rows = []
        for y in range(198):
            row = []
            for x in range(201):
                u, v = x/200, y/197
                curve = .47 + .21*math.sin(v*7.8-1.1)
                core = math.exp(-((u-curve)/(.105+.05*math.sin(v*5)**2))**2)
                core *= .64+.30*math.sin(v*5.4+.2)**2
                satellite = .48*math.exp(-(((u-.23)/.17)**2+((v-.70)/.23)**2))
                heat = min(1, max(0, core+satellite))
                value = heat*(len(palette)-1)
                index = min(int(value), len(palette)-2)
                blend = value-index
                grain = rng.uniform(-3.4, 3.4)
                color = [int(max(0,min(255,palette[index][i]*(1-blend)+palette[index+1][i]*blend+grain))) for i in range(3)]
                row.append('#%02x%02x%02x' % tuple(color))
            rows.append('{'+' '.join(row)+'}')
        image = tk.PhotoImage(width=201, height=198)
        image.put(' '.join(rows))
        self.cover_image = image.zoom(2)
        self.cover.create_image(0, 0, image=self.cover_image, anchor="nw")
        self.cover.create_text(22, 26, text="THERMAL / 01", anchor="nw", fill="#e0e5c4", font=("Segoe UI", 9, "bold"))
        self.cover.create_text(22, 315, text="FIND THE\nFREQUENCY.", anchor="nw", fill="#f0efd4", font=("Segoe UI", 22, "bold"))

    def write(self, value):
        self.log.configure(state="normal"); self.log.insert("end", str(value) + "\n"); self.log.see("end"); self.log.configure(state="disabled")

    def work(self, action, kind):
        if self.busy:
            return
        self.busy = True
        for button in (self.start_button, self.local_button, self.search_button, self.folder_button):
            button.configure(state="disabled")
        self.cancel_button.configure(state="normal")
        self.progress.start(12)
        self.runner = Runner(lambda name, data: self.events.put((name, data)))
        runner = self.runner
        def worker():
            try:
                self.events.put((kind, action(runner)))
            except Cancelled as error:
                self.events.put(("cancelled", str(error)))
            except Exception as error:
                self.events.put(("error", str(error)))
            finally:
                self.events.put(("idle", None))
        threading.Thread(target=worker, daemon=True).start()

    def search(self):
        if self.busy:
            return
        query = self.query.get().strip()
        if not query:
            return
        self.status.set("Searching YouTube…")
        self.work(lambda runner: runner.search(query), "results")

    def select(self, event=None):
        if self.busy:
            return
        selection = self.table.selection()
        if selection:
            item = self.results[int(selection[0])]
            self.url.set("https://www.youtube.com/watch?v=" + item["id"])
            self.song.set("")
            self.track_name.set(item.get("title", "Selected track"))

    def choose(self):
        path = filedialog.askdirectory(title="Choose your default acapella folder")
        if path:
            try:
                self.settings.save(path)
                self.output.set(path)
            except OSError as error:
                messagebox.showerror("Could not save folder", str(error))

    def open_folder(self):
        try:
            path = Path(self.output.get()); path.mkdir(parents=True, exist_ok=True)
            if os.name == "nt":
                os.startfile(str(path))
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except OSError as error:
            messagebox.showerror("Could not open folder", str(error))

    def local(self):
        if self.busy:
            return
        path = filedialog.askopenfilename(title="Choose a song", filetypes=[("Audio", "*.mp3 *.wav *.flac *.m4a *.ogg *.aac"), ("All files", "*.*")])
        if path:
            self.track_name.set(Path(path).stem)
            self.start(local=path)

    def start(self, local=None):
        if self.busy:
            return
        try:
            url = "" if local else youtube_url(self.url.get())
            self.settings.save(self.output.get())
            values = (url, self.output.get(), self.song.get().strip(), self.key.get().strip(), self.bpm.get().strip())
            self.status.set("Starting…")
            self.work(lambda runner: runner.process(*values, local=local), "done")
        except Exception as error:
            messagebox.showerror("Cannot start", str(error))

    def cancel(self):
        if self.runner:
            self.runner.cancelled.set()
            self.status.set("Cancelling…")

    def poll(self):
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "idle":
                    self.busy = False
                    self.progress.stop()
                    for button in (self.start_button, self.local_button, self.search_button, self.folder_button):
                        button.configure(state="normal")
                    self.cancel_button.configure(state="disabled")
                elif kind == "results":
                    self.results = value
                    if value:
                        self.empty_hint.place_forget()
                    else:
                        self.empty_hint.configure(text="No matches. Try another artist or title.")
                        self.empty_hint.place(relx=.5, rely=.6, anchor="center")
                    for item in self.table.get_children(): self.table.delete(item)
                    for i, item in enumerate(value):
                        seconds = item.get("duration")
                        duration = f"{int(seconds)//60}:{int(seconds)%60:02}" if seconds else "—"
                        self.table.insert("", "end", iid=str(i), values=(item.get("title", ""), item.get("channel") or item.get("uploader", ""), duration))
                    self.status.set("Select a result, then download." if value else "No results. Try another query.")
                elif kind == "done":
                    self.status.set("Saved · " + Path(value).name)
                    self.track_name.set(Path(value).stem)
                    self.write("Saved: " + str(value))
                elif kind in ("error", "cancelled"):
                    self.status.set("Processing failed — see details below." if kind == "error" else value)
                    self.write(value)
                elif kind == "stage":
                    self.status.set(value); self.write(value)
                else:
                    self.write(value)
        except queue.Empty:
            pass
        self.after(100, self.poll)

    def close(self):
        if self.busy:
            self.cancel()
            self.after(200, self.close_when_idle)
        else:
            self.destroy()

    def close_when_idle(self):
        if self.busy:
            self.after(200, self.close_when_idle)
        else:
            self.destroy()


if __name__ == "__main__":
    App().mainloop()
