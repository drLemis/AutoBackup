"""Lightweight UI strings: English + Windows UI language (ru when available)."""
import json
import sys
from pathlib import Path

_STRINGS: dict = {}
_LANG = "en"

# Autonym labels for the language menu (add an entry when adding strings/xx.json).
# Order here determines language display order in the UI.
LANG_LABELS = {
    "en": "English",
    "de": "Deutsch",
    "fr": "Français",
    "es": "Español",
    "pt": "Português",
    "ar": "العربية",
    "ru": "Русский",
    "ua": "Українська",
    "he": "עברית",
    "zh": "中文",
    "ja": "日本語",
    "ko": "한국어",
    "br": "Português (BR)",
}

RTL_LANGS = {"ar", "he"}

LANG_ORDER = list(LANG_LABELS.keys())


def is_rtl(lang: str = "") -> bool:
    return (lang or _LANG) in RTL_LANGS


def _strings_dir() -> Path:
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "strings"
    return Path(__file__).resolve().parent / "strings"


def discover_langs() -> tuple[str, ...]:
    base = _strings_dir()
    if not base.is_dir():
        return ("en",)
    available = {p.stem for p in base.glob("*.json") if p.stem}
    ordered = [c for c in LANG_ORDER if c in available]
    return tuple(ordered) if ordered else ("en",)


def lang_label(code: str) -> str:
    return LANG_LABELS.get(code, code)


def detect_lang() -> str:
    if sys.platform != "win32":
        return "en"
    try:
        import ctypes
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        primary = lang_id & 0x3FF
        if primary == 0x19:  # Russian
            return "ru"
        if primary == 0x01:  # Arabic
            return "ar"
        if primary == 0x0D:  # Hebrew
            return "he"
    except Exception:
        pass
    return "en"


def current_lang() -> str:
    return _LANG


def set_locale(lang: str) -> str:
    global _STRINGS, _LANG
    available = discover_langs()
    if lang not in available:
        lang = "en" if "en" in available else available[0]
    path = _strings_dir() / f"{lang}.json"
    if not path.is_file():
        path = _strings_dir() / "en.json"
        lang = "en"
    if path.is_file():
        with open(path, encoding="utf-8") as f:
            _STRINGS = json.load(f)
        _LANG = lang
    else:
        _STRINGS = {}
        _LANG = "en"
    return _LANG


def init_locale(saved_lang: str = "") -> str:
    """Use saved manual choice, otherwise auto-detect from Windows UI language."""
    available = discover_langs()
    if saved_lang in available:
        return set_locale(saved_lang)
    detected = detect_lang()
    if detected in available:
        return set_locale(detected)
    return set_locale("en" if "en" in available else available[0])


def t(key: str, **kwargs) -> str:
    text = _STRINGS.get(key, key)
    if kwargs:
        try:
            return text.format(**kwargs)
        except (KeyError, ValueError):
            return text
    return text


def help_text(max_versions: int) -> str:
    body = t("help.body", max_versions=max_versions)
    return f"{body}\n\n{t('help.copyright')}"
