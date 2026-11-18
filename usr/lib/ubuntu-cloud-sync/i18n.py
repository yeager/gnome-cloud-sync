# SPDX-License-Identifier: GPL-3.0-or-later
"""Resolve UI translations from desktop locale settings."""
import gettext
import locale
from datetime import datetime
from pathlib import Path

locale.setlocale(locale.LC_TIME, "")
locale_dir = Path(__file__).resolve().parents[2] / "share/locale"
_ = gettext.translation("ubuntu-cloud-sync", localedir=locale_dir, fallback=True).gettext


def format_time(value):
    if not value:
        return ""
    try:
        return datetime.fromisoformat(value).astimezone().strftime("%x %X %Z")
    except ValueError:
        return value
