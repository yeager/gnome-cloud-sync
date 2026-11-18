# GNOME Cloud Sync

En fristående prototyp för GNOME-skrivbordet.

En prototyp med ett GTK-fönster och statusmärken i GNOME Filer. Varje leverantör har en egen lokal mapp och en egen bakgrundstjänst. Börja med testfiler. Tvåvägssynkronisering kan sprida borttagningar.

## Installera och öppna

Bygg paketet med `./build-package.sh .` (kräver `gettext` och `dpkg-deb`).

Kör följande i mappen där installationspaketet finns.

```sh
sudo apt install ./ubuntu-cloud-sync_0.4.2_all.deb
nautilus -q
ubuntu-cloud-sync
```

Öppna GNOME Filer igen. Programmet följer skrivbordets språk. Om du vill prova det svenska gränssnittet direkt kan du starta programmet med `LANGUAGE=sv ubuntu-cloud-sync` efter att ha stängt det.

Kontrollera iCloud-stödet med `rclone help backend iclouddrive`. Om kommandot säger att stödet saknas, installera det aktuella Linux-paketet från [rclones nedladdningssida](https://rclone.org/downloads/).

## Anslut en tjänst

- **OneDrive.** Välj Logga in och slutför Microsofts inloggning i webbläsaren. Resultatet skickas automatiskt tillbaka till appen. Välj sedan Starta synkronisering. Flödet kräver [OneDrive Client for Linux 2.5.12 eller senare](https://github.com/abraunegg/onedrive/blob/master/docs/ubuntu-package-install.md). Prototypen synkroniserar kontots standardenhet. Använd ett testkonto.
- **Google Drive.** Välj Konfigurera molnanslutning i rclone. Skapa en anslutning med namnet `google` och typen `drive`. Slutför inloggningen och stäng konfigurationsmenyn. Dokument som skapats i Google Dokument, Kalkylark eller Presentationer ingår inte.
- **iCloud Drive.** Skapa en rclone-anslutning med namnet `icloud` och typen `iclouddrive`. Behåll standardtjänsten Drive. Slutför Apples tvåfaktorsinloggning. Du kan behöva ansluta på nytt när Apples session löper ut.

För Google Drive och iCloud Drive skapar du en separat testmapp direkt under molnlagringens rot. Lägg en tom fil med namnet `RCLONE_TEST` och en testfil som du kan avvara i mappen. Ange mappens exakta namn i GTK och välj Starta synkronisering. Den lokala mappen måste vara tom vid första körningen. Låt markörfilen ligga kvar på båda sidor.

## Se status eller pausa

Öppna `~/Cloud Sync` i GNOME Filer. Statusmärkena visar om en synkronisering pågår, om den senaste körningen lyckades eller om ett problem behöver åtgärdas. Högerklicka på en leverantörsmapp och välj **Status för molnsynkronisering** för att öppna appen.

**Pausa** stoppar OneDrive-övervakningen eller stänger av schemalagda rclone-körningar. En pågående rclone-körning får slutföras. Vid problem ger tjänstloggen mer information.

```sh
journalctl --user -u ubuntu-cloud-sync@onedrive.service -n 50
journalctl --user -u ubuntu-cloud-sync@google.service -n 50
journalctl --user -u ubuntu-cloud-sync@icloud.service -n 50
```

Se den engelska [installationsguiden](README.md) för mer om återställning och inställningar.

## GNOME Nätkonton

I vyerna för OneDrive och Google Drive kan du öppna ett befintligt nätkonto i
Filer eller gå till inställningarna för nätkonton. Lägg till Microsoft 365 eller
Google där och aktivera Filer. Lokal synkronisering använder fortfarande en
separat inloggning. GNOME Nätkonton har inget stöd för iCloud Drive.

## Licens

GNOME Cloud Sync omfattas av GPL-3.0-or-later. Se `COPYING`.

För USB-import från iPhone, se [den separata appen](https://github.com/yeager/iphone-import/blob/main/README.sv.md).
