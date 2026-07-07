import ctypes
from ctypes import wintypes
import os
import sys
import shutil
import time
import threading
import hashlib
import webbrowser
import io
import json
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import platformdirs
from PIL import Image, ImageDraw
import pystray
import logging.handlers

from locale_util import init_locale, set_locale, current_lang, discover_langs, lang_label, t, help_text, is_rtl
from version_check import check_for_update

try:
    import winreg
except ImportError:
    winreg = None  # non-Windows fallback

# Shell_NotifyIconW constants and struct for silent balloon notifications
NIM_MODIFY = 1
NIF_INFO = 0x00000010
NIIF_NOSOUND = 0x00000010

class NOTIFYICONDATAW(ctypes.Structure):
    _fields_ = [
        ('cbSize', wintypes.DWORD),
        ('hWnd', wintypes.HWND),
        ('uID', wintypes.UINT),
        ('uFlags', wintypes.UINT),
        ('uCallbackMessage', wintypes.UINT),
        ('hIcon', wintypes.HICON),
        ('szTip', wintypes.WCHAR * 128),
        ('dwState', wintypes.DWORD),
        ('dwStateMask', wintypes.DWORD),
        ('szInfo', wintypes.WCHAR * 256),
        ('uVersion', wintypes.UINT),
        ('szInfoTitle', wintypes.WCHAR * 64),
        ('dwInfoFlags', wintypes.DWORD),
        ('guidItem', ctypes.c_byte * 16),
        ('hBalloonIcon', wintypes.HICON),
    ]

APP_VERSION = "1.3.0"

QUIET_SECONDS = 2.0
POLL_INTERVAL = 0.5
MAX_VERSIONS_PER_FILE = 5
MIN_VERSIONS = 1
MAX_VERSIONS_LIMIT = 100

HASH_EXT = ".hash"
FILE_ATTRIBUTE_HIDDEN = 0x02

TS_FORMAT = "%Y%m%d_%H%M%S"
TS_LEN = 15

REG_PATH = r"Software\\Lemis\\AutoBackup"
REG_RUN_PATH = r"Software\\Microsoft\\Windows\\CurrentVersion\\Run"

LOG_DIR = platformdirs.user_log_dir("AutoBackup", "Lemis")
LOG_FILE = Path(LOG_DIR) / "AutoBackup.log"
MIN_DISK_FREE_MB = 500

# --- File exclusion patterns ---
# Temp/lock files, caches, and OS junk that should never be backed up.
_EXCLUDED_EXTS = {
    ".tmp", ".temp", ".~", ".bak", ".swp", ".lock",
    ".part", ".crdownload", ".partial",
    ".crswap", ".psswap", ".wbk",
}
_EXCLUDED_NAMES = {
    "thumbs.db", ".ds_store", "desktop.ini", "ehthumbs.db",
    ".gitattributes", ".gitignore",
}
_EXCLUDED_DIRS = {
    ".git", "node_modules", "__pycache__", ".venv", "venv",
    ".mypy_cache", ".pytest_cache", ".tox", ".eggs", "build", "dist",
}


def is_inside(child, parent):
    child_path = Path(child).resolve()
    parent_path = Path(parent).resolve()
    return parent_path in child_path.parents or child_path == parent_path


def hide_file(path):
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.kernel32.SetFileAttributesW(str(path), FILE_ATTRIBUTE_HIDDEN)
    except Exception:
        pass


def load_prefs():
    if not winreg:
        return "", "", "", MAX_VERSIONS_PER_FILE, True
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            src, _ = winreg.QueryValueEx(key, "SourcePath")
            dst, _ = winreg.QueryValueEx(key, "BackupPath")
            try:
                lang, _ = winreg.QueryValueEx(key, "Language")
            except FileNotFoundError:
                lang = ""
            try:
                ver, _ = winreg.QueryValueEx(key, "MaxVersions")
                ver = max(MIN_VERSIONS, min(MAX_VERSIONS_LIMIT, int(ver)))
            except (FileNotFoundError, ValueError):
                ver = MAX_VERSIONS_PER_FILE
            try:
                sound, _ = winreg.QueryValueEx(key, "Sound")
                sound = int(sound) != 0
            except (FileNotFoundError, ValueError):
                sound = True
            return src, dst, lang, ver, sound
    except FileNotFoundError:
        return "", "", "", MAX_VERSIONS_PER_FILE, True
    except Exception:
        return "", "", "", MAX_VERSIONS_PER_FILE, True


def save_prefs(src, dst, lang=None, max_versions=None, sound=None):
    if not winreg:
        return
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            winreg.SetValueEx(key, "SourcePath", 0, winreg.REG_SZ, src or "")
            winreg.SetValueEx(key, "BackupPath", 0, winreg.REG_SZ, dst or "")
            if lang is not None:
                winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, lang)
            if max_versions is not None:
                winreg.SetValueEx(key, "MaxVersions", 0, winreg.REG_DWORD, int(max_versions))
            if sound is not None:
                winreg.SetValueEx(key, "Sound", 0, winreg.REG_DWORD, 1 if sound else 0)
    except Exception as e:
        print(f"Save prefs failed: {e}")


def resource_path(relative):
    """Get path to resource, works for dev and for PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative)
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), relative)


def set_startup(enabled):
    """Add/remove AutoBackup from Windows startup via registry Run key."""
    if not winreg:
        return
    try:
        if enabled:
            exe_path = sys.executable if getattr(sys, "frozen", False) else sys.argv[0]
            cmd = f'"{exe_path}"'
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_WRITE) as key:
                winreg.SetValueEx(key, "AutoBackup", 0, winreg.REG_SZ, cmd)
        else:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH, 0, winreg.KEY_WRITE) as key:
                try:
                    winreg.DeleteValue(key, "AutoBackup")
                except FileNotFoundError:
                    pass
    except Exception as e:
        print(f"Startup registry failed: {e}")
def is_startup_enabled():
    """Check if AutoBackup is set to start with Windows."""
    if not winreg:
        return False
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_RUN_PATH) as key:
            winreg.QueryValueEx(key, "AutoBackup")
            return True
    except FileNotFoundError:
        return False
    except Exception:
        return False



def format_size(size_bytes):
    """Human-readable file size."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    if size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    if size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def folder_size(path):
    """Total size of a folder (best-effort, skips errors)."""
    total = 0
    try:
        for dirpath, _, filenames in os.walk(path):
            for name in filenames:
                try:
                    total += os.path.getsize(os.path.join(dirpath, name))
                except OSError:
                    pass
    except Exception:
        pass
    return total


def _setup_file_log():
    """Set up rotating file logging to a platform-appropriate directory."""
    os.makedirs(LOG_DIR, exist_ok=True)
    handler = logging.handlers.RotatingFileHandler(
        LOG_FILE, maxBytes=1024 * 1024, backupCount=2, encoding="utf-8",
    )
    handler.setFormatter(logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S",
    ))
    logger = logging.getLogger("AutoBackup")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger


file_logger = _setup_file_log()


def log_info(msg):
    file_logger.info(msg)


def log_warning(msg):
    file_logger.warning(msg)


def log_error(msg):
    file_logger.error(msg)


_TRAY_COLORS = {
    "watching": "#43a047",
    "paused": "#1e88e5",
    "stopped": "#9e9e9e",
    "busy": "#fb8c00",
    "error": "#e53935",
}


def _tray_image(color_hex: str) -> Image.Image:
    """Create a 16x16 colored circle for the tray icon."""
    img = Image.new("RGBA", (16, 16), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([1, 1, 14, 14], fill=color_hex)
    # subtle white ring for visibility
    draw.ellipse([1, 1, 14, 14], outline="#ffffff", width=1)
    return img


def center_window(win, parent=None):
    """Center a tkinter window on its parent (or on screen if no parent)."""
    win.update_idletasks()
    if parent:
        px = parent.winfo_x()
        py = parent.winfo_y()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
    else:
        px = py = 0
        pw = win.winfo_screenwidth()
        ph = win.winfo_screenheight()
    ww = win.winfo_reqwidth()
    wh = win.winfo_reqheight()
    x = px + (pw - ww) // 2
    y = py + (ph - wh) // 2
    win.geometry(f"+{max(0, x)}+{max(0, y)}")


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
            self.tip, text=self.text, justify="left",
            background="#ffffe0", relief="solid", borderwidth=1,
            font=("Segoe UI", 9), padx=8, pady=6, wraplength=440,
        )
        lbl.pack()

    def hide(self, _=None):
        if self.tip:
            self.tip.destroy()
            self.tip = None


class BackupHandler(FileSystemEventHandler):
    def __init__(self, source_dir, backup_dir, log_callback, busy_callback, max_versions=MAX_VERSIONS_PER_FILE, notify_callback=None):
        self.source_dir = Path(source_dir).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.log = log_callback
        self.set_busy = busy_callback
        self.notify = notify_callback
        self.max_versions = max_versions
        self.pending = {}
        self.lock = threading.Lock()
        self.baseline = {}

    @staticmethod
    def _fingerprint(path):
        stat = path.stat()
        return (stat.st_size, stat.st_mtime_ns)

    @staticmethod
    def _is_excluded(path):
        """Return True if a file or directory should be skipped."""
        name = path.name.lower()
        if name in _EXCLUDED_NAMES:
            return True
        if path.is_file():
            ext = path.suffix.lower()
            if ext in _EXCLUDED_EXTS:
                return True
            if name.endswith("~") or name.startswith("~$"):
                return True
            # Adobe temp naming: ~pramXXXX.tmp
            if name.startswith("~") and ext in (".tmp", ".temp"):
                return True
        return False

    @staticmethod
    def _is_excluded_dir(path):
        """Return True if a directory and its contents should be skipped."""
        return path.name.lower() in _EXCLUDED_DIRS

    def _iter_source_files(self):
        for dirpath, dirnames, filenames in os.walk(self.source_dir):
            # Prune excluded directories in-place so os.walk doesn't descend
            dirnames[:] = [d for d in dirnames if d.lower() not in _EXCLUDED_DIRS]
            for name in filenames:
                p = Path(dirpath) / name
                if self._is_excluded(p):
                    continue
                yield p

    def build_baseline(self):
        """Snapshot existing files so only post-start changes are backed up."""
        self.baseline = {}
        count = 0
        for path in self._iter_source_files():
            try:
                resolved = path.resolve()
                if self.backup_dir == resolved or self.backup_dir in resolved.parents:
                    continue
                self.baseline[str(resolved)] = self._fingerprint(resolved)
                count += 1
            except OSError:
                pass
        self.log("log.baseline_done", count=count)

    def _track(self, path):
        try:
            p = Path(path)
            if not p.is_file():
                return
            if self._is_excluded(p):
                return
            resolved = p.resolve()
            if self.backup_dir == resolved or self.backup_dir in resolved.parents:
                return
            with self.lock:
                self.pending[str(resolved)] = time.time()
        except Exception as e:
            self.log("log.track_error", error=e)

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
        with open(path, "rb") as f:
            if size <= chunk_size * 3:
                # Small file: hash it entirely - faster than 3 partial reads
                h.update(f.read())
            else:
                h.update(f.read(chunk_size))
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
                return hash_file.read_text(encoding="utf-8").strip()
            except Exception:
                return None
        return None

    def _prune_old(self, backup_folder, original_name):
        backups = self._list_backups(backup_folder, original_name)
        excess = len(backups) - self.max_versions
        if excess <= 0:
            return
        for old in backups[:excess]:
            try:
                old.unlink()
                hash_file = old.with_suffix(old.suffix + HASH_EXT)
                if hash_file.exists():
                    hash_file.unlink()
                self.log("log.pruned", name=old.name)
            except Exception as e:
                self.log("log.prune_failed", name=old.name, error=e)

    def _backup_file(self, path):
        try:
            src = Path(path)
            if not src.exists():
                return

            for _ in range(20):
                try:
                    with open(src, "rb"):
                        pass
                    break
                except (PermissionError, OSError):
                    time.sleep(0.5)
            else:
                self.log("log.still_locked", name=src.name)
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

            key = str(src.resolve())
            fp = self._fingerprint(src)
            if key in self.baseline and fp == self.baseline[key]:
                return

            current_hash = self._quick_hash(src)
            last_hash = self._last_backup_hash(backup_folder, original_name)
            if current_hash == last_hash:
                self.baseline[key] = fp
                self.log("log.skipped_unchanged", path=str(rel))
                return

            # --- Disk space check ---
            try:
                usage = shutil.disk_usage(backup_folder)
                free_mb = usage.free / (1024 * 1024)
                if free_mb < MIN_DISK_FREE_MB:
                    log_warning(f"Low disk space on backup drive: {free_mb:.0f} MB free")
                    self.log("log.disk_low", free_mb=int(free_mb))
                    return
            except OSError:
                pass

            # --- Size drop detection ---
            existing = self._list_backups(backup_folder, original_name)
            if existing:
                prev_size = existing[-1].stat().st_size
                src_size = src.stat().st_size
                if src_size > 0 and prev_size > 0 and src_size < prev_size * 0.5:
                    log_warning(f"Size drop detected: {original_name} went from {prev_size} to {src_size} bytes")
                    self.log("log.size_drop", name=original_name, old_size=format_size(prev_size), new_size=format_size(src_size))

            timestamp = datetime.now().strftime(TS_FORMAT)
            backup_name = self._make_backup_name(original_name, timestamp)
            dest = backup_folder / backup_name
            dest.parent.mkdir(parents=True, exist_ok=True)

            t0 = time.time()
            shutil.copy2(src, dest)
            elapsed = time.time() - t0

            # --- Backup validation ---
            try:
                dest_hash = self._quick_hash(dest)
                if dest_hash != current_hash:
                    log_warning(f"Backup validation failed for {dest.name}, retrying...")
                    time.sleep(0.5)
                    if dest.exists():
                        dest.unlink()
                    shutil.copy2(src, dest)
                    dest_hash = self._quick_hash(dest)
                    if dest_hash != current_hash:
                        log_error(f"Backup validation failed after retry for {dest.name}")
                        self.log("log.validation_failed", path=str(rel))
                        if dest.exists():
                            dest.unlink()
                        return
            except Exception as e:
                log_error(f"Validation error for {dest.name}: {e}")
                self.log("log.validation_failed", path=str(rel))
                if dest.exists():
                    dest.unlink()
                return

            hash_file = dest.with_suffix(dest.suffix + HASH_EXT)
            try:
                hash_file.write_text(current_hash, encoding="utf-8")
                hide_file(hash_file)
            except Exception as e:
                self.log("log.sidecar_failed", error=e)

            size_mb = dest.stat().st_size / 1048576
            self.log(
                "log.saved",
                path=str(rel),
                size_mb=size_mb,
                seconds=elapsed,
            )

            self.baseline[key] = fp
            self._prune_old(backup_folder, original_name)

            if self.notify:
                self.notify(str(rel))

        except Exception as e:
            log_error(f"Backup failed for {path}: {e}")
            self.log("log.backup_failed", path=path, error=e)
        finally:
            self.set_busy(False)


class AutoBackupApp:
    COLOR_IDLE = "#9e9e9e"
    COLOR_WATCHING = "#43a047"
    COLOR_BUSY = "#fb8c00"
    COLOR_PAUSED = "#1e88e5"
    COLOR_UPDATE_PATCH = "#5c6bc0"
    COLOR_UPDATE_MAJOR = "#e53935"
    COLOR_UPDATE_MAJOR_ALT = "#ff7043"

    def __init__(self, root):
        self.root = root
        self.root.title(f"{t('app.title')} v{APP_VERSION}")
        self.root.geometry("520x440")
        self.root.minsize(520, 440)

        log_info(f"AutoBackup v{APP_VERSION} starting")

        try:
            icon_path = resource_path("icon.ico")
            if os.path.exists(icon_path):
                self.root.iconbitmap(default=icon_path)
        except Exception as e:
            log_error(f"Icon load failed: {e}")

        self.observer = None
        self.handler = None
        self.worker_thread = None
        self.running = False
        self.paused = False
        self._busy = False
        self._status_key = "status.stopped"
        self._help_tooltip = None
        self._update_info = None
        self._size_job = None
        self._tray_icon = None
        self._observer_retries = 0
        self._disk_low = False
        self._last_good_backups = {}

        # Load persisted preferences (needed before UI build)
        _prefs = load_prefs()
        self._saved_src = _prefs[0]
        self._saved_dst = _prefs[1]
        self._saved_ver = _prefs[3]
        self._saved_sound = _prefs[4]

        self.sound_var = tk.BooleanVar(value=self._saved_sound)
        self.startup_var = tk.BooleanVar(value=is_startup_enabled())
        self._log_entries = []

        self._build_ui()
        self.root.after(0, self._apply_rtl)
        self._set_status("status.stopped")

        # Check for first run
        self._first_run = self._check_first_run()
        if self._first_run:
            self.root.after(100, self._show_wizard)

        threading.Thread(target=self._check_update_thread, daemon=True).start()
        self._setup_tray()

        # Auto-start watching if folders are already configured
        self.root.after(300, self._try_auto_start)

    def _try_auto_start(self):
        """Auto-start watching on launch if both folders are configured and valid."""
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()
        if src and dst and os.path.isdir(src) and os.path.isdir(dst):
            if not is_inside(dst, src):
                self.start()

    def _build_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=4, pady=4)

        # ========== TAB 1: Backup ==========
        backup_tab = ttk.Frame(self.notebook)
        self.notebook.add(backup_tab, text=t("tab.backup"))

        grid = ttk.Frame(backup_tab)
        grid.pack(fill="x", padx=8, pady=(8, 4))
        grid.columnconfigure(1, weight=1)

        self.lbl_work = ttk.Label(grid, text=t("label.work_folder"))
        self.lbl_work.grid(row=0, column=0, sticky="w", padx=(0, 6), pady=3)
        self.src_var = tk.StringVar(value=self._saved_src)
        self.entry_src = ttk.Entry(grid, textvariable=self.src_var)
        self.entry_src.grid(row=0, column=1, sticky="ew", pady=3)
        self.btn_browse_src = ttk.Button(grid, text=t("btn.browse"), command=self._pick_src)
        self.btn_browse_src.grid(row=0, column=2, padx=4, pady=3)

        self.lbl_backup = ttk.Label(grid, text=t("label.backup_folder"))
        self.lbl_backup.grid(row=1, column=0, sticky="w", padx=(0, 6), pady=3)
        self.dst_var = tk.StringVar(value=self._saved_dst)
        self.entry_dst = ttk.Entry(grid, textvariable=self.dst_var)
        self.entry_dst.grid(row=1, column=1, sticky="ew", pady=3)
        self.btn_browse_dst = ttk.Button(grid, text=t("btn.browse"), command=self._pick_dst)
        self.btn_browse_dst.grid(row=1, column=2, padx=4, pady=3)

        # --- Versions + size row ---
        self.lbl_versions = ttk.Label(grid, text=t("label.versions"))
        self.lbl_versions.grid(row=2, column=0, sticky="w", padx=(0, 6), pady=3)
        self.versions_var = tk.IntVar(value=self._saved_ver)
        self.versions_spin = ttk.Spinbox(
            grid, from_=MIN_VERSIONS, to=MAX_VERSIONS_LIMIT,
            textvariable=self.versions_var, width=5, justify="center",
        )
        self.versions_spin.grid(row=2, column=1, sticky="w", pady=3)
        self.size_var = tk.StringVar(value="")
        self.size_lbl = ttk.Label(grid, textvariable=self.size_var, font=("Segoe UI", 9, "italic"))
        self.size_lbl.grid(row=2, column=1, sticky="e", pady=3, padx=(0, 10))

        # --- START / PAUSE / RESUME button ---
        btn_row = ttk.Frame(backup_tab)
        btn_row.pack(fill="x", padx=8, pady=6)
        self.run_btn = tk.Button(
            btn_row, text=t("btn.start"), command=self.toggle,
            bg=self.COLOR_IDLE, fg="white", activebackground=self.COLOR_IDLE,
            font=("Segoe UI", 11, "bold"), width=14, height=1,
            relief="flat", cursor="hand2", borderwidth=0,
        )
        self.run_btn.pack()

        # --- Status indicator ---
        status_frame = ttk.Frame(backup_tab)
        status_frame.pack(fill="x", padx=8, pady=(4, 2))
        self.status_indicator = tk.Canvas(
            status_frame, width=18, height=18, highlightthickness=0,
        )
        self.status_indicator.pack(side="left", padx=(0, 6))
        self._indicator_dot = self.status_indicator.create_oval(
            1, 1, 17, 17, fill=self.COLOR_IDLE, outline="",
        )
        self.status_var = tk.StringVar()
        self.status_lbl = ttk.Label(
            status_frame, textvariable=self.status_var,
            font=("Segoe UI", 9), wraplength=460,
        )
        self.status_lbl.pack(side="left", fill="x", expand=True)

        # Help button
        self.help_lbl = tk.Label(
            status_frame, text="  ?  ",
            font=("Segoe UI", 10, "bold"),
            fg="white", bg="#1e88e5",
            cursor="question_arrow", padx=2,
        )
        self.help_lbl.pack(side="right", padx=(6, 0))
        self._help_tooltip = ToolTip(self.help_lbl, help_text(self.versions_var.get()))

        # Update button (hidden until an update is found)
        self.update_btn = tk.Button(
            status_frame, command=self._open_release,
            fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", borderwidth=0, padx=8, pady=2,
        )

        # --- Log ---
        self.log_box = scrolledtext.ScrolledText(
            backup_tab, height=16, state="disabled", wrap="word",
            font=("Segoe UI", 9),
        )
        self.log_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))
        self.log_box.bind("<Button-3>", self._on_log_right_click)

        # ========== TAB 2: Restore ==========
        restore_tab = ttk.Frame(self.notebook)
        self.notebook.add(restore_tab, text=t("tab.restore"))

        restore_top = ttk.Frame(restore_tab)
        restore_top.pack(fill="x", padx=8, pady=(8, 0))
        self.restore_search_var = tk.StringVar()
        self.restore_search_var.trace_add("write", lambda *_: self._restore_refresh())
        self.lbl_restore_search = ttk.Label(restore_top, text=t("restore.search"))
        self.lbl_restore_search.pack(side="left")
        self.entry_search = ttk.Entry(restore_top, textvariable=self.restore_search_var)
        self.entry_search.pack(side="left", fill="x", expand=True, padx=(4, 0))

        list_frame = ttk.Frame(restore_tab)
        list_frame.pack(fill="both", expand=True, padx=8, pady=4)
        cols = ("name", "date", "size")
        self.restore_tree = ttk.Treeview(
            list_frame, columns=cols, show="headings", selectmode="browse",
        )
        self.restore_tree.heading("name", text=t("restore.col_name"))
        self.restore_tree.heading("date", text=t("restore.col_date"))
        self.restore_tree.heading("size", text=t("restore.col_size"))
        self.restore_tree.column("name", width=200)
        self.restore_tree.column("date", width=130)
        self.restore_tree.column("size", width=80, anchor="e")
        self.restore_vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.restore_tree.yview)
        self.restore_tree.configure(yscrollcommand=self.restore_vsb.set)
        self.restore_tree.pack(side="left", fill="both", expand=True)
        self.restore_vsb.pack(side="right", fill="y")
        self.restore_tree.bind("<Double-1>", lambda e: self._restore_open())

        self.restore_status_var = tk.StringVar(value=t("restore.no_backup"))
        self.restore_status_lbl = ttk.Label(
            restore_tab, textvariable=self.restore_status_var,
            font=("Segoe UI", 9), foreground="#999",
        )
        self.restore_status_lbl.pack(anchor="w", padx=8, pady=(0, 4))

        self.restore_actions = ttk.Frame(restore_tab)
        self.restore_actions.pack(fill="x", padx=8, pady=(0, 8))
        self.btn_restore_open = ttk.Button(
            self.restore_actions, text=t("restore.open"), command=self._restore_open,
        )
        self.btn_restore_open.pack(side="left")
        self.btn_restore_restore = ttk.Button(
            self.restore_actions, text=t("restore.restore"), command=self._restore_restore,
        )
        self.btn_restore_restore.pack(side="left", padx=(4, 0))
        self.btn_restore_export = ttk.Button(
            self.restore_actions, text=t("restore.export"), command=self._restore_export,
        )
        self.btn_restore_export.pack(side="left", padx=(4, 0))
        self.btn_open_backups = ttk.Button(
            self.restore_actions, text=t("btn.open_backups"), command=self._open_backups,
        )
        self.btn_open_backups.pack(side="right")
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)

        # ========== TAB 3: Settings ==========
        settings_tab = ttk.Frame(self.notebook)
        self.notebook.add(settings_tab, text=t("tab.settings"))

        settings_inner = ttk.Frame(settings_tab, padding=16)
        settings_inner.pack(fill="both", expand=True)

        # Sound
        self.chk_sound = ttk.Checkbutton(
            settings_inner, text=t("chk.sound"), variable=self.sound_var,
            command=self._on_sound_toggled,
        )
        self.chk_sound.pack(anchor="w", pady=4)

        # Startup
        self.chk_startup = ttk.Checkbutton(
            settings_inner, text=t("chk.startup"), variable=self.startup_var,
            command=self._on_startup_toggled,
        )
        self.chk_startup.pack(anchor="w", pady=4)

        # Language
        self.lang_row = ttk.Frame(settings_inner)
        self.lang_row.pack(anchor="w", pady=4)
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(
            self.lang_row, textvariable=self.lang_var,
            state="readonly", width=14,
        )
        self.lang_combo.pack(side="left")
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_selected)
        self._label_to_code = {}
        self._reload_lang_choices()

        # Reset wizard
        self.btn_reset_wizard = ttk.Button(
            settings_inner, text=t("settings.reset_wizard"),
            command=self._reset_wizard,
        )
        self.btn_reset_wizard.pack(anchor="w", pady=(8, 0))

        # Version
        self.ver_lbl = ttk.Label(
            settings_inner, text=f"v{APP_VERSION}",
            font=("Segoe UI", 9), foreground="#999",
        )
        self.ver_lbl.pack(anchor="sw", pady=(8, 0))

        ttk.Label(settings_inner, text="", font=("Segoe UI", 9)).pack(fill="both", expand=True)
        self.copyright_lbl = ttk.Label(
            settings_inner, text=t("help.copyright"),
            font=("Segoe UI", 8), foreground="#bbb",
        )
        self.copyright_lbl.pack(anchor="sw")

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.bind("<Unmap>", self._on_minimize)

    def _set_indicator(self, color):
        try:
            self.status_indicator.itemconfig(self._indicator_dot, fill=color)
        except Exception:
            pass

    def _set_status(self, key):
        self._status_key = key
        self.status_var.set(t(key))
        if key == "status.watching":
            self._set_indicator(self.COLOR_WATCHING)
        elif key == "status.paused":
            self._set_indicator(self.COLOR_PAUSED)
        elif key == "status.stopped":
            self._set_indicator(self.COLOR_IDLE)
        elif key == "status.copying":
            self._set_indicator(self.COLOR_BUSY)
        elif key == "status.disk_low":
            self._set_indicator(self.COLOR_UPDATE_MAJOR)
        elif key == "status.error":
            self._set_indicator(self.COLOR_UPDATE_MAJOR)
        else:
            self._set_indicator(self.COLOR_IDLE)

    def _reload_lang_choices(self):
        codes = discover_langs()
        labels = [lang_label(c) for c in codes]
        self.lang_combo["values"] = labels
        self._label_to_code = {lang_label(c): c for c in codes}
        self.lang_var.set(lang_label(current_lang()))

    def _on_lang_selected(self, _event=None):
        code = self._label_to_code.get(self.lang_var.get())
        if code:
            self._set_lang(code)

    def _set_lang(self, lang):
        if lang == current_lang():
            return
        set_locale(lang)
        save_prefs(self.src_var.get().strip(), self.dst_var.get().strip(), lang, self.versions_var.get())
        self._refresh_ui()

    def _sync_lang_dropdown(self):
        self.lang_var.set(lang_label(current_lang()))

    def _ask_yes_no(self, title, message):
        """Custom yes/no dialog with localized buttons."""
        dlg = tk.Toplevel(self.root)
        dlg.title(title)
        dlg.transient(self.root)
        dlg.grab_set()
        dlg.resizable(False, False)
        ttk.Label(dlg, text=message, wraplength=350, padding=20).pack()
        btn_frame = ttk.Frame(dlg)
        btn_frame.pack(pady=(0, 12))
        result = [False]
        def yes():
            result[0] = True
            dlg.destroy()
        def no():
            dlg.destroy()
        ttk.Button(btn_frame, text=t("dialog.yes"), command=yes).pack(side="left", padx=4)
        ttk.Button(btn_frame, text=t("dialog.no"), command=no).pack(side="left", padx=4)
        center_window(dlg, self.root)
        dlg.wait_window()
        return result[0]

    def _play_sound(self, path):
        """Play a WAV file - platform-independent dispatch."""
        try:
            if sys.platform == "win32":
                alias = "_ab_chime"
                winmm = ctypes.windll.winmm
                winmm.mciSendStringW(f'close {alias}', None, 0, None)
                winmm.mciSendStringW(f'open "{path}" alias {alias}', None, 0, None)
                winmm.mciSendStringW(f'setaudio {alias} volume to 500', None, 0, None)
                winmm.mciSendStringW(f'play {alias}', None, 0, None)
            elif sys.platform == "darwin":
                import subprocess
                subprocess.Popen(["afplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            else:
                import subprocess
                for player in ("paplay", "aplay", "ffplay"):
                    try:
                        subprocess.Popen([player, path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        break
                    except FileNotFoundError:
                        continue
        except Exception:
            pass

    def _refresh_ui(self):
        self.root.title(f"{t('app.title')} v{APP_VERSION}")
        self.notebook.tab(0, text=t("tab.backup"))
        self.notebook.tab(1, text=t("tab.restore"))
        self.notebook.tab(2, text=t("tab.settings"))
        self.lbl_work.config(text=t("label.work_folder"))
        self.lbl_backup.config(text=t("label.backup_folder"))
        self.btn_browse_src.config(text=t("btn.browse"))
        self.btn_browse_dst.config(text=t("btn.browse"))
        self.btn_open_backups.config(text=t("btn.open_backups"))
        self.btn_restore_open.config(text=t("restore.open"))
        self.btn_restore_restore.config(text=t("restore.restore"))
        self.btn_restore_export.config(text=t("restore.export"))
        self.chk_sound.config(text=t("chk.sound"))
        self.chk_startup.config(text=t("chk.startup"))
        self.btn_reset_wizard.config(text=t("settings.reset_wizard"))
        self.lbl_versions.config(text=t("label.versions"))
        self.lbl_restore_search.config(text=t("restore.search"))
        self.restore_tree.heading("name", text=t("restore.col_name"))
        self.restore_tree.heading("date", text=t("restore.col_date"))
        self.restore_tree.heading("size", text=t("restore.col_size"))
        self._restore_refresh()
        self._replay_log()
        if self.running:
            if self._busy:
                self._set_button(self.COLOR_BUSY, "btn.busy")
                self.status_var.set(t("status.copying"))
            elif self.paused:
                self._set_button(self.COLOR_PAUSED, "btn.resume")
                self.status_var.set(t("status.paused"))
            else:
                self._set_button(self.COLOR_WATCHING, "btn.pause")
                self.status_var.set(t(self._status_key))
        else:
            self._set_button(self.COLOR_IDLE, "btn.start")
            self.status_var.set(t(self._status_key))
        if self._help_tooltip:
            self._help_tooltip.text = help_text(self.versions_var.get())
        self._sync_lang_dropdown()
        self._refresh_update_button()
        self._update_tray()
        self._apply_rtl()

    def _apply_rtl(self):
        rtl = is_rtl()
        a = "e" if rtl else "w"
        j = "right" if rtl else "left"
        # Grid columns: swap label ↔ browse button
        lbl_col, btn_col = (2, 0) if rtl else (0, 2)
        self.lbl_work.grid_configure(column=lbl_col, sticky=a)
        self.btn_browse_src.grid_configure(column=btn_col)
        self.lbl_backup.grid_configure(column=lbl_col, sticky=a)
        self.btn_browse_dst.grid_configure(column=btn_col)
        self.lbl_versions.grid_configure(column=lbl_col, sticky=a)
        # Packed widgets
        self.lbl_restore_search.pack_configure(side="right" if rtl else "left")
        self.entry_search.pack_configure(side="right" if rtl else "left", fill="x", expand=True, padx=(4, 0))
        self.restore_status_lbl.pack_configure(anchor=a, padx=8, pady=(0, 4))
        self.chk_sound.pack_configure(anchor=a, pady=4)
        self.chk_startup.pack_configure(anchor=a, pady=4)
        self.lang_row.pack_configure(anchor=a, pady=4)
        self.lang_combo.pack_configure(side="right" if rtl else "left")
        self.btn_reset_wizard.pack_configure(anchor=a, pady=(8, 0))
        self.ver_lbl.pack_configure(anchor="s" + a, pady=(8, 0))
        self.copyright_lbl.pack_configure(anchor="s" + a)
        self.status_indicator.pack_configure(side="right" if rtl else "left", padx=(6 if rtl else 0, 0 if rtl else 6))
        self.status_lbl.pack_configure(side="right" if rtl else "left", fill="x", expand=True)
        self.help_lbl.pack_configure(side="left" if rtl else "right", padx=(0 if rtl else 6, 6 if rtl else 0))
        self.update_btn.pack_configure(side="left" if rtl else "right", padx=(0 if rtl else 0, 6 if rtl else 0))
        # Entries: text justification
        self.entry_src.configure(justify=j)
        self.entry_dst.configure(justify=j)
        self.entry_search.configure(justify=j)
        self.status_lbl.configure(justify=j)
        # Treeview: column anchors + scrollbar side
        self.restore_tree.column("name", anchor=a)
        self.restore_tree.column("date", anchor=a)
        self.restore_tree.pack_forget()
        self.restore_vsb.pack_forget()
        side_tree = "right" if rtl else "left"
        side_vsb = "left" if rtl else "right"
        self.restore_tree.pack(side=side_tree, fill="both", expand=True)
        self.restore_vsb.pack(side=side_vsb, fill="y")
        # Restore action buttons: flip sides
        for btn in (self.btn_restore_open, self.btn_restore_restore, self.btn_restore_export):
            btn.pack_forget()
            btn.pack(side=side_tree, padx=(0 if btn == self.btn_restore_open else 4, 0))
        self.btn_open_backups.pack_forget()
        self.btn_open_backups.pack(side="left" if rtl else "right")
        # Notebook tabs on right side for RTL (some themes don't support -tabposition)
        try:
            self.notebook.configure(tabposition="en" if rtl else "nw")
        except tk.TclError:
            pass
        # Log: right-justify via tag (direction via Tcl causes click/select flicker)
        self.log_box.tag_remove("rtl", "1.0", "end")
        if rtl:
            self.log_box.tag_configure("rtl", justify="right")
            self.log_box.tag_add("rtl", "1.0", "end")

    def _check_update_thread(self):
        info = check_for_update(APP_VERSION)
        if info:
            self.root.after(0, lambda i=info: self._show_update_button(i))
    def _show_update_button(self, info):
        self._update_info = info
        if not self.update_btn.winfo_ismapped():
            self.update_btn.pack(side="left" if is_rtl() else "right", padx=(0, 6))
        self._refresh_update_button()

    def _refresh_update_button(self):
        if not self._update_info:
            return
        info = self._update_info
        if info["level"] == "major":
            self.update_btn.configure(
                text=t("btn.update_major", version=info["version"]),
                bg=self.COLOR_UPDATE_MAJOR,
                activebackground=self.COLOR_UPDATE_MAJOR,
            )
        else:
            self.update_btn.configure(
                text=t("btn.update_patch", version=info["version"]),
                bg=self.COLOR_UPDATE_PATCH,
                activebackground=self.COLOR_UPDATE_PATCH,
            )

    def _open_release(self):
        if self._update_info:
            webbrowser.open(self._update_info["url"])

    def _set_button(self, color, text_key):
        self.run_btn.configure(bg=color, activebackground=color, text=t(text_key))

    def _set_busy(self, busy):
        if not self.running:
            return
        self._busy = busy
        if busy:
            self.root.after(0, lambda: self._set_button(self.COLOR_BUSY, "btn.busy"))
            self.root.after(0, lambda: self._set_status("status.copying"))
        else:
            self.root.after(0, lambda: self._set_button(self.COLOR_WATCHING, "btn.pause"))
            if not self._disk_low:
                self.root.after(0, lambda: self._set_status("status.watching"))

    def _pick_src(self):
        d = filedialog.askdirectory(title=t("dialog.pick_work"))
        if d:
            self.src_var.set(d)

    def _pick_dst(self):
        d = filedialog.askdirectory(title=t("dialog.pick_backup"))
        if d:
            self.dst_var.set(d)

    def _open_backups(self):
        dst = self.dst_var.get().strip()
        if not dst:
            messagebox.showinfo(
                t("dialog.no_backup_title"),
                t("dialog.no_backup_body"),
            )
            return
        if not os.path.isdir(dst):
            messagebox.showinfo(
                t("dialog.no_backup_title"),
                t("dialog.no_backup_body"),
            )
            return
        if sys.platform == "win32":
            os.startfile(dst)
        else:
            import subprocess
            subprocess.Popen(["xdg-open", dst])

    def log(self, key, **kwargs):
        """Log a translatable message. key is a localization key, kwargs are template params."""
        ts = datetime.now()
        self._log_entries.append((ts, key, kwargs))
        msg = t(key, **kwargs)
        ts_str = ts.strftime('%H:%M:%S')
        line = f"{msg} [{ts_str}]\n" if is_rtl() else f"[{ts_str}] {msg}\n"
        self.root.after(0, self._append_log, line)

    def _append_log(self, line):
        self.log_box.configure(state="normal")
        pos = self.log_box.index("end-1c")
        self.log_box.insert("end", line)
        if is_rtl():
            self.log_box.tag_add("rtl", pos, "end-1c")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def _replay_log(self):
        """Re-render all log entries in the current language."""
        self.log_box.configure(state="normal")
        self.log_box.delete("1.0", "end")
        self.log_box.configure(state="disabled")
        for ts, key, kwargs in self._log_entries:
            msg = t(key, **kwargs)
            ts_str = ts.strftime('%H:%M:%S')
            line = f"{msg} [{ts_str}]\n" if is_rtl() else f"[{ts_str}] {msg}\n"
            self._append_log(line)

    def toggle(self):
        if not self.running:
            self.start()
        elif self.paused:
            self.resume()
        else:
            self.pause()

    def pause(self):
        """Stop watching but keep handler/baseline in memory."""
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=3)
            self.observer = None
        self.paused = True
        self._set_button(self.COLOR_PAUSED, "btn.resume")
        self._set_status("status.paused")
        self.log("log.paused")
        self._update_tray()

    def resume(self):
        """Re-start the observer without re-scanning."""
        if not self.handler:
            self.start()
            return
        self.observer = Observer()
        self.observer.schedule(self.handler, self.src_var.get().strip(), recursive=True)
        self.observer.start()
        self.paused = False
        self._set_button(self.COLOR_WATCHING, "btn.pause")
        self._set_status("status.watching")
        self.log("log.resumed")
        self._update_tray()

    def start(self):
        src = self.src_var.get().strip()
        dst = self.dst_var.get().strip()

        if not src or not os.path.isdir(src):
            messagebox.showerror(t("dialog.error_title"), t("dialog.invalid_work"))
            return
        if not dst:
            messagebox.showerror(t("dialog.error_title"), t("dialog.missing_backup"))
            return

        dst_path = Path(dst)
        if not dst_path.is_dir():
            if dst_path.exists():
                messagebox.showerror(t("dialog.error_title"), t("dialog.missing_backup"))
                return
            if not self._ask_yes_no(
                t("dialog.create_backup_title"),
                t("dialog.create_backup", path=dst),
            ):
                return
            try:
                dst_path.mkdir(parents=True, exist_ok=True)
            except OSError:
                messagebox.showerror(t("dialog.error_title"), t("dialog.missing_backup"))
                return

        if is_inside(dst, src):
            messagebox.showerror(t("dialog.error_title"), t("dialog.backup_inside_work"))
            return

        # Check disk space on start
        try:
            usage = shutil.disk_usage(dst_path)
            free_mb = usage.free / (1024 * 1024)
            if free_mb < MIN_DISK_FREE_MB:
                self._disk_low = True
                self._set_status("status.disk_low")
                self.log("log.disk_low", free_mb=int(free_mb))
                return
        except OSError:
            pass
        self._disk_low = False

        save_prefs(src, dst, max_versions=self.versions_var.get(), sound=self.sound_var.get())

        max_ver = self.versions_var.get()
        self._observer_retries = 0
        self.handler = BackupHandler(
            src, dst, self.log, self._set_busy,
            max_versions=max_ver, notify_callback=self._on_backup_complete,
        )
        self._set_status("status.scanning")
        self.root.update_idletasks()
        self.handler.build_baseline()

        self._start_observer()

        self.running = True
        self.paused = False
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        self._set_button(self.COLOR_WATCHING, "btn.pause")
        self._set_status("status.watching")
        self.log("log.watching", path=src)
        self.log("log.backups_to", path=dst)
        self.log("log.keeping_versions", count=max_ver)
        self._start_size_refresh()
        self._update_tray()

    def _start_observer(self):
        """Start the observer with error recovery."""
        try:
            self.observer = Observer()
            self.observer.schedule(self.handler, self.src_var.get().strip(), recursive=True)
            self.observer.start()
        except Exception as e:
            log_error(f"Observer start failed: {e}")
            if self._observer_retries < 3:
                self._observer_retries += 1
                self.log("log.restarting", tries=self._observer_retries)
                time.sleep(5)
                self._start_observer()
            else:
                log_error("Observer failed to start after 3 retries")
                self.log("log.restart_failed", tries=3, error=e)
                self._set_status("status.error")
                self._tray_notify(t("app.title"), t("tray.balloon_error"))

    def _worker_loop(self):
        disk_check_counter = 0
        while self.running:
            try:
                if self.handler:
                    self.handler.process_pending()
                # Periodic disk space check (every 60 polls = ~30s)
                disk_check_counter += 1
                if disk_check_counter >= 60:
                    disk_check_counter = 0
                    self._check_disk_space()
            except Exception as e:
                log_error(f"Worker loop error: {e}")
                self.log("log.worker_error", error=e)
            time.sleep(POLL_INTERVAL)

    def _check_disk_space(self):
        """Check backup disk space and pause if critically low."""
        dst = self.dst_var.get().strip()
        if not dst:
            return
        try:
            usage = shutil.disk_usage(dst)
            free_mb = usage.free / (1024 * 1024)
            if free_mb < MIN_DISK_FREE_MB:
                if not self._disk_low and self.running and not self.paused:
                    self._disk_low = True
                    self.pause()
                    self._set_status("status.disk_low")
                    self._tray_notify(
                        t("dialog.disk_low_title"),
                        t("dialog.disk_low_body", free_mb=int(free_mb)),
                    )
                    self.log("log.disk_low", free_mb=int(free_mb))
                    log_warning(f"Disk space low: {free_mb:.0f} MB free on backup drive")
            else:
                if self._disk_low and free_mb >= MIN_DISK_FREE_MB + 100:
                    self._disk_low = False
                    self.log("log.disk_space_ok")
                    log_info("Disk space recovered, resuming")
        except OSError:
            pass

    def stop(self):
        self.running = False
        self.paused = False
        self._disk_low = False
        self._observer_retries = 0
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=3)
            self.observer = None
        self.handler = None
        self._set_button(self.COLOR_IDLE, "btn.start")
        self._set_status("status.stopped")
        self._stop_size_refresh()
        self.log("log.stopped")
        self._update_tray()

    def _on_close(self):
        self._stop_size_refresh()
        if self.running:
            if not self._ask_yes_no(t("dialog.close_title"), t("dialog.close_body")):
                return
            self.stop()
        self._destroy_tray()
        log_info("AutoBackup shutting down")
        self.root.destroy()

    # --- Backup size display ---
    def _start_size_refresh(self):
        self._stop_size_refresh()
        self._refresh_size()
        self._size_job = self.root.after(5000, self._start_size_refresh)

    def _stop_size_refresh(self):
        if self._size_job is not None:
            self.root.after_cancel(self._size_job)
            self._size_job = None

    def _refresh_size(self):
        dst = self.dst_var.get().strip()
        if dst and os.path.isdir(dst):
            size = folder_size(dst)
            self.size_var.set(f"({format_size(size)})")
        else:
            self.size_var.set("")

    # --- Notification ---
    def _on_backup_complete(self, path=""):
        self._tray_notify(
            t("app.title"),
            t("tray.balloon_saved", file=path or "?"),
        )
        if self.sound_var.get():
            wav = resource_path("notification.wav")
            if os.path.exists(wav):
                self._play_sound(wav)

    # --- Startup with Windows ---
    def _on_startup_toggled(self):
        set_startup(self.startup_var.get())

    def _on_sound_toggled(self):
        save_prefs(
            self.src_var.get().strip(), self.dst_var.get().strip(),
            sound=self.sound_var.get(),
        )

    # --- Tray ---
    def _get_tray_status(self):
        if self._disk_low:
            return "error", t("tray.tooltip_error")
        if self.running and self._busy:
            return "busy", t("tray.tooltip_watching")
        if self.running and self.paused:
            return "paused", t("tray.tooltip_paused")
        if self.running:
            return "watching", t("tray.tooltip_watching")
        return "stopped", t("tray.tooltip_stopped")

    def _make_tray_menu(self):
        status_key, _ = self._get_tray_status()
        if self.running and not self.paused and not self._busy and not self._disk_low:
            pause_text = t("tray.menu.pause")
        else:
            pause_text = t("tray.menu.resume")
        return pystray.Menu(
            pystray.MenuItem(t("tray.menu.open"), self._tray_open),
            pystray.MenuItem(pause_text, self._tray_toggle_pause),
            pystray.MenuItem(t("tray.menu.restore"), self._tray_restore),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(t("tray.menu.exit"), self._tray_exit),
        )

    def _setup_tray(self):
        try:
            status_key, tooltip = self._get_tray_status()
            icon_img = _tray_image(_TRAY_COLORS.get(status_key, "#9e9e9e"))
            self._tray_icon = pystray.Icon(
                "AutoBackup", icon_img, tooltip, self._make_tray_menu(),
            )
            self._tray_icon._on_notification_failure = lambda: None
            t = threading.Thread(target=self._tray_icon.run, daemon=True)
            t.start()
        except Exception as e:
            log_error(f"Tray setup failed: {e}")

    def _update_tray(self):
        if not self._tray_icon:
            return
        try:
            status_key, tooltip = self._get_tray_status()
            self._tray_icon.icon = _tray_image(_TRAY_COLORS.get(status_key, "#9e9e9e"))
            self._tray_icon.title = tooltip
            self._tray_icon.menu = self._make_tray_menu()
            self._tray_icon.update_menu()
        except Exception as e:
            log_error(f"Tray update error: {e}")

    def _destroy_tray(self):
        if self._tray_icon:
            try:
                self._tray_icon.stop()
            except Exception:
                pass
            self._tray_icon = None

    def _tray_open(self):
        self.root.after(0, lambda: (
            self.root.deiconify(), self.root.lift(), self.root.focus_force(),
        ))

    def _tray_toggle_pause(self):
        self.root.after(0, self.toggle)

    def _tray_restore(self):
        self.root.after(0, self._show_restore)

    def _tray_exit(self):
        self.root.after(0, self._on_close)

    def _tray_notify(self, title, message):
        if not self._tray_icon:
            return
        try:
            if sys.platform == "win32":
                nid = NOTIFYICONDATAW(
                    cbSize=ctypes.sizeof(NOTIFYICONDATAW),
                    hWnd=self._tray_icon._hwnd,
                    uID=id(self._tray_icon),
                    uFlags=NIF_INFO,
                    szInfo=message,
                    szInfoTitle=title or "",
                    dwInfoFlags=NIIF_NOSOUND,
                )
                ctypes.windll.shell32.Shell_NotifyIconW(NIM_MODIFY, ctypes.byref(nid))
            else:
                self._tray_icon.notify(title, message)
        except Exception:
            pass

    def _on_minimize(self, event):
        """When window is minimized to taskbar, keep running silently."""
        pass

    # --- Inline restore (Restore tab) ---
    def _show_restore(self):
        """Switch to the Restore tab and refresh the backup list."""
        self.notebook.select(1)
        self._restore_refresh()

    def _on_tab_changed(self, event=None):
        if self.notebook.index(self.notebook.select()) == 1:
            self._restore_refresh()

    def _restore_refresh(self):
        dst = self.dst_var.get().strip()
        query = self.restore_search_var.get().strip().lower()
        if not dst or not os.path.isdir(dst):
            self.restore_status_var.set(t("restore.no_backup"))
            self.restore_tree.delete(*self.restore_tree.get_children())
            return
        self.restore_tree.delete(*self.restore_tree.get_children())
        count = 0
        for dirpath, _, filenames in os.walk(dst):
            for name in filenames:
                if name.endswith(HASH_EXT):
                    continue
                stem, ext = os.path.splitext(name)
                if len(stem) > TS_LEN + 1 and stem[-TS_LEN - 1] == "_":
                    ts_part = stem[-TS_LEN:]
                    try:
                        dt = datetime.strptime(ts_part, TS_FORMAT)
                        if query and query not in name.lower():
                            continue
                        full = Path(dirpath) / name
                        size = os.path.getsize(full)
                        self.restore_tree.insert("", "end", values=(
                            name,
                            dt.strftime("%Y-%m-%d %H:%M"),
                            format_size(size),
                        ), tags=(str(full),))
                        count += 1
                    except ValueError:
                        continue
        if count == 0:
            self.restore_status_var.set(t("restore.empty"))
        else:
            self.restore_status_var.set(f"{count} {t('restore.col_name').lower()}" + ("s" if count != 1 else ""))

    def _restore_open(self, event=None):
        sel = self.restore_tree.selection()
        if not sel:
            return
        item = self.restore_tree.item(sel[0])
        tags = item.get("tags", ())
        if tags:
            path = Path(tags[0])
            if path.exists():
                if sys.platform == "win32":
                    os.startfile(path)
                else:
                    import subprocess
                    subprocess.Popen(["xdg-open", str(path)])

    def _restore_restore(self):
        sel = self.restore_tree.selection()
        if not sel:
            return
        item = self.restore_tree.item(sel[0])
        tags = item.get("tags", ())
        if not tags:
            return
        path = Path(tags[0])
        if not path.exists():
            return
        stem, ext = os.path.splitext(path.name)
        if len(stem) > TS_LEN + 1 and stem[-TS_LEN - 1] == "_":
            original_stem = stem[:-(TS_LEN + 1)]
        else:
            original_stem = stem
        original_name = original_stem + ext
        src = self.src_var.get().strip()
        initial_dir = src if os.path.isdir(src) else dst
        dest = filedialog.asksaveasfilename(
            title=t("restore.save_as"),
            initialfile=original_name,
            initialdir=initial_dir,
        )
        if dest:
            try:
                shutil.copy2(str(path), dest)
                self.log("restore.restored", src=path.name, dest=dest)
                messagebox.showinfo(t("restore.done"), t("restore.restored", src=path.name, dest=dest))
            except Exception as e:
                messagebox.showerror(t("restore.error"), str(e))

    def _restore_export(self):
        dst = self.dst_var.get().strip()
        if not dst or not os.path.isdir(dst):
            return
        dest = filedialog.asksaveasfilename(
            title=t("restore.export_save_as"),
            defaultextension=".html",
            filetypes=[("HTML", "*.html"), ("CSV", "*.csv")],
            initialfile="backup_list.html",
        )
        if not dest:
            return
        try:
            rows = []
            for dirpath, _, filenames in os.walk(dst):
                for name in filenames:
                    if name.endswith(HASH_EXT):
                        continue
                    stem, ext = os.path.splitext(name)
                    if len(stem) > TS_LEN + 1 and stem[-TS_LEN - 1] == "_":
                        ts_part = stem[-TS_LEN:]
                        try:
                            dt = datetime.strptime(ts_part, TS_FORMAT)
                            full = Path(dirpath) / name
                            rows.append((full, name, dt, os.path.getsize(full)))
                        except ValueError:
                            continue
            rows.sort(key=lambda x: x[2], reverse=True)
            is_html = dest.lower().endswith(".html")
            if is_html:
                html_dir = "rtl" if is_rtl() else "ltr"
                html_align = "right" if is_rtl() else "left"
                lines = [
                    "<!DOCTYPE html><html dir='" + html_dir + "'><head><meta charset='utf-8'>",
                    f"<title>{t('restore.title')}</title>",
                    "<style>body{font-family:sans-serif;margin:20px}"
                    "table{border-collapse:collapse;width:100%}"
                    "th,td{text-align:" + html_align + ";padding:6px 10px;border-bottom:1px solid #ddd}"
                    "th{background:#f5f5f5}</style></head><body>",
                    f"<h1>{t('restore.title')}</h1>",
                    f"<p>Backup folder: {dst}</p>",
                    f"<p>Generated: {datetime.now():%Y-%m-%d %H:%M}</p>",
                    "<table><tr>"
                    f"<th>{t('restore.col_name')}</th>"
                    f"<th>{t('restore.col_date')}</th>"
                    f"<th>{t('restore.col_size')}</th>"
                    "</tr>",
                ]
                for full, name, dt, size in rows:
                    lines.append(
                        f"<tr><td>{name}</td>"
                        f"<td>{dt:%Y-%m-%d %H:%M}</td>"
                        f"<td>{format_size(size)}</td></tr>"
                    )
                lines.append("</table></body></html>")
                Path(dest).write_text("\n".join(lines), encoding="utf-8")
            else:
                import csv
                with open(dest, "w", newline="", encoding="utf-8-sig") as f:
                    w = csv.writer(f)
                    w.writerow([t("restore.col_name"), t("restore.col_date"), t("restore.col_size")])
                    for full, name, dt, size in rows:
                        w.writerow([name, dt.strftime("%Y-%m-%d %H:%M"), format_size(size)])
            self.log("restore.export_done", path=dest)
            messagebox.showinfo(t("restore.export"), t("restore.export_done", path=dest))
        except Exception as e:
            messagebox.showerror(t("restore.error"), str(e))

    def _on_log_right_click(self, event):
        """Right-click on log to restore a file."""
        self._show_restore()

    # --- First-run wizard ---
    def _check_first_run(self):
        if not winreg:
            return False
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                try:
                    val, _ = winreg.QueryValueEx(key, "FirstRun")
                    return int(val) != 0
                except FileNotFoundError:
                    return True
        except FileNotFoundError:
            return True
        except Exception:
            return True

    def _set_first_run_done(self):
        if not winreg:
            return
        try:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                winreg.SetValueEx(key, "FirstRun", 0, winreg.REG_DWORD, 0)
        except Exception:
            pass

    def _show_wizard(self):
        win = tk.Toplevel(self.root)
        win.title(t("wizard.title"))
        win.geometry("480x420")
        win.minsize(440, 380)
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        center_window(win, self.root)

        frame = ttk.Frame(win, padding=16)
        frame.pack(fill="both", expand=True)

        # Language - prominent at top
        lang_box = ttk.Labelframe(frame, text=t("wizard.lang"), padding=8)
        lang_box.pack(fill="x", pady=(0, 12))
        lang_inner = ttk.Frame(lang_box)
        lang_inner.pack()
        wiz_lang_var = tk.StringVar()
        wiz_label_to_code = {}
        codes = discover_langs()
        for code in codes:
            wiz_label_to_code[lang_label(code)] = code
        wiz_rbs = []
        cols = 3
        for i, code in enumerate(codes):
            label = lang_label(code)
            rb = ttk.Radiobutton(
                lang_inner, text=label, variable=wiz_lang_var,
                value=label,
            )
            rb.grid(row=i // cols, column=i % cols, sticky="w", padx=4, pady=1)
            wiz_rbs.append(rb)
        wiz_lang_var.set(lang_label(current_lang()))

        lbl_intro = ttk.Label(
            frame, text=t("wizard.intro"),
            font=("Segoe UI", 11), wraplength=440,
        )
        lbl_intro.pack(anchor="w", pady=(0, 12))

        lbl_step1 = ttk.Label(
            frame, text=t("wizard.step1"),
            font=("Segoe UI", 10, "bold"),
        )
        lbl_step1.pack(anchor="w")
        src_frame = ttk.Frame(frame)
        src_frame.pack(fill="x", pady=(2, 10))
        self._wiz_src_var = tk.StringVar(value=self._saved_src)
        ttk.Entry(src_frame, textvariable=self._wiz_src_var).pack(side="left", fill="x", expand=True, padx=(0, 4))
        wiz_btn_src = ttk.Button(
            src_frame, text=t("btn.browse"),
            command=lambda: self._wiz_src_var.set(
                filedialog.askdirectory(title=t("dialog.pick_work")) or self._wiz_src_var.get(),
            ),
        )
        wiz_btn_src.pack(side="right")

        lbl_step2 = ttk.Label(
            frame, text=t("wizard.step2"),
            font=("Segoe UI", 10, "bold"),
        )
        lbl_step2.pack(anchor="w")
        dst_frame = ttk.Frame(frame)
        dst_frame.pack(fill="x", pady=(2, 10))
        self._wiz_dst_var = tk.StringVar(value=self._saved_dst)
        ttk.Entry(dst_frame, textvariable=self._wiz_dst_var).pack(side="left", fill="x", expand=True, padx=(0, 4))
        wiz_btn_dst = ttk.Button(
            dst_frame, text=t("btn.browse"),
            command=lambda: self._wiz_dst_var.set(
                filedialog.askdirectory(title=t("dialog.pick_backup")) or self._wiz_dst_var.get(),
            ),
        )
        wiz_btn_dst.pack(side="right")

        def _on_wizard_lang(*_):
            try:
                code = wiz_label_to_code.get(wiz_lang_var.get())
                if code and code != current_lang():
                    set_locale(code)
                    save_prefs(self.src_var.get().strip(), self.dst_var.get().strip(), code, self.versions_var.get())
                    self._refresh_ui()
                    win.title(t("wizard.title"))
                    lang_box.config(text=t("wizard.lang"))
                    lbl_intro.config(text=t("wizard.intro"))
                    lbl_step1.config(text=t("wizard.step1"))
                    lbl_step2.config(text=t("wizard.step2"))
                    wiz_btn_src.config(text=t("btn.browse"))
                    wiz_btn_dst.config(text=t("btn.browse"))
                    wiz_btn_skip.config(text=t("wizard.skip"))
                    wiz_btn_start.config(text=t("wizard.start"))
                    for rb, c in zip(wiz_rbs, codes):
                        rb.config(text=lang_label(c))
                    rtl = is_rtl()
                    a = "e" if rtl else "w"
                    lbl_intro.pack_configure(anchor=a)
                    lbl_step1.pack_configure(anchor=a)
                    lbl_step2.pack_configure(anchor=a)
                    wiz_btn_src.pack_configure(side="left" if rtl else "right")
                    wiz_btn_dst.pack_configure(side="left" if rtl else "right")
                    wiz_btn_skip.pack_configure(side="right" if rtl else "left")
                    wiz_btn_start.pack_configure(side="left" if rtl else "right")
            except Exception as e:
                log_error(f"Wizard lang switch failed: {e}")

        wiz_lang_var.trace_add("write", _on_wizard_lang)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(fill="x")
        wiz_btn_skip = ttk.Button(
            btn_frame, text=t("wizard.skip"),
            command=lambda: self._wizard_finish(win),
        )
        wiz_btn_skip.pack(side="left")
        wiz_btn_start = ttk.Button(
            btn_frame, text=t("wizard.start"),
            command=lambda: self._wizard_apply(win),
        )
        wiz_btn_start.pack(side="right")

        win.wait_window()

    def _wizard_apply(self, win):
        src = self._wiz_src_var.get().strip()
        dst = self._wiz_dst_var.get().strip()
        if src:
            self.src_var.set(src)
        if dst:
            self.dst_var.set(dst)
        self._wizard_finish(win)
        if src and dst and os.path.isdir(src):
            self.root.after(100, self.start)

    def _wizard_finish(self, win):
        self._set_first_run_done()
        win.destroy()

    def _reset_wizard(self):
        """Reset first-run flag and show the welcome wizard again."""
        if winreg:
            try:
                with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
                    winreg.SetValueEx(key, "FirstRun", 0, winreg.REG_DWORD, 1)
            except Exception:
                pass
        self._show_wizard()

if __name__ == "__main__":
    _src, _dst, _lang, _ver, _sound = load_prefs()
    init_locale(_lang)
    root = tk.Tk()
    app = AutoBackupApp(root)
    root.mainloop()
