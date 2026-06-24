import ctypes
import os
import sys
import shutil
import time
import threading
import hashlib
import webbrowser
from datetime import datetime
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, scrolledtext, messagebox
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from locale_util import init_locale, set_locale, current_lang, discover_langs, lang_label, t, help_text
from version_check import check_for_update

try:
    import winreg
except ImportError:
    winreg = None  # non-Windows fallback

APP_VERSION = "1.1.0"

QUIET_SECONDS = 2.0
POLL_INTERVAL = 0.5
MAX_VERSIONS_PER_FILE = 5

HASH_EXT = ".hash"
FILE_ATTRIBUTE_HIDDEN = 0x02

TS_FORMAT = "%Y%m%d_%H%M%S"
TS_LEN = 15

REG_PATH = r"Software\\Lemis\\AutoBackup"


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
        return "", "", ""
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            src, _ = winreg.QueryValueEx(key, "SourcePath")
            dst, _ = winreg.QueryValueEx(key, "BackupPath")
            try:
                lang, _ = winreg.QueryValueEx(key, "Language")
            except FileNotFoundError:
                lang = ""
            return src, dst, lang
    except FileNotFoundError:
        return "", "", ""
    except Exception:
        return "", "", ""


def save_prefs(src, dst, lang=None):
    if not winreg:
        return
    try:
        with winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH) as key:
            winreg.SetValueEx(key, "SourcePath", 0, winreg.REG_SZ, src or "")
            winreg.SetValueEx(key, "BackupPath", 0, winreg.REG_SZ, dst or "")
            if lang is not None:
                winreg.SetValueEx(key, "Language", 0, winreg.REG_SZ, lang)
    except Exception as e:
        print(f"Save prefs failed: {e}")


def resource_path(relative):
    """Get path to resource, works for dev and for PyInstaller bundle."""
    if hasattr(sys, "_MEIPASS"):
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
    def __init__(self, source_dir, backup_dir, log_callback, busy_callback):
        self.source_dir = Path(source_dir).resolve()
        self.backup_dir = Path(backup_dir).resolve()
        self.log = log_callback
        self.set_busy = busy_callback
        self.pending = {}
        self.lock = threading.Lock()
        self.baseline = {}

    @staticmethod
    def _fingerprint(path):
        stat = path.stat()
        return (stat.st_size, stat.st_mtime_ns)

    def _iter_source_files(self):
        for dirpath, _, filenames in os.walk(self.source_dir):
            for name in filenames:
                yield Path(dirpath) / name

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
        self.log(t("log.baseline_done", count=count))

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
            self.log(t("log.track_error", error=e))

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
                return hash_file.read_text(encoding="utf-8").strip()
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
                self.log(t("log.pruned", name=old.name))
            except Exception as e:
                self.log(t("log.prune_failed", name=old.name, error=e))

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
                self.log(t("log.still_locked", name=src.name))
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
                self.log(t("log.skipped_unchanged", path=str(rel)))
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
                hash_file.write_text(current_hash, encoding="utf-8")
                hide_file(hash_file)
            except Exception as e:
                self.log(t("log.sidecar_failed", error=e))

            size_mb = dest.stat().st_size / 1048576
            self.log(t(
                "log.saved",
                path=str(rel),
                size_mb=size_mb,
                seconds=elapsed,
            ))

            self.baseline[key] = fp
            self._prune_old(backup_folder, original_name)

        except Exception as e:
            self.log(t("log.backup_failed", path=path, error=e))
        finally:
            self.set_busy(False)


class AutoBackupApp:
    COLOR_IDLE = "#9e9e9e"
    COLOR_WATCHING = "#43a047"
    COLOR_BUSY = "#fb8c00"
    COLOR_UPDATE_PATCH = "#5c6bc0"
    COLOR_UPDATE_MAJOR = "#e53935"
    COLOR_UPDATE_MAJOR_ALT = "#ff7043"

    def __init__(self, root):
        self.root = root
        self.root.title(f"{t('app.title')} v{APP_VERSION}")
        self.root.geometry("480x340")
        self.root.minsize(480, 340)

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
        self._busy = False
        self._status_key = "status.stopped"
        self._help_tooltip = None
        self._update_info = None
        self._blink_job = None
        self._blink_on = False

        self._build_ui()
        self._set_status("status.stopped")
        threading.Thread(target=self._check_update_thread, daemon=True).start()

    def _build_ui(self):
        grid = ttk.Frame(self.root)
        grid.pack(fill="x", padx=8, pady=4)
        grid.columnconfigure(1, weight=1)

        saved_src, saved_dst, _saved_lang = load_prefs()

        self.lbl_work = ttk.Label(grid, text=t("label.work_folder"))
        self.lbl_work.grid(
            row=0, column=0, sticky="w", padx=(0, 6), pady=3,
        )
        self.src_var = tk.StringVar(value=saved_src)
        ttk.Entry(grid, textvariable=self.src_var).grid(row=0, column=1, sticky="ew", pady=3)
        self.btn_browse_src = ttk.Button(grid, text=t("btn.browse"), command=self._pick_src)
        self.btn_browse_src.grid(row=0, column=2, padx=4, pady=3)

        self.lbl_backup = ttk.Label(grid, text=t("label.backup_folder"))
        self.lbl_backup.grid(
            row=1, column=0, sticky="w", padx=(0, 6), pady=3,
        )
        self.dst_var = tk.StringVar(value=saved_dst)
        ttk.Entry(grid, textvariable=self.dst_var).grid(row=1, column=1, sticky="ew", pady=3)
        self.btn_browse_dst = ttk.Button(grid, text=t("btn.browse"), command=self._pick_dst)
        self.btn_browse_dst.grid(row=1, column=2, padx=4, pady=3)

        self.run_btn = tk.Button(
            grid, text=t("btn.start"), command=self.toggle,
            bg=self.COLOR_IDLE, fg="white", activebackground=self.COLOR_IDLE,
            font=("Segoe UI", 10, "bold"), width=8,
            relief="flat", cursor="hand2", borderwidth=0,
        )
        self.run_btn.grid(row=0, column=3, padx=(5, 0), pady=3, sticky="ns")

        help_frame = ttk.Frame(grid)
        help_frame.grid(row=1, column=3, padx=(5, 0), pady=(4, 0))
        self.help_lbl = tk.Label(
            help_frame, text="  ?  ",
            font=("Segoe UI", 10, "bold"),
            fg="white", bg="#1e88e5",
            cursor="question_arrow", padx=2,
        )
        self.help_lbl.pack()
        self._help_tooltip = ToolTip(self.help_lbl, help_text(MAX_VERSIONS_PER_FILE))

        actions = ttk.Frame(self.root)
        actions.pack(fill="x", padx=8, pady=(0, 4))
        self.btn_open_backups = ttk.Button(
            actions, text=t("btn.open_backups"), command=self._open_backups,
        )
        self.btn_open_backups.pack(side="left")

        self.update_btn = tk.Button(
            actions, command=self._open_release,
            fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", borderwidth=0, padx=8, pady=2,
        )

        self.lang_frame = ttk.Frame(actions)
        self.lang_frame.pack(side="right")
        self.lang_var = tk.StringVar()
        self.lang_combo = ttk.Combobox(
            self.lang_frame, textvariable=self.lang_var,
            state="readonly", width=14,
        )
        self.lang_combo.pack(side="left")
        self.lang_combo.bind("<<ComboboxSelected>>", self._on_lang_selected)
        self._label_to_code = {}
        self._reload_lang_choices()

        self.status_var = tk.StringVar()
        self.status_lbl = ttk.Label(
            self.root, textvariable=self.status_var,
            font=("Segoe UI", 9), wraplength=440,
        )
        self.status_lbl.pack(fill="x", padx=8, pady=(0, 4))

        self.log_box = scrolledtext.ScrolledText(
            self.root, height=18, state="disabled", wrap="word",
            font=("Segoe UI", 9),
        )
        self.log_box.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    def _set_status(self, key):
        self._status_key = key
        self.status_var.set(t(key))

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
        save_prefs(self.src_var.get().strip(), self.dst_var.get().strip(), lang)
        self._refresh_ui()

    def _sync_lang_dropdown(self):
        self.lang_var.set(lang_label(current_lang()))

    def _refresh_ui(self):
        self.root.title(f"{t('app.title')} v{APP_VERSION}")
        self.lbl_work.config(text=t("label.work_folder"))
        self.lbl_backup.config(text=t("label.backup_folder"))
        self.btn_browse_src.config(text=t("btn.browse"))
        self.btn_browse_dst.config(text=t("btn.browse"))
        self.btn_open_backups.config(text=t("btn.open_backups"))
        if self.running:
            if self._busy:
                self._set_button(self.COLOR_BUSY, "btn.busy")
                self.status_var.set(t("status.copying"))
            else:
                self._set_button(self.COLOR_WATCHING, "btn.stop")
                self.status_var.set(t(self._status_key))
        else:
            self._set_button(self.COLOR_IDLE, "btn.start")
            self.status_var.set(t(self._status_key))
        if self._help_tooltip:
            self._help_tooltip.text = help_text(MAX_VERSIONS_PER_FILE)
        self._sync_lang_dropdown()
        self._refresh_update_button()

    def _check_update_thread(self):
        info = check_for_update(APP_VERSION)
        if info:
            self.root.after(0, lambda i=info: self._show_update_button(i))

    def _show_update_button(self, info):
        self._update_info = info
        if not self.update_btn.winfo_ismapped():
            self.update_btn.pack(side="left", padx=(8, 0))
        self._refresh_update_button()
        if info["level"] == "major":
            self._start_blink()
        else:
            self._stop_blink()

    def _refresh_update_button(self):
        if not self._update_info:
            return
        info = self._update_info
        if info["level"] == "major":
            self.update_btn.configure(
                text=t("btn.update_major"),
                bg=self.COLOR_UPDATE_MAJOR if self._blink_on else self.COLOR_UPDATE_MAJOR_ALT,
                activebackground=self.COLOR_UPDATE_MAJOR,
            )
        else:
            self.update_btn.configure(
                text=t("btn.update_patch", version=info["version"]),
                bg=self.COLOR_UPDATE_PATCH,
                activebackground=self.COLOR_UPDATE_PATCH,
            )

    def _start_blink(self):
        self._stop_blink()
        self._blink_on = True
        self._blink_tick()

    def _blink_tick(self):
        if not self._update_info or self._update_info["level"] != "major":
            return
        self._blink_on = not self._blink_on
        self._refresh_update_button()
        self._blink_job = self.root.after(500, self._blink_tick)

    def _stop_blink(self):
        if self._blink_job is not None:
            self.root.after_cancel(self._blink_job)
            self._blink_job = None

    def _open_release(self):
        if self._update_info and self._update_info.get("url"):
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
            self.root.after(0, lambda: self._set_button(self.COLOR_WATCHING, "btn.stop"))
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

    def log(self, msg):
        ts = datetime.now().strftime("%H:%M:%S")
        line = f"[{ts}] {msg}\n"
        self.root.after(0, self._append_log, line)

    def _append_log(self, line):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", line)
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def toggle(self):
        if self.running:
            self.stop()
        else:
            self.start()

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
            if not messagebox.askyesno(
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

        save_prefs(src, dst)

        self.handler = BackupHandler(src, dst, self.log, self._set_busy)
        self._set_status("status.scanning")
        self.root.update_idletasks()
        self.handler.build_baseline()

        self.observer = Observer()
        self.observer.schedule(self.handler, src, recursive=True)
        self.observer.start()

        self.running = True
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

        self._set_button(self.COLOR_WATCHING, "btn.stop")
        self._set_status("status.watching")
        self.log(t("log.watching", path=src))
        self.log(t("log.backups_to", path=dst))
        self.log(t("log.keeping_versions", count=MAX_VERSIONS_PER_FILE))

    def _worker_loop(self):
        while self.running:
            try:
                if self.handler:
                    self.handler.process_pending()
            except Exception as e:
                self.log(t("log.worker_error", error=e))
            time.sleep(POLL_INTERVAL)

    def stop(self):
        self.running = False
        if self.observer:
            self.observer.stop()
            self.observer.join(timeout=3)
            self.observer = None
        self.handler = None
        self._set_button(self.COLOR_IDLE, "btn.start")
        self._set_status("status.stopped")
        self.log(t("log.stopped"))

    def _on_close(self):
        self._stop_blink()
        if self.running:
            if not messagebox.askyesno(t("dialog.close_title"), t("dialog.close_body")):
                return
            self.stop()
        self.root.destroy()


if __name__ == "__main__":
    _src, _dst, _lang = load_prefs()
    init_locale(_lang)
    root = tk.Tk()
    app = AutoBackupApp(root)
    root.mainloop()
