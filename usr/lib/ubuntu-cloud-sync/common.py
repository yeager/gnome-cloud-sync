# SPDX-License-Identifier: GPL-3.0-or-later
"""Shared paths and engine status for the GTK app and Nautilus."""
import json
import os
from pathlib import Path
from tempfile import NamedTemporaryFile

from i18n import _, format_time

PROVIDERS = {"onedrive": "OneDrive", "google": "Google Drive", "icloud": "iCloud Drive"}
BASE = Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "ubuntu-cloud-sync"


def folder(provider):
    return Path.home() / "Cloud Sync" / PROVIDERS[provider]


def state(provider):
    return BASE / provider


def read_json(path):
    try:
        data = json.loads(path.read_text())
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def write_private(path, value):
    with NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        try:
            handle.write(value)
            handle.flush()
            os.replace(handle.name, path)
        finally:
            Path(handle.name).unlink(missing_ok=True)


def status(provider):
    directory = state(provider)
    if not (directory / "ready").is_file():
        return None, _("Complete setup to start syncing.")
    local = folder(provider)
    if not local.is_dir() or local.is_symlink() or local.parent.is_symlink():
        return "dialog-warning", _("Sync folder is missing or has been replaced.")
    if provider != "onedrive":
        return fallback_status(directory)
    info = read_json(directory / "monitor-status.json")
    process = info.get("process", {})
    sync = info.get("sync", {})
    pid = info.get("pid")
    if (info.get("schema_version") != 1 or type(pid) is not int
            or not Path(f"/proc/{pid}").exists()):
        return fallback_status(directory)
    if process.get("state") == "syncing":
        return "emblem-synchronizing", _("Syncing with OneDrive…")
    if process.get("state") == "degraded":
        result = sync.get("last_cycle", {}).get("result", "unknown").replace("_", " ")
        return "dialog-warning", _("OneDrive needs attention ({result}).").format(result=_(result))
    if process.get("state") == "idle" and sync.get("last_cycle", {}).get("result") == "success":
        return "emblem-default", _("Last successful sync: {timestamp}").format(
            timestamp=format_time(sync.get("last_successful_sync_at")))
    return None, _("Waiting for first sync.")


def fallback_status(directory):
    info = read_json(directory / "status.json")
    phase = info.get("state")
    pid = info.get("pid")
    if phase == "running" and (type(pid) is not int or not Path(f"/proc/{pid}").exists()):
        return "dialog-warning", _("The last sync was interrupted.")
    badge = {"running": "emblem-synchronizing", "success": "emblem-default",
             "error": "dialog-warning", "paused": "media-playback-pause"}.get(phase)
    message = _(info.get("message", "Waiting for first sync."))
    if info.get("timestamp"):
        message = message.format(timestamp=format_time(info["timestamp"]))
    return badge, message
