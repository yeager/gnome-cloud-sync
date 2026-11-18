# GNOME Cloud Sync

An independent prototype for the GNOME desktop.

An experimental GTK 4 control panel and Nautilus extension for OneDrive, Google
Drive, and iCloud Drive. Each provider has its own settings, credentials, local
folder, and systemd user unit. Test with disposable data before using real files.
Two-way sync propagates edits and deletions.

## Install and run

From the directory with the package:

```sh
sudo apt install ./ubuntu-cloud-sync_0.4.1_all.deb
nautilus -q
ubuntu-cloud-sync
```

Reopen GNOME Files after quitting it to load the extension. If the backend packages
are absent, install `onedrive`, `rclone`, and a terminal emulator. Use [OneDrive Client for Linux 2.5.12 or newer](https://github.com/abraunegg/onedrive/blob/master/docs/ubuntu-package-install.md), and a current rclone build with the iCloud Drive backend. Some Ubuntu builds
omit that backend. Run `rclone help backend iclouddrive` to check. If it is
missing, install the current Linux .deb from [rclone downloads](https://rclone.org/downloads/).

## OneDrive

Choose OneDrive and click Sign in. Complete Microsoft sign-in in the browser.
The client returns the result to the app automatically. Click Start sync when ready. The isolated profile syncs the account's default drive to
`~/Cloud Sync/OneDrive`. Use a test account. This prototype has no folder picker
or account switching.

## Google Drive and iCloud Drive

1. Select the provider and click Configure rclone remote. In the terminal, create
   a remote named `google` of type `drive`, or `icloud` of type `iclouddrive`
   with its default Drive service. Complete the engine's own sign-in prompts and
   exit the config menu. Leave config-file encryption off for this prototype.
2. In the provider's web UI, create a dedicated top-level test folder. Put an empty
   file named `RCLONE_TEST` and at least one disposable plain file at that folder's
   top level. Leave the marker in place on both sides after setup.
3. Enter the exact cloud folder name in GTK and click Start sync. The local folder
   must start empty. rclone performs an initial bisync and then runs approximately
   every five minutes. Google Docs, Sheets, and Slides are excluded. iCloud uses
   the Drive backend with Apple two-factor authentication and periodic reconnects.
   Consult rclone's limitations for your account and Advanced Data Protection settings.

## Status and recovery

Open `~/Cloud Sync` in GNOME Files. Emblems on the provider folders show a running
pass, a successful last pass, or a problem. A check mark describes the last
successful pass and is not confirmation of the current state of individual files.
Right-click a provider folder and select Cloud Sync Status to open the GTK app.
OneDrive uses the monitor JSON when available and recognizes status lines from
older client builds as a fallback.

Start sync enables the monitor or timer for future desktop sessions. Pause stops
the OneDrive monitor or disables scheduled rclone runs. An active rclone pass
finishes before the pause takes full effect. If bisync stops and requires recovery,
the prototype never automatically runs another baseline sync. Review both copies
and the engine's recovery docs first.

```sh
journalctl --user -u ubuntu-cloud-sync@onedrive.service -n 50
journalctl --user -u ubuntu-cloud-sync@google.service -n 50
journalctl --user -u ubuntu-cloud-sync@icloud.service -n 50
```

The application uses a separate profile under
`${XDG_CONFIG_HOME:-$HOME/.config}/ubuntu-cloud-sync`. It does not import or
change your existing client settings. Avoid pointing any other sync process at
these same local folders. Your cloud engine manages its credentials in the
provider profile. Pause all providers in the window before uninstalling.

## Upstream documentation

- https://github.com/abraunegg/onedrive/blob/master/docs/usage.md
- https://rclone.org/drive/
- https://rclone.org/iclouddrive/
- https://rclone.org/bisync/

## GNOME Online Accounts

The OneDrive and Google Drive views can open an existing GNOME cloud volume in
Files and link to Online Accounts settings. Add Microsoft 365 or Google there
and enable Files to make a volume available. Offline sync still uses its own
engine sign-in. GNOME Online Accounts has no iCloud Drive provider.

## License

GNOME Cloud Sync is licensed under GPL-3.0-or-later. See `COPYING`.

## iPhone USB import

Connect and unlock an iPhone with a USB data cable. Tap **Trust** on the phone
if prompted. Open **Import from iPhone** in GNOME Cloud Sync, choose the
device and a local destination folder, then start the import.

The importer copies photos and videos exposed under the phone's DCIM folder.
If a destination already contains a file with the same name and contents,
it is skipped. A different file with the same name is preserved alongside it.
Choose a local folder on a filesystem that supports hard links, such as ext4,
so finished files can be created without overwriting existing files.
If iCloud Photos uses Optimize Storage, some originals may first need to be
downloaded to the phone. USB import leaves the files on the phone intact.
