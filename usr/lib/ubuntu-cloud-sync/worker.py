#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run exactly one engine for a configured provider."""
import json
import os
import os
import signal
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

from common import PROVIDERS, folder, state, write_private


def publish(directory, phase, message, **details):
    write_private(directory / "status.json", json.dumps({"state": phase, "message": message, "pid": os.getpid(), **details}))


def run(provider):
    directory = state(provider)
    local = folder(provider)
    if not (directory / "ready").is_file() or not local.is_dir() or local.is_symlink() or local.parent.is_symlink():
        raise RuntimeError("The configured local folder is missing.")
    if str(local.stat().st_ino) != (directory / "ready").read_text().strip():
        raise RuntimeError("The configured local folder was replaced.")
    if provider == "onedrive":
        status_file = directory / "monitor-status.json"
        status_file.unlink(missing_ok=True)
        try:
            publish(directory, "running", "Starting the OneDrive monitor…")
            with subprocess.Popen(
                    ["onedrive", "--confdir", str(directory), "--monitor", "--verbose"],
                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                    errors="replace") as monitor:
                for line in monitor.stdout:
                    print(line, end="", flush=True)
                    message = line.strip()
                    if message == "Sync with Microsoft OneDrive is complete":
                        publish(directory, "success", "Last successful sync: {timestamp}", timestamp=timestamp())
                    elif message.startswith("Sync with Microsoft OneDrive has completed, however"):
                        publish(directory, "error", "Some OneDrive transfers failed. See the service journal.")
                    elif message.startswith(("Syncing changes and items from OneDrive",
                                             "Fetching items from the OneDrive API")):
                        publish(directory, "running", "Syncing with OneDrive…")
                code = monitor.wait()
            if code:
                publish(directory, "error", "OneDrive stopped with an error. See the service journal.")
            else:
                publish(directory, "paused", "OneDrive monitor stopped.")
            return code
        finally:
            status_file.unlink(missing_ok=True)
    remote = (directory / "remote").read_text().strip()
    args = ["rclone", "--config", str(directory / "rclone.conf")]
    flags = ["--drive-skip-gdocs"] if provider == "google" else []
    command = args + ["bisync", str(local), remote, "--workdir", str(directory / "bisync"),
                      "--check-access", "--max-delete", "25", "--create-empty-src-dirs",
                      "--conflict-resolve", "none"] + flags
    if not (directory / "initialized").exists():
        if (directory / "initial-attempt").exists():
            raise RuntimeError("Initial sync was interrupted. Review the journal before recovering.")
        if any(local.iterdir()):
            raise RuntimeError("Initial sync requires an empty local folder.")
        contents = subprocess.check_output(args + ["lsf", remote, "--files-only"] + flags,
                                           text=True, timeout=60).splitlines()
        if "RCLONE_TEST" not in contents or len(contents) < 2:
            raise RuntimeError("Add RCLONE_TEST and a test file to the selected remote folder.")
        # The cutoff protects initial sync as well as recurring runs against a wrong path.
        (local / "RCLONE_TEST").touch(exist_ok=False)
        write_private(directory / "initial-attempt", "started\n")
        command.append("--resync")
    publish(directory, "running", "Syncing…")
    subprocess.run(command, check=True)
    write_private(directory / "initialized", "yes\n")
    publish(directory, "success", "Last successful sync: {timestamp}", timestamp=timestamp())
    return 0


def timestamp():
    return datetime.now(timezone.utc).isoformat()


def interrupted(_signal, _frame):
    raise InterruptedError("Sync interrupted.")


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, interrupted)
    provider = sys.argv[1]
    if provider not in PROVIDERS:
        sys.exit(2)
    try:
        sys.exit(run(provider))
    except InterruptedError:
        publish(state(provider), "paused" if provider == "onedrive" else "error",
                "OneDrive monitor stopped." if provider == "onedrive" else "Sync interrupted.")
        sys.exit(0 if provider == "onedrive" else 1)
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as error:
        print(error, file=sys.stderr)
        if state(provider).is_dir():
            message = str(error) if isinstance(error, RuntimeError) else "Sync failed. See the service journal."
            publish(state(provider), "error", message)
        sys.exit(1)
