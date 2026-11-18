# SPDX-License-Identifier: GPL-3.0-or-later
"""Display the latest folder-level engine state in GNOME Files."""
import sys

from gi.repository import Gio, GLib, GObject, Nautilus

sys.path.insert(0, "/usr/lib/ubuntu-cloud-sync")
from i18n import _
from common import PROVIDERS, folder, status


class UbuntuCloudSync(GObject.GObject, Nautilus.InfoProvider, Nautilus.MenuProvider):
    def __init__(self):
        super().__init__()
        self.items = {}
        self.badges = {}
        GLib.timeout_add_seconds(2, self.refresh)

    @staticmethod
    def provider(file):
        path = file.get_location().get_path()
        return next((name for name in PROVIDERS if str(folder(name)) == path), None)

    def update_file_info(self, file):
        provider = self.provider(file)
        if provider:
            self.items[provider] = file
            badge, _ = status(provider)
            self.badges[provider] = badge
            if badge:
                file.add_emblem(badge)
        return Nautilus.OperationResult.COMPLETE

    def refresh(self):
        for provider, file in list(self.items.items()):
            badge, _ = status(provider)
            if self.badges.get(provider) != badge:
                self.badges[provider] = badge
                file.invalidate_extension_info()
        return GLib.SOURCE_CONTINUE

    def get_file_items(self, files):
        if len(files) != 1 or not self.provider(files[0]):
            return []
        item = Nautilus.MenuItem(name="UbuntuCloudSync::status", label=_("Cloud Sync Status"),
                                 tip=_("Open GNOME Cloud Sync"))
        item.connect("activate", lambda *_: Gio.AppInfo.create_from_commandline(
            "ubuntu-cloud-sync", None, Gio.AppInfoCreateFlags.NONE).launch([], None))
        return [item]
