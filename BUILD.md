# Building AutoBackup (developers)

End-user instructions are in [README.md](README.md) (English) and [README.ru.md](README.ru.md) (Russian).

## Requirements

- Windows 10 or newer
- Python 3.8+
- Dependencies from [requirements.txt](requirements.txt)

## Setup

```powershell
cd AutoBackup
python -m venv .venv
.\.venv\Scripts\activate
python -m pip install -r requirements.txt
```

## Run from source

```powershell
python AutoBackup.py
```

## Build the .exe

```powershell
pyinstaller AutoBackup.spec
```

Output: `dist\AutoBackup.exe`

The spec bundles `icon.ico`, `locale_util.py`, and `strings/*.json` for the packaged app.

To add a language: add `strings/xx.json` and an entry in `LANG_LABELS` inside `locale_util.py`.
