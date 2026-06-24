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
- Only the **latest 5 copies** of each file are kept; older ones are removed automatically.

---

## Getting an old version back

AutoBackup never changes your working files by itself.

1. Click **Open backups** (or open your backup folder in File Explorer).
2. Find the dated copy you want.
3. Copy it into your work folder.
4. Rename it if you need to replace the current file.

---

## Good to know

- Keep AutoBackup running while you work - closing it stops protection.
- The backup folder must **not** sit inside the work folder.
- If Windows is set to Russian, the app uses Russian; otherwise English.
- Use the language menu (bottom right) to switch anytime.
- This is a helper for your project files. It does not replace full PC backups, cloud storage, or professional backup software.

---

## License

**Nuclear Waste Software License v1.0 (NWSL)** - [read license](https://github.com/ErikMcClure/bad-licenses/blob/master/NWSL)

Copyright (c) 2026 Lemis.

---

*Developers: [BUILD.md](BUILD.md)*
