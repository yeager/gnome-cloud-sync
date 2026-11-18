#!/usr/bin/python3
# SPDX-License-Identifier: GPL-3.0-or-later
"""GTK setup for the three independently managed sync folders."""
import configparser
import re
import shutil
import subprocess
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
from gi.repository import Gio, GLib, Gtk

from i18n import _ as translate
from iphone import ImportWindow
from common import PROVIDERS, folder, state, status, write_private

def launch(uri):
    Gio.AppInfo.launch_default_for_uri(uri, None)


class Setup(Gtk.ApplicationWindow):
    def __init__(self, app):
        super().__init__(application=app, title="GNOME Cloud Sync", default_width=600)
        self.auth = None
        self.iphone_window = None
        self.job = None
        self.notice = ""
        self.volumes = Gio.VolumeMonitor.get()
        self.online_drives = []
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        for edge in ("top", "bottom", "start", "end"):
            getattr(panel, f"set_margin_{edge}")(24)
        self.set_child(panel)

        self.providers = Gtk.DropDown.new_from_strings(list(PROVIDERS.values()))
        panel.append(self.providers)
        self.location = Gtk.Label(xalign=0, selectable=True, wrap=True)
        panel.append(self.location)
        self.instructions = Gtk.Label(xalign=0, wrap=True)
        panel.append(self.instructions)
        self.entry = Gtk.Entry()
        panel.append(self.entry)
        self.connect_button = self.button(panel, translate("Sign in"), self.connect_provider)
        self.cancel = self.button(panel, translate("Cancel sign-in"), self.cancel_auth)
        self.controls = Gtk.Box(spacing=8)
        panel.append(self.controls)
        self.start = self.button(self.controls, translate("Start sync"), self.start_sync)
        self.pause = self.button(self.controls, translate("Pause"), self.pause_sync)
        self.open = self.button(self.controls, translate("Open folder"), self.open_folder)
        self.message = Gtk.Label(xalign=0, wrap=True, selectable=True)
        panel.append(self.message)
        self.online = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        panel.append(self.online)
        self.online.append(Gtk.Label(
            label=translate("GNOME Online Accounts opens cloud files in Files. Local sync uses its own sign-in."),
            xalign=0, wrap=True))
        self.accounts = Gtk.DropDown.new_from_strings([])
        self.online.append(self.accounts)
        online_actions = Gtk.Box(spacing=8)
        self.online.append(online_actions)
        self.browse_online = self.button(online_actions, translate("Browse cloud files"), self.open_online)
        self.button(online_actions, translate("Online Accounts settings"), self.open_online_settings)
        self.button(panel, translate("Import from iPhone"), self.open_iphone_import)
        self.providers.connect("notify::selected", self.change_provider)
        self.connect("close-request", self.close_window)
        self.change_provider()
        GLib.timeout_add(700, self.refresh)

    @staticmethod
    def button(box, title, callback):
        button = Gtk.Button(label=title)
        box.append(button)
        button.connect("clicked", callback)
        return button

    @property
    def provider(self):
        return list(PROVIDERS)[self.providers.get_selected()]

    def change_provider(self, *_):
        self.notice = ""
        self.entry.set_text("")
        self.entry.set_placeholder_text(translate("Cloud folder name, e.g. Ubuntu Sync Test"))
        self.refresh()

    def open_iphone_import(self, *_):
        if self.iphone_window is None:
            self.iphone_window = ImportWindow(self)
        self.iphone_window.refresh_devices()
        self.iphone_window.present()

    def close_window(self, *_):
        if self.iphone_window and self.iphone_window.cancellable:
            self.iphone_window.present()
            return True
        if self.auth:
            self.cancel_auth()
        return False

    def refresh(self):
        provider = self.provider
        directory = state(provider)
        ready = (directory / "ready").is_file()
        authenticated = (directory / "refresh_token").is_file()
        engine = "onedrive" if provider == "onedrive" else "rclone"
        available = shutil.which(engine) is not None
        self.providers.set_sensitive(not (self.auth or self.job))
        self.location.set_text(str(folder(provider)))
        self.refresh_online(provider)
        self.cancel.set_visible(bool(self.auth))
        self.open.set_sensitive(folder(provider).is_dir())
        self.entry.set_visible(provider != "onedrive" and not ready)
        self.connect_button.set_visible((provider != "onedrive" and not ready)
                                        or (not authenticated and not ready and not self.auth))
        self.connect_button.set_sensitive(available)
        self.start.set_sensitive(available and not self.job and not self.auth
                                 and (provider != "onedrive" or authenticated or ready))
        self.pause.set_sensitive(ready and not self.job)
        if ready:
            instructions = translate("Files added here sync in both directions. Deletions can sync too.")
        elif provider == "onedrive":
            instructions = translate("Sign in with Microsoft in your browser. Return here when sign-in is complete.")
        else:
            instructions = translate("Configure rclone, then enter the name of a dedicated cloud folder. Put an empty RCLONE_TEST file and one disposable test file in it before starting.")
        self.instructions.set_text(instructions)
        self.connect_button.set_label(translate("Configure rclone remote") if provider != "onedrive" else translate("Sign in"))
        if self.auth:
            self.poll_auth()
        if self.job:
            code = self.job.poll()
            if code is not None:
                self.job = None
                self.notice = (translate("Request sent to systemd.") if code == 0 else
                               translate("Service command failed. See the user service journal."))
        _, detail = status(provider)
        if provider == "onedrive" and authenticated and not ready:
            detail = translate("Signed in. Select Start sync when ready.")
        if not available:
            detail = translate("Install {engine} to enable this provider.").format(engine=engine)
        self.message.set_text("\n".join(filter(None, [self.notice, detail])))
        return GLib.SOURCE_CONTINUE

    def refresh_online(self, provider):
        scheme = {"onedrive": "onedrive", "google": "google-drive"}.get(provider)
        self.online.set_visible(scheme is not None)
        drives = []
        if scheme:
            for volume in self.volumes.get_volumes():
                root = volume.get_activation_root()
                if root is not None and root.get_uri_scheme() == scheme:
                    drives.append((volume.get_name(), root.get_uri()))
        drives.sort()
        if drives != self.online_drives:
            self.online_drives = drives
            self.accounts.set_model(Gtk.StringList.new([name for name, _ in drives]))
        self.accounts.set_visible(bool(drives))
        self.browse_online.set_sensitive(bool(drives))

    def open_online(self, *_):
        index = self.accounts.get_selected()
        if index < len(self.online_drives):
            try:
                subprocess.Popen(["nautilus", self.online_drives[index][1]])
            except OSError as error:
                self.notice = str(error)
                self.refresh()

    def open_online_settings(self, *_):
        try:
            subprocess.Popen(["gnome-control-center", "online-accounts"])
        except OSError as error:
            self.notice = str(error)
            self.refresh()

    def connect_provider(self, *_):
        directory = state(self.provider)
        try:
            directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.provider != "onedrive":
                subprocess.Popen(["x-terminal-emulator", "-e", "rclone", "--config",
                                  str(directory / "rclone.conf"), "config"], umask=0o077)
                self.notice = translate("Create a remote named {provider} in the terminal.").format(provider=self.provider)
            elif not self.auth:
                self.auth = subprocess.Popen(
                    ["onedrive", "--confdir", str(directory)],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL, umask=0o077)
                self.notice = translate("Waiting for Microsoft sign-in…")
        except (OSError, ValueError) as error:
            self.notice = str(error)
        self.refresh()

    def poll_auth(self):
        if self.auth.poll() is None:
            return
        self.auth = None
        authenticated = (state(self.provider) / "refresh_token").is_file()
        self.notice = (translate("Microsoft account connected.") if authenticated else
                       translate("Microsoft sign-in failed. Start a fresh sign-in and retry."))

    def cancel_auth(self, *_):
        if self.auth and self.auth.poll() is None:
            self.auth.terminate()
            try:
                self.auth.wait(timeout=0.25)
            except subprocess.TimeoutExpired:
                self.auth.kill()
                self.auth.wait()
        self.auth = None
        self.notice = ""

    def start_sync(self, *_):
        provider = self.provider
        directory = state(provider)
        local = folder(provider)
        try:
            if not (directory / "ready").exists():
                if local.parent.is_symlink() or local.is_symlink():
                    raise ValueError(translate("Use a regular local Cloud Sync folder."))
                local.mkdir(parents=True, exist_ok=True)
                if any(local.iterdir()):
                    raise ValueError(translate("Initial setup requires an empty local folder."))
                if provider == "onedrive":
                    escaped = str(local).replace("\\", "\\\\").replace('"', '\\"')
                    write_private(directory / "config", f'sync_dir = "{escaped}"\n')
                else:
                    name = self.entry.get_text().strip()
                    if not re.fullmatch(r"[\w .-]+", name) or name in {".", ".."}:
                        raise ValueError(translate("Enter one top-level cloud folder name."))
                    config = configparser.ConfigParser(interpolation=None)
                    config.read(directory / "rclone.conf")
                    backend = "drive" if provider == "google" else "iclouddrive"
                    if config.get(provider, "type", fallback="") != backend or (
                            provider == "icloud" and config.get(provider, "service", fallback="drive") != "drive"):
                        raise ValueError(translate("Create a {backend} remote named {provider} first.").format(backend=backend, provider=provider))
                    write_private(directory / "remote", f"{provider}:{name}\n")
                write_private(directory / "ready", f"{local.stat().st_ino}\n")
            service = f"ubuntu-cloud-sync@{provider}.service"
            if provider == "onedrive":
                command = ["enable", "--now", service]
            else:
                command = ["enable", "--now", f"ubuntu-cloud-sync@{provider}.timer", "--no-block"]
            self.job = subprocess.Popen(
                ["/usr/bin/python3", str(Path(__file__).with_name("start.py")), provider, *command])
            self.notice = translate("Starting sync…")
        except (OSError, ValueError, subprocess.SubprocessError, configparser.Error) as error:
            self.notice = str(error)
        self.refresh()

    def pause_sync(self, *_):
        provider = self.provider
        service = f"ubuntu-cloud-sync@{provider}.service"
        if provider == "onedrive":
            args = ["disable", "--now", service]
        else:
            args = ["disable", "--now", f"ubuntu-cloud-sync@{provider}.timer"]
        try:
            self.job = subprocess.Popen(["systemctl", "--user", *args])
            self.notice = (translate("Pausing sync…") if provider == "onedrive" else
                           translate("Pausing scheduled sync. Any active pass will finish."))
        except OSError as error:
            self.notice = str(error)
        self.refresh()

    def open_folder(self, *_):
        try:
            launch(folder(self.provider).as_uri())
        except GLib.Error as error:
            self.notice = str(error)
            self.refresh()


app = Gtk.Application(application_id="org.example.UbuntuCloudSync")
app.connect("activate", lambda application: (
    application.get_active_window() or Setup(application)).present())
app.run()
