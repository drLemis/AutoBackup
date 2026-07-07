"""Check GitHub releases for a newer AutoBackup version and download updates."""
import json
import re
import sys
import urllib.request
from pathlib import Path

GITHUB_REPO = "drLemis/AutoBackup"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
CHECK_TIMEOUT = 8
DOWNLOAD_TIMEOUT = 60
USER_AGENT = "AutoBackup-UpdateCheck/1.0"


def parse_version(text: str) -> tuple[int, int, int]:
    text = text.strip().lstrip("vV")
    nums = [int(n) for n in re.findall(r"\d+", text)]
    while len(nums) < 3:
        nums.append(0)
    return tuple(nums[:3])


def classify_update(current: str, latest: str) -> str | None:
    """Return None, 'patch', or 'major' (minor/major bumps use the loud UI)."""
    cur = parse_version(current)
    lat = parse_version(latest)
    if lat <= cur:
        return None
    if lat[0] > cur[0] or lat[1] > cur[1]:
        return "major"
    if lat[2] > cur[2]:
        return "patch"
    return None


def check_for_update(current_version: str) -> dict | None:
    try:
        req = urllib.request.Request(
            API_URL,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": USER_AGENT,
            },
        )
        with urllib.request.urlopen(req, timeout=CHECK_TIMEOUT) as resp:
            data = json.loads(resp.read().decode())
        tag = data.get("tag_name", "")
        if not tag:
            return None
        level = classify_update(current_version, tag)
        if not level:
            return None
        version = tag.lstrip("vV")
        url = data.get("html_url") or RELEASE_URL
        assets = data.get("assets", [])
        return {
            "level": level,
            "version": version,
            "url": url,
            "tag": tag,
            "assets": assets,
            "body": data.get("body", ""),
        }
    except Exception:
        return None


def get_update_asset(info: dict) -> dict | None:
    """Find the best asset for the current platform."""
    if not info or not info.get("assets"):
        return None
    is_windows = sys.platform == "win32"
    for asset in info["assets"]:
        name = asset.get("name", "")
        if is_windows and name.endswith(".exe"):
            return asset
        if not is_windows and name.endswith(".pyz"):
            return asset
    return info["assets"][0] if info["assets"] else None


def download_asset(asset: dict, dest_dir: str | Path) -> Path | None:
    """Download a release asset to the given directory. Returns the local path or None."""
    url = asset.get("browser_download_url") or asset.get("url")
    name = asset.get("name", "AutoBackup_update")
    dest = Path(dest_dir) / name
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        with urllib.request.urlopen(req, timeout=DOWNLOAD_TIMEOUT) as resp:
            data = resp.read()
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(data)
        return dest
    except Exception:
        return None
