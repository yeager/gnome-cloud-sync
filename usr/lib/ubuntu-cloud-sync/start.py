# SPDX-License-Identifier: GPL-3.0-or-later
"""Sequence service activation off the GTK event loop."""
import subprocess
import sys

systemctl = ["systemctl", "--user"]
provider, *command = sys.argv[1:]
subprocess.run(systemctl + ["daemon-reload"], check=True)
subprocess.run(systemctl + command, check=True)
if provider != "onedrive":
    subprocess.run(systemctl + ["start", f"ubuntu-cloud-sync@{provider}.service"], check=True)
