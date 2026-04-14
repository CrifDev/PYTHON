import customtkinter as ctk
from tkinter import messagebox
import time
import json
import os
import csv
from datetime import datetime
import sys

# --- Le Chien Truffier 3000 ---
def get_icon_path():
    # 1. On fouille dans le dossier caché "_internal" de PyInstaller
    if hasattr(sys, '_MEIPASS'):
        chemin_cache = os.path.join(sys._MEIPASS, 'logo.ico')
        if os.path.exists(chemin_cache):
            return chemin_cache
            
    # 2. Sinon, on cherche juste à côté du fichier (exe ou script)
    if getattr(sys, 'frozen', False):
        dossier_base = os.path.dirname(sys.executable)
    else:
        dossier_base = os.path.dirname(os.path.abspath(__file__))
        
    return os.path.join(dossier_base, 'logo.ico')

DATA_FILE = "mes_chronos_sauvegardes.json"
ARCHIVE_FILE = "archives_décomptes.csv"

# [ ... NE TOUCHE PAS A TaskFrame ... ]

class TaskFrame(ctk.CTkFrame):
    def __init__(self, master, app_instance, name, elapsed=0, multiplier="x1"):
        super().__init__(master, border_width=2, border_color="#444444", corner_radius=10)
        
        self.app_instance = app_instance 
        self.name = name
        self.is_running = False
        self.elapsed = elapsed
        self.last_update = 0

        # Pack les widgets fixes en PREMIER (côté droit) pour qu'ils gardent leur taille
        self.archive_btn = ctk.CTkButton(self, text="Archiver", width=80, fg_color="#b8860b", hover_color="#8b6508", command=self.archive)
        self.archive_btn.pack(side="right", padx=10, pady=15)

        self.btn = ctk.CTkButton(self, text="Start", width=80, fg_color="#2FA572", hover_color="#106A43", command=self.toggle)
        self.btn.pack(side="right", padx=5, pady=15)

        self.multiplier = ctk.StringVar(value=multiplier)
        self.mult_menu = ctk.CTkOptionMenu(
            self, 
            values=["x0.5", "x0.75", "x1", "x1.25", "x1.5", "x2", "x3", "x4", "x5", "x10"], 
            variable=self.multiplier, 
            width=75, 
            fg_color="#333333",
            button_color="#444444"
        )
        self.mult_menu.pack(side="right", padx=10)

        self.time_label = ctk.CTkLabel(self, text="00:00:00", width=80, font=("Consolas", 16))
        self.time_label.pack(side="right", padx=10)

        # Poignée de drag (≡) à gauche
        self.drag_handle = ctk.CTkLabel(self, text="\u2261", font=("Arial", 20), width=20, cursor="fleur")
        self.drag_handle.pack(side="left", padx=(10, 2), pady=15)

        # Label prend l'espace restant — packé en DERNIER
        self.label = ctk.CTkLabel(self, text=self.name, anchor="w", font=("Arial", 14, "bold"))
        self.label.pack(side="left", padx=(5, 15), pady=15, fill="x", expand=True)

        self.bind("<Configure>", self._clamp_label_width)
        self._clamp_label_width()

        # Drag & drop bindings
        self.drag_handle.bind("<ButtonPress-1>", self._on_drag_start)
        self.drag_handle.bind("<B1-Motion>", self._on_drag_motion)
        self.drag_handle.bind("<ButtonRelease-1>", self._on_drag_end)

        self.update_display()

    def _clamp_label_width(self, event=None):
        reserved = 420
        available = self.winfo_width() - reserved
        max_chars = max(5, available // 8)
        if len(self.name) > max_chars:
            self.label.configure(text=self.name[:max_chars] + "\u2026")
        else:
            self.label.configure(text=self.name)

    def _on_drag_start(self, event):
        self.app_instance._drag_task = self
        self.configure(border_color="#2FA572")

    def _on_drag_motion(self, event):
        app = self.app_instance
        y = event.widget.winfo_rooty() + event.y
        # Reset les bordures de tous les chronos
        for task in app.tasks:
            if task is not self:
                task.configure(border_color="#444444")
        # Trouve la position cible
        target_idx = len(app.tasks)
        for i, task in enumerate(app.tasks):
            task_y = task.winfo_rooty()
            task_h = task.winfo_height()
            if y < task_y + task_h // 2:
                target_idx = i
                break
        app._drag_target_index = target_idx
        # Highlight la cible
        if target_idx < len(app.tasks) and app.tasks[target_idx] is not self:
            app.tasks[target_idx].configure(border_color="#2FA572")

    def _on_drag_end(self, event):
        self.configure(border_color="#444444")
        app = self.app_instance
        for task in app.tasks:
            task.configure(border_color="#444444")
        if hasattr(app, '_drag_task') and hasattr(app, '_drag_target_index'):
            old_index = app.tasks.index(self)
            new_index = app._drag_target_index
            if new_index > old_index:
                new_index -= 1
            if old_index != new_index:
                app.tasks.pop(old_index)
                new_index = max(0, min(new_index, len(app.tasks)))
                app.tasks.insert(new_index, self)
                app._repack_tasks()
            del app._drag_task
            del app._drag_target_index

    def toggle(self):
        if self.is_running:
            self.update_time()
            self.is_running = False
            self.btn.configure(text="Start", fg_color="#2FA572")
        else:
            self.last_update = time.time()
            self.is_running = True
            self.btn.configure(text="Stop", fg_color="#C93B3B", hover_color="#8B1A1A")

    def update_time(self):
        if self.is_running:
            now = time.time()
            diff = now - self.last_update
            mult = float(self.multiplier.get().replace("x", ""))
            self.elapsed += diff * mult
            self.last_update = now
        self.update_display()

    def update_display(self):
        m, s = divmod(int(self.elapsed), 60)
        h, m = divmod(m, 60)
        self.time_label.configure(text=f"{h:02d}:{m:02d}:{s:02d}")
        
    def get_formatted_time(self):
        m, s = divmod(int(self.elapsed), 60)
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}:{s:02d}"

    def archive(self):
        if self.is_running:
            messagebox.showerror("Hé ho !", "Tu essaies d'archiver un chrono qui tourne ! Mets-le en pause.")
            return
            
        confirm = messagebox.askyesno("Facturation", f"T'es sûr de vouloir archiver '{self.name}' ?")
        
        if confirm:
            self.app_instance.archive_task(self)

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("DenisChrono")
        self.geometry("850x750") 
        
        # --- L'astuce mortelle : on force l'icône 200 millisecondes APRES l'ouverture ---
        self.after(200, self.force_icon)
        
        self.tasks = []

        self.entry = ctk.CTkEntry(self, placeholder_text="Nom de la tâche...", height=40, font=("Arial", 14))
        self.entry.pack(pady=15, padx=15, fill="x")

        self.add_btn = ctk.CTkButton(self, text="Ajouter Chrono", height=35, font=("Arial", 14, "bold"), command=self.add_task)
        self.add_btn.pack(pady=5)

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.scroll.pack(pady=10, padx=15, fill="both", expand=True)

        self.folder_btn = ctk.CTkButton(self, text="📁 Ouvrir le dossier des archives", fg_color="#444444", hover_color="#222222", command=self.open_folder)
        self.folder_btn.pack(pady=10)

        self.load_data()
        self.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.update_clocks()

    def force_icon(self):
        chemin_icone = get_icon_path()
        if os.path.exists(chemin_icone):
            try:
                self.iconbitmap(chemin_icone)
            except Exception as e:
                print("Windows refuse l'icône :", e)
        else:
            print("L'icône est introuvable au chemin :", chemin_icone)

    def add_task(self):
        name = self.entry.get()
        if name:
            task = TaskFrame(self.scroll, self, name) 
            task.pack(fill="x", pady=8)
            self.tasks.append(task)
            self.entry.delete(0, 'end')

    def update_clocks(self):
        for task in self.tasks:
            task.update_time()
        self.after(1000, self.update_clocks)

    def save_data(self):
        data_to_save = []
        for task in self.tasks:
            if task.is_running:
                task.update_time()
            data_to_save.append({
                "name": task.name,
                "elapsed": task.elapsed,
                "multiplier": task.multiplier.get()
            })
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f, ensure_ascii=False, indent=4)

    def load_data(self):
        if os.path.exists(DATA_FILE):
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                try:
                    saved_data = json.load(f)
                    for item in saved_data:
                        task = TaskFrame(self.scroll, self, item["name"], elapsed=item["elapsed"], multiplier=item.get("multiplier", "x1"))
                        task.pack(fill="x", pady=8)
                        self.tasks.append(task)
                except json.JSONDecodeError:
                    pass

    def archive_task(self, task):
        file_exists = os.path.exists(ARCHIVE_FILE)
        with open(ARCHIVE_FILE, "a", newline="", encoding="utf-8-sig") as csvfile:
            fieldnames = ["Tâche", "Date_Archivage", "Temps_Facturable", "Multiplicateur"]
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, delimiter=";")
            if not file_exists:
                writer.writeheader() 
            writer.writerow({
                "Tâche": task.name,
                "Date_Archivage": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "Temps_Facturable": task.get_formatted_time(),
                "Multiplicateur": task.multiplier.get()
            })
        self.tasks.remove(task)
        task.destroy()
        self.save_data()

    def _repack_tasks(self):
        for task in self.tasks:
            task.pack_forget()
        for task in self.tasks:
            task.pack(fill="x", pady=8)
        self.save_data()

    def open_folder(self):
        os.startfile(os.getcwd())

    def on_closing(self):
        self.save_data()
        self.destroy()

if __name__ == "__main__":
    ctk.set_appearance_mode("dark")
    app = App()
    app.mainloop()