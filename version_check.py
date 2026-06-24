"""Check GitHub releases for a newer AutoBackup version."""
import json
import re
import urllib.request

GITHUB_REPO = "drLemis/AutoBackup"
API_URL = f"https://api.github.com/repos/{GITHUB_REPO}/releases/latest"
RELEASE_URL = f"https://github.com/{GITHUB_REPO}/releases/latest"
CHECK_TIMEOUT = 8
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
        return {"level": level, "version": version, "url": url}
    except Exception:
        return None
