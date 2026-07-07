# AutoBackup

[English](README.md) | **Deutsch**

AutoBackup überwacht leise den Ordner, in dem Sie arbeiten, und speichert datierte Sicherungskopien, wenn Sie eine Datei speichern. Wenn Photoshop, Word oder ein anderes Programm dieselbe Datei immer wieder überschreibt, bleiben die letzten Versionen in einem separaten Ordner erhalten.

## Download

[![Download hier!](https://img.shields.io/badge/Download-hier!-2ea44f?style=for-the-badge)](https://github.com/drLemis/AutoBackup/releases/latest)

**[Download hier!](https://github.com/drLemis/AutoBackup/releases/latest)**

1. Klicken Sie den Link oben (oder den grünen Button).
2. Wählen Sie die Datei für Ihr System (Windows `.exe`, Linux Binary oder macOS `.zip`).
3. Ausführen. Keine Installation nötig.

[![License: NWSL](https://img.shields.io/badge/license-NWSL-orange)](LICENSE)

---

## Voraussetzungen

- Windows 10+, Linux (Desktop) oder macOS
- Ein **Arbeitsordner** (Ihre Projekte)
- Ein **Sicherungsordner** an einem anderen Ort - nicht im Arbeitsordner (z. B. eine externe Festplatte oder `D:\Backups`)

---

## Schnellstart

1. Öffnen Sie AutoBackup.
2. Klicken Sie neben **Arbeitsordner** auf **Durchsuchen...** und wählen Sie Ihren Projektordner.
3. Klicken Sie neben **Sicherungsordner** auf **Durchsuchen...** und wählen Sie das Ziel für Kopien.
4. Klicken Sie auf **START** und lassen Sie das Fenster geöffnet.
5. Unter **Sicherungen öffnen** sehen Sie Ihre Kopien.

Die Zeile unter den Schaltflächen zeigt den Status: gestoppt, überwache oder kopiere Datei.

**Farben der Schaltfläche**

| Farbe | Bedeutung |
|-------|-----------|
| Grau | Gestoppt |
| Grün | Überwachung läuft - Sicherungen erfolgen automatisch |
| Orange | Kopiere gerade eine Datei |

---

## Was beim Speichern passiert

- Wenn Sie **START** drücken, merkt sich AutoBackup, welche Dateien bereits vorhanden sind. **Nur Dateien, die Sie danach ändern**, werden gesichert - nicht Ihr gesamter Ordner auf einmal.
- Nach dem Speichern einer Datei wartet AutoBackup kurz und speichert dann eine Kopie mit Datum und Uhrzeit im Namen, z. B.: `MyDrawing_20260526_143022.psd`
- Unterordner innerhalb Ihres Arbeitsordners werden genauso im Sicherungsordner abgebildet.
- Wenn Sie dieselbe Datei erneut ohne Änderungen speichern, überspringt AutoBackup die Kopie.
- Temporäre Dateien, Caches (`.git`, `node_modules`, `__pycache__`) und Systemmüll (Thumbs.db usw.) werden automatisch ausgeschlossen.
- Stellen Sie mit dem Zählfeld **Kopien behalten** (1–100) ein, wie viele Kopien pro Datei aufbewahrt werden.

---

## Pause und Fortsetzen

- Klicken Sie **PAUSE**, um die Überwachung vorübergehend zu stoppen - die Dateiliste bleibt im Speicher, kein erneutes Scannen beim Fortsetzen.
- Klicken Sie **WEITER**, um die Überwachung sofort fortzusetzen.
- Nutzen Sie die Pause, wenn Sie viele Dateien speichern, die noch nicht gesichert werden sollen.

---

## Alte Version wiederherstellen

AutoBackup ändert niemals Ihre Arbeitsdateien von sich aus.

- Klicken Sie **Wiederherstellen...**, um alle Sicherungsversionen mit Suche, Datum und Dateigröße zu durchsuchen.
- Wählen Sie eine Datei und klicken Sie **Wiederherstellen nach...**, um sie zurück in Ihren Arbeitsordner (oder an einen beliebigen Ort) zu speichern.
- Oder klicken Sie **Öffnen**, um eine Kopie anzusehen, ohne sie wiederherzustellen.

---

## Wissenswertes

- Lassen Sie AutoBackup während der Arbeit geöffnet - Schließen beendet den Schutz.
- Der Sicherungsordner darf **nicht** innerhalb des Arbeitsordners liegen.
- Die App erkennt Ihre Windows-Sprache automatisch (Arabisch, Hebräisch, Russisch) oder Sie wechseln jederzeit über das Sprachmenü (unten rechts).
- Aktivieren Sie **Mit Windows starten**, um AutoBackup automatisch beim Anmelden zu starten.
- Aktivieren Sie **Ton**, um einen dezenten Signalton bei abgeschlossener Sicherung zu hören (standardmäßig aus).
- Die Größe des Sicherungsordners wird neben dem Kopien-Zählfeld angezeigt.
- Dies ist ein Helfer für Ihre Projektdateien. Es ersetzt keine vollständige PC-Sicherung, Cloud-Speicher oder professionelle Backup-Software.

---

## Lizenz

**Nuclear Waste Software License v1.0 (NWSL)** - [Lizenz lesen](LICENSE)

Copyright (c) 2026 drLemis.

---


