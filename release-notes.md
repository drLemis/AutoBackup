## v1.2.0 — Smarter, faster, more polished

### First-start experience
- **Auto-start on launch** — if your folders are already configured, AutoBackup begins watching immediately. No need to press START every time.
- **Sound on by default** — a subtle `chimes.wav` plays when a backup completes. Toggle off with the Sound checkbox.
- **All settings persisted** — Sound, Start with Windows, version count, language, and folder paths are all saved to the registry and restored on next launch.

### Smarter backups
- **File exclusions** — temp files (`.tmp`, `.bak`, `*~`), caches (`.git`, `node_modules`, `__pycache__`, `venv`), and OS junk (`Thumbs.db`, `.DS_Store`, `desktop.ini`) are automatically skipped. No more cluttered backups.
- **Configurable version retention** — spinner lets you choose 1–100 copies per file (was hardcoded to 5). Saved to registry.
- **Smarter hashing** — small files get a full-content hash; large files use the fast 3-chunk sample. Faster and more accurate.

### Pause & Resume
- **PAUSE button** stops the file watcher but keeps your baseline in memory. No re-scanning on resume.
- **RESUME** instantly re-enables watching. Perfect for batch operations you don't want backed up.

### Restore made easy
- **Restore... dialog** — browse all backup versions with search, date, and file size columns.
- **Restore to...** defaults to your work folder (not the backup folder). One-click restore to the right place.
- **Open** button to preview a backup without restoring.

### Quality of life
- **Backup folder size** — shown next to the copies spinner, auto-refreshes every 5 seconds.
- **Start with Windows** — checkbox adds/removes a registry Run key for automatic launch on login.
- **Sound notification** — plays `chimes.wav` at 50% volume when a backup completes. Off by default toggle.
