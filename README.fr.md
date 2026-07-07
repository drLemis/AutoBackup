# AutoBackup

[English](README.md) | **Français**

AutoBackup surveille silencieusement le dossier où vous travaillez et enregistre des copies de sauvegarde datées lorsque vous sauvegardez un fichier. Si Photoshop, Word ou un autre programme écrase le même fichier encore et encore, vous conservez les dernières versions dans un dossier séparé.

## Téléchargement

[![Télécharger ici !](https://img.shields.io/badge/Télécharger-ici!-2ea44f?style=for-the-badge)](https://github.com/drLemis/AutoBackup/releases/latest)

**[Télécharger ici !](https://github.com/drLemis/AutoBackup/releases/latest)**

1. Cliquez sur le lien ci-dessus (ou le bouton vert).
2. Choisissez le fichier pour votre système (Windows `.exe`, Linux binary ou macOS `.zip`).
3. Lancez-le. Rien à installer.

[![License: NWSL](https://img.shields.io/badge/license-NWSL-orange)](LICENSE)

---

## Prérequis

- Windows 10+, Linux (bureau) ou macOS
- Un **dossier de travail** (vos projets)
- Un **dossier de sauvegarde** à un endroit différent - pas dans le dossier de travail (par exemple un disque externe ou `D:\Sauvegardes`)

---

## Démarrage rapide

1. Ouvrez AutoBackup.
2. Cliquez sur **Parcourir...** à côté de **Dossier de travail** et choisissez votre dossier.
3. Cliquez sur **Parcourir...** à côté de **Dossier de sauvegarde** et choisissez la destination.
4. Cliquez sur **DÉMARRER** et laissez la fenêtre ouverte.
5. Pour voir vos copies, cliquez sur **Ouvrir les sauvegardes**.

La ligne sous les boutons indique ce qui se passe : arrêté, surveillance ou copie d'un fichier.

**Couleurs du bouton**

| Couleur | Signification |
|---------|---------------|
| Gris | Arrêté |
| Vert | Surveillance active - sauvegardes automatiques |
| Orange | Copie d'un fichier en cours |

---

## Ce qui se passe lors de la sauvegarde

- Quand vous appuyez sur **DÉMARRER**, AutoBackup note quels fichiers sont déjà présents. **Seuls les fichiers modifiés après** sont sauvegardés - pas toute votre bibliothèque d'un coup.
- Après la sauvegarde d'un fichier, AutoBackup attend un instant, puis enregistre une copie avec la date et l'heure dans le nom, ex. : `MyDrawing_20260526_143022.psd`
- Les sous-dossiers de votre dossier de travail sont reproduits à l'identique dans le dossier de sauvegarde.
- Si vous sauvegardez le même fichier sans réelles modifications, AutoBackup ne crée pas de copie supplémentaire.
- Les fichiers temporaires, caches (`.git`, `node_modules`, `__pycache__`) et fichiers système (Thumbs.db, etc.) sont automatiquement exclus.
- Définissez le nombre de copies à conserver par fichier avec le compteur **Garder copies** (1–100).

---

## Pause et reprise

- Cliquez sur **PAUSE** pour arrêter temporairement la surveillance - la liste des fichiers reste en mémoire, aucun nouveau scan au moment de la reprise.
- Cliquez sur **REPRENDRE** pour continuer instantanément.
- Utilisez la pause lorsque vous effectuez une série de sauvegardes que vous ne souhaitez pas encore archiver.

---

## Récupérer une ancienne version

AutoBackup ne modifie jamais vos fichiers de travail par lui-même.

- Cliquez sur **Restaurer...** pour parcourir toutes vos versions de sauvegarde avec recherche, dates et tailles de fichiers.
- Sélectionnez un fichier et cliquez sur **Restaurer vers...** pour le sauvegarder dans votre dossier de travail (ou ailleurs).
- Ou cliquez sur **Ouvrir** pour prévisualiser une sauvegarde sans la restaurer.

---

## Bon à savoir

- Laissez AutoBackup ouvert pendant votre travail - le fermer arrête la protection.
- Le dossier de sauvegarde ne doit **pas** se trouver dans le dossier de travail.
- L'application détecte automatiquement la langue de Windows (arabe, hébreu, russe) ou vous pouvez changer à tout moment via le menu des langues (en bas à droite).
- Cochez **Démarrer avec Windows** pour lancer AutoBackup automatiquement à l'ouverture de session.
- Cochez **Son** pour entendre un signal discret lors d'une sauvegarde (désactivé par défaut).
- La taille du dossier de sauvegarde est affichée à côté du compteur de copies.
- C'est un outil d'appoint pour vos fichiers de projet. Il ne remplace pas les sauvegardes complètes du PC, le stockage cloud ou les logiciels de sauvegarde professionnels.

---

## Licence

**Nuclear Waste Software License v1.0 (NWSL)** - [lire la licence](LICENSE)

Copyright (c) 2026 drLemis.

---


