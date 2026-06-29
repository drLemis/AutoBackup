# AutoBackup

**English** | [Русский](README.ru.md)

AutoBackup quietly watches the folder where you work and saves dated backup copies when you save a file. If Photoshop, Word, or another program overwrites the same file again and again, you still keep the last few versions in a separate folder.

## Download

[![Download here!](https://img.shields.io/badge/Download-here!-2ea44f?style=for-the-badge)](https://github.com/drLemis/AutoBackup/releases/latest)

**[Download here!](https://github.com/drLemis/AutoBackup/releases/latest)**

1. Click the link above (or the green button).
2. On the page that opens, click **AutoBackup.exe** to download it.
3. Double-click **AutoBackup.exe** to run. Nothing to install.

[![License: NWSL](https://img.shields.io/badge/license-NWSL-orange)](https://github.com/ErikMcClure/bad-licenses/blob/master/NWSL)

---

## What you need

- Windows 10 or newer
- A **work folder** (your projects)
- A **backup folder** on a different location - not inside the work folder (for example an external drive or `D:\Backups`)

---

## Quick start

1. Open AutoBackup.
2. Click **Browse...** next to **Work folder** and pick where your files live.
3. Click **Browse...** next to **Backup folder** and pick where copies should go.
4. Click **START** and leave the window open while you work.
5. To see your copies, click **Open backups**.

The line under the buttons tells you what is happening: stopped, watching, or copying a file.

**Button colors**

| Color | Meaning |
|-------|---------|
| Gray | Stopped |
| Green | Watching - backups run automatically |
| Orange | Copying a file right now |

---

## What happens when you save

- When you press **START**, AutoBackup notes which files are already there. **Only files you change after that** get backed up - not your whole library at once.
- After you finish saving a file, AutoBackup waits a moment, then saves a copy with the date and time in the name, for example: `MyDrawing_20260526_143022.psd`
- Folders inside your work folder are copied the same way inside the backup folder.
- If you save the same file again with no real changes, AutoBackup skips making another copy.
- Temp files, caches (`.git`, `node_modules`, `__pycache__`), and OS junk (Thumbs.db, etc.) are automatically excluded.
- Set how many copies to keep per file with the **Keep copies** spinner (1–100).

---

## Pause and resume

- Click **PAUSE** to stop watching temporarily — your baseline is kept in memory, so no re-scanning happens when you resume.
- Click **RESUME** to continue watching instantly.
- Use pause when you're doing a batch of saves you don't want backed up yet.

---

## Getting an old version back

AutoBackup never changes your working files by itself.

- Click **Restore...** to browse all your backup versions with search, dates, and file sizes.
- Select a file and click **Restore to...** to save it back to your work folder (or anywhere you choose).
- Or click **Open** to preview a backup without restoring it.

---

## Good to know

- Keep AutoBackup running while you work - closing it stops protection.
- The backup folder must **not** sit inside the work folder.
- If Windows is set to Russian, the app uses Russian; otherwise English.
- Use the language menu (bottom right) to switch anytime.
- Check **Start with Windows** to launch AutoBackup automatically on login.
- Check **Sound** to hear a subtle chime when a backup completes (off by default).
- The backup folder size is shown next to the copies spinner so you know how much space is used.
- This is a helper for your project files. It does not replace full PC backups, cloud storage, or professional backup software.

---

## License

**Nuclear Waste Software License v1.0 (NWSL)** - [read license](https://github.com/ErikMcClure/bad-licenses/blob/master/NWSL)

Copyright (c) 2026 Lemis.

---

*Developers: [BUILD.md](BUILD.md)*
