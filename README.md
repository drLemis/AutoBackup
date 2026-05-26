# AutoBackup

AutoBackup is a small desktop utility that watches a work folder and automatically creates timestamped backup copies whenever files change.

It is designed for artists, designers, editors, and anyone working with applications that save over the same file repeatedly. Instead of losing older work, AutoBackup keeps recent versions in a separate backup folder.

[![License: NWSL](https://img.shields.io/badge/license-NWSL-orange)](https://github.com/ErikMcClure/bad-licenses/blob/master/NWSL)

<h2>Download:</h2>

[Latest release](https://github.com/drLemis/AutoBackup/releases/latest)

## Features

- Watches a selected work folder recursively.
- Creates a new timestamped backup after a file finishes saving.
- Mirrors the original folder structure inside the backup folder.
- Skips duplicate backups when the file content has not changed.
- Keeps only the latest 5 versions per file.
- Automatically prunes older versions.
- Waits for locked files to become available before copying.
- Saves your selected folders between runs on Windows.
- Provides a simple Tkinter GUI with live status logs.

## How It Works

When AutoBackup detects a created, modified, or moved file, it waits until the file has been quiet for 2 seconds. It also checks that the file is no longer locked by another application.

Once the file is ready, AutoBackup copies it to the backup folder using this format:

```text
OriginalName_YYYYMMDD_HHMMSS.ext
```

For example:

```text
Work/Project/File.psd
Backup/Project/File_20260526_224030.psd
```

Each backup also gets a small `.hash` sidecar file. AutoBackup uses this to avoid creating duplicate backups when the file content is unchanged.

## Requirements

- Windows 10 or newer recommended

And if you're a source-code type of person:
- Python 3.8+
- `watchdog`
- Tkinter, included with most standard Python installations

AutoBackup can run on non-Windows systems, but saved folder preferences use the Windows registry and are only persisted on Windows.

## Installation

Just download [AutoBackup.exe](https://github.com/drLemis/AutoBackup/releases/latest) and run it. That's it.

## Usage

1. Open AutoBackup.
2. Choose your **Work folder**.
3. Choose a **Backup folder**.
4. Click **START**.
5. Leave AutoBackup running while you work.

The backup folder must not be inside the watched work folder. This prevents AutoBackup from backing up its own backups in a loop.

Button colors:

- Gray: idle
- Green: watching
- Orange: copying a file

## Restoring Files

AutoBackup does not overwrite your working files when restoring. To restore an older version:

1. Open the backup folder.
2. Find the timestamped version you want.
3. Copy it back into your work folder manually.
4. Rename it if needed.

## Building a Windows Executable

The repository includes a PyInstaller spec file.

Install PyInstaller:

```powershell
python -m pip install pyinstaller watchdog
```

Build the executable:

```powershell
python -m PyInstaller --onefile --windowed --name AutoBackup --icon=icon.ico --add-data "icon.ico;." AutoBackup.py       
```

The generated executable will be placed in the `dist` folder.

## Project Structure

```text
AutoBackup.py       Main application
icon.ico            Application icon
```

## Notes

- AutoBackup keeps the latest 5 versions of each file.
- Backup filenames use local system time.
- Backup `.hash` files are used internally and should not be edited.
- **This is a local backup helper, not a replacement for full system backups, cloud sync, or version control!**

## License

This software is licensed under the **[NWSL](https://github.com/ErikMcClure/bad-licenses/blob/master/NWSL)**.

Copyright (c) 2026 Lemis.
