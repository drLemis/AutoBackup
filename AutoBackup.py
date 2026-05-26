import os
import sys
import shutil
import time
import threading
import hashlib
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

try:
    import winreg
except ImportError:
    winreg = None  # non-Windows fallback

APP_VERSION = "1.0"

QUIET_SECONDS = 2.0
POLL_INTERVAL = 0.5
MAX_VERSIONS_PER_FILE = 5

HASH_EXT = ".hash"

HELP_TEXT = (
    "AutoBackup watches your work folder for any file changes.\n\n"
    "When a file finishes saving (no writes for 2 seconds and no app is holding it locked)\n"
    "a timestamped copy is placed in your backup folder, mirroring the original folder structure.\n\n"
    "Smart features:\n"
    "> Each save = one new versioned copy (e.g. MyFile_20250115_143022.psd)\n"
    "> Duplicate-skip: if the file's content hash is identical to the previous backup, no new backup is made.\n"
    f"> Auto-prune: keeps only the latest {MAX_VERSIONS_PER_FILE} versions per file.\n\n"
    "Press the START/STOP button to toggle watching.\n"
    "GRAY  = idle\n"
    "GREEN = actively watching\n"
    "ORANGE = busy copying a file\n\n"
    "(c) Lemis - 2026 - NWSL - FUCK ADOBE"
)

TS_FORMAT = "%Y%m%d_%H%M%S"
TS_LEN = 15

REG_PATH = r"Software\\Lemis\\AutoBackup"

def load_prefs():
    if not winreg:
        return "", ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            src, _ = winreg.QueryValueEx(key, "SourcePath")
            dst, _ = winreg.QueryValueEx(key, "BackupPath")
            return src, dst
    except FileNotFoundError:
        return "", ""
    except Exception:
        return "", ""

def save_prefs(src, dst):
    if not winreg:
        return
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            winreg.SetValueEx(key, "SourcePath", 0, winreg.REG_SZ, src or "")
            winreg.SetValueEx(key, "BackupPath", 0, winreg.REG_SZ, dst or "")
    except Exception as e:
        print(f"Save prefs failed: {e}")

def resource_path(relative):
    """Get path to resource, works for dev and for PyInstaller bundle."""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)

class ToolTip:
    def __init__(self, widget, text):
        self.widget = widget
        self.text = text
        self.tip = None
        widget.bind("<Enter>", self.show)
        widget.bind("<Leave>", self.hide)

    def show(self, _=None):
        if self.tip:
            return
        x = self.widget.winfo_rootx() + 25
        y = self.widget.winfo_rooty() + 25
        self.tip = tk.Toplevel(self.widget)
        self.tip.wm_overrideredirect(True)
        self.tip.wm_geometry(f"+{x}+{y}")
        lbl = tk.Label(
            self.tip, text=self.text, justify='left',
            background="#ffffe0", relief='solid', borderwidth=1,
            font=("Segoe UI", 9), padx=8, pady=6, wraplength=440
        )
        lbl.pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None

class BackupHandler(FileSystemEventHandler):
    def __init__(self, source_dir, backup_dir, log_callback, busy_callback):
        self.source_dir = Path(source_dir).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.log = log_callback
        self.set_busy = busy_callback
        self.pending = {}
        self.lock = threading.Lock()

    def _track(self, path):
        try:
            p = Path(path)
            if not p.is_file():
                return
            resolved = p.resolve()
            if self.backup_dir == resolved or self.backup_dir in resolved.parents:
                return
            with self.lock:
                self.pending[str(resolved)] = time.time()
        except Exception as e:
            self.log(f"[!] Track error: {e}")

    def on_modified(self, event):
        if not event.is_directory:
            self._track(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._track(event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._track(event.dest_path)

    def process_pending(self):
        now = time.time()
        ready = []
        with self.lock:
            for path, last_seen in list(self.pending.items()):
                if now - last_seen >= QUIET_SECONDS:
                    ready.append(path)
                    del self.pending[path]
        for path in ready:
            self._backup_file(path)

    @staticmethod
    def _quick_hash(path, chunk_size=1024 * 1024):
        h = hashlib.md5()
        size = os.path.getsize(path)
        h.update(str(size).encode())
        with open(path, 'rb') as f:
            h.update(f.read(chunk_size))
            if size > chunk_size * 2:
                f.seek(size // 2)
                h.update(f.read(chunk_size))
                f.seek(max(0, size - chunk_size))
                h.update(f.read(chunk_size))
        return h.hexdigest()

    @staticmethod
    def _make_backup_name(original_name, timestamp):
        stem, ext = os.path.splitext(original_name)
        return f"{stem}_{timestamp}{ext}"

    @staticmethod
    def _is_backup_of(filename, original_name):
        stem, ext = os.path.splitext(original_name)
        if not filename.endswith(ext):
            return False
        expected_prefix = stem + "_"
        if not filename.startswith(expected_prefix):
            return False
        middle = filename[len(expected_prefix):-len(ext)] if ext else filename[len(expected_prefix):]
        if len(middle) != TS_LEN:
            return False
        try:
            datetime.strptime(middle, TS_FORMAT)
            return True
        except ValueError:
            return False

    def _list_backups(self, backup_folder, original_name):
        if not backup_folder.exists():
            return []
        results = []
        for entry in os.listdir(backup_folder):
            full = backup_folder / entry
            if not full.is_file():
                continue
            if self._is_backup_of(entry, original_name):
                results.append(full)
        results.sort(key=lambda p: p.stat().st_mtime)
        return results

    def _last_backup_hash(self, backup_folder, original_name):
        backups = self._list_backups(backup_folder, original_name)
        if not backups:
            return None
        newest = backups[-1]
        hash_file = newest.with_suffix(newest.suffix + HASH_EXT)
        if hash_file.exists():
            try:
                return hash_file.read_text(encoding='utf-8').strip()
            except Exception:
                return None
        return None

    def _prune_old(self, backup_folder, original_name):
        backups = self._list_backups(backup_folder, original_name)
        excess = len(backups) - MAX_VERSIONS_PER_FILE
        if excess <= 0:
            return
        for old in backups[:excess]:
            try:
                old.unlink()
                hash_file = old.with_suffix(old.suffix + HASH_EXT)
                if hash_file.exists():
                    hash_file.unlink()
                self.log(f"[~] Pruned: {old.name}")
            except Exception as e:
                self.log(f"[!] Prune failed for {old.name}: {e}")

    def _backup_file(self, path):
        try:
            src = Path(path)
            if not src.exists():
                return

            for _ in range(20):
                try:
                    with open(src, 'rb'):
                        pass
                    break
                except (PermissionError, OSError):
                    time.sleep(0.5)
            else:
                self.log(f"[!] Still locked, will retry: {src.name}")
                with self.lock:
                    self.pending[str(src)] = time.time()
                return

            self.set_busy(True)

            try:
                rel = src.relative_to(self.source_dir)
            except ValueError:
                rel = Path(src.name)

            original_name = src.name
            backup_folder = self.backup_dir / rel.parent

            current_hash = self._quick_hash(src)
            last_hash = self._last_backup_hash(backup_folder, original_name)
            if current_hash == last_hash:
                self.log(f"[=] No change, skipped: {rel}")
                return

            timestamp = datetime.now().strftime(TS_FORMAT)
            backup_name = self._make_backup_name(original_name, timestamp)
            dest = backup_folder / backup_name
            dest.parent.mkdir(parents=True, exist_ok=True)

            t0 = time.time()
            shutil.copy2(src, dest)
            elapsed = time.time() - t0

            hash_file = dest.with_suffix(dest.suffix + HASH_EXT)
            try:
                hash_file.write_text(current_hash, encoding='utf-8')
            except Exception as e:
                self.log(f"[!] Hash sidecar failed: {e}")

            size_mb = dest.stat().st_size / 1048576
            self.log(f"[✓] {rel}  ({size_mb:.1f} MB in {elapsed:.1f}s)")

            self._prune_old(backup_folder, original_name)

        except Exception as e:
            self.log(f"[!] Backup failed for {path}: {e}")
        finally:
            self.set_busy(False)

class AutoBackupApp:
    COLOR_IDLE = "#9e9e9e"
    COLOR_WATCHING = "#43a047"
    COLOR_BUSY = "#fb8c00"

    def __init__(self, root):
        self.root = root
        self.root.title(f"AutoBackup v{APP_VERSION}")
        self.root.geometry("460x300")
        self.root.minsize(460, 300)

        # Set custom window icon
        try:
            icon_path = resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
        except Exception as e:
            print(f"Icon load failed: {e}")

        self.observer = None
        self.handler = None
        self.worker_thread = None
        self.running = False

        self._build_ui()

    def _build_ui(self):
        topbar = ttk.Frame(self.root)
        topbar.pack(fill='x', padx=8, pady=(2, 2))

        grid = ttk.Frame(self.root)
        grid.pack(fill='x', padx=8, pady=4)
        grid.columnconfigure(1, weight=1)
        
        saved_src, saved_dst = load_prefs()

        ttk.Label(grid, text="Work folder:").grid(row=0, column=0, sticky='w', padx=(0, 6), pady=3)
        self.src_var = tk.StringVar(value=saved_src)
        ttk.Entry(grid, textvariable=self.src_var).grid(row=0, column=1, sticky='ew', pady=3)
        ttk.Button(grid, text="Browse...", command=self._pick_src).grid(row=0, column=2, padx=4, pady=3)

        ttk.Label(grid, text="Backup folder:").grid(row=1, column=0, sticky='w', padx=(0, 6), pady=3)
        self.dst_var = tk.StringVar(value=saved_dst)
        ttk.Entry(grid, textvariable=self.dst_var).grid(row=1, column=1, sticky='ew', pady=3)
        ttk.Button(grid, text="Browse...", command=self._pick_dst).grid(row=1, column=2, padx=4, pady=3)

        self.run_btn = tk.Button(
            grid, text="START", command=self.toggle,
            bg=self.COLOR_IDLE, fg="white", activebackground=self.COLOR_IDLE,
            font=("Segoe UI", 10, "bold"), width=8,
            relief='flat', cursor='hand2', borderwidth=0
        )
        self.run_btn.grid(row=0, column=3, padx=(5, 0), pady=3, sticky='ns')

        help_frame = ttk.Frame(grid)
        help_frame.grid(row=1, column=3, padx=(5, 0), pady=(4, 0))
        self.help_lbl = tk.Label(
            help_frame, text="  ?  ",
            font=("Segoe UI", 10, "bold"),
            fg="white", bg="#1e88e5",
            cursor="question_arrow", padx=2
        )
        self.help_lbl.pack()
        ToolTip(self.help_lbl, HELP_TEXT)

        self.log_box = scrolledtext.ScrolledText(
            self.root, height=20, state='disabled', wrap='word',
            font=("Consolas", 9)
        )
        self.log_box.pack(fill='both', expand=True, padx=8, pady=(0, 8))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_button(self, color, text):
        self.run_btn.configure(bg=color, activebackground=color, text=text)

    def _set_busy(self, busy):
        if not self.running:
            return
        if busy:
            self.root.after(0, lambda: self._set_button(self.COLOR_BUSY, "BUSY..."))
        else:
            self.root.after(0, lambda: self._set_button(self.COLOR_WATCHING, "STOP"))

    def _pick_src(self):
        d = filedialog.askdirectory(title="Select work folder to watch")
        if d:
            self.src_var.set(d)

    def _pick_dst(self):
        d = filedialog.askdirectory(title="Select backup destination folder")
        if d:
            self.dst_var.set(d)

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.root.after(0, self._append_log, line)

    def _append_log(self, line):
        self.log_box.configure(state='normal')
        self.log_box.insert('end', line)
        self.log_box.see('end')
        self.log_box.configure(state='disabled')

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

    def start(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()

        if not src or not os.path.isdir(src):
            self.log("[!] Invalid work folder.")
            return
        if not dst:
            self.log("[!] Please choose a backup folder.")
            return

        os.makedirs(dst, exist_ok=True)

        if os.path.abspath(dst).startswith(os.path.abspath(src)):
            self.log("[!] Backup folder must NOT be inside the watched folder.")
            return

        save_prefs(src, dst)

        self.handler = BackupHandler(src, dst, self.log, self._set_busy)
        self.observer = Observer()
        self.observer.schedule(self.handler, src, recursive=True)
        self.observer.start()

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        self._set_button(self.COLOR_WATCHING, "STOP")
        self.log(f"[*] Watching: {src}")
        self.log(f"[*] Backups → {dst}")
        self.log(f"[*] Keeping {MAX_VERSIONS_PER_FILE} versions per file.")

    def _worker_loop(self):
        while self.running:
            try:
                if self.handler:
                    self.handler.process_pending()
            except Exception as e:
                self.log(f"[!] Worker error: {e}")
            time.sleep(POLL_INTERVAL)

    def stop(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=3)
            self.observer = None
        self.handler = None
        self._set_button(self.COLOR_IDLE, "START")
        self.log("[*] Stopped.")

    def _on_close(self):
        if self.running:
            self.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = AutoBackupApp(root)
    root.mainloop()