# AutoBackup

[English](README.md) | **Español**

AutoBackup vigila silenciosamente la carpeta donde trabajas y guarda copias de seguridad con fecha cuando guardas un archivo. Si Photoshop, Word u otro programa sobrescribe el mismo archivo una y otra vez, las últimas versiones se conservan en una carpeta separada.

## Descargar

[![¡Descargar aquí!](https://img.shields.io/badge/Descargar-aquí!-2ea44f?style=for-the-badge)](https://github.com/drLemis/AutoBackup/releases/latest)

**[¡Descargar aquí!](https://github.com/drLemis/AutoBackup/releases/latest)**

1. Haz clic en el enlace de arriba (o el botón verde).
2. Elige el archivo para tu sistema (Windows `.exe`, Linux binary o macOS `.zip`).
3. Ejecútalo. No requiere instalación.

[![License: NWSL](https://img.shields.io/badge/license-NWSL-orange)](LICENSE)

---

## Requisitos

- Windows 10+, Linux (escritorio) o macOS
- Una **carpeta de trabajo** (tus proyectos)
- Una **carpeta de respaldo** en una ubicación diferente - no dentro de la carpeta de trabajo (por ejemplo, un disco externo o `D:\Respaldo`)

---

## Inicio rápido

1. Abre AutoBackup.
2. Haz clic en **Examinar...** junto a **Carpeta de trabajo** y selecciona tu carpeta.
3. Haz clic en **Examinar...** junto a **Carpeta de respaldo** y elige el destino.
4. Haz clic en **INICIAR** y deja la ventana abierta.
5. Para ver tus copias, haz clic en **Abrir respaldos**.

La línea debajo de los botones indica lo que está sucediendo: detenido, vigilando o copiando un archivo.

**Colores del botón**

| Color | Significado |
|-------|-------------|
| Gris | Detenido |
| Verde | Vigilando - respaldos automáticos |
| Naranja | Copiando un archivo ahora |

---

## Qué sucede al guardar

- Cuando presionas **INICIAR**, AutoBackup registra qué archivos ya existen. **Solo los archivos que modifiques después** se respaldan - no toda tu biblioteca de una vez.
- Después de guardar un archivo, AutoBackup espera un momento y luego guarda una copia con fecha y hora en el nombre, ej.: `MyDrawing_20260526_143022.psd`
- Las subcarpetas dentro de tu carpeta de trabajo se replican igual en la carpeta de respaldo.
- Si guardas el mismo archivo de nuevo sin cambios reales, AutoBackup omite crear otra copia.
- Archivos temporales, cachés (`.git`, `node_modules`, `__pycache__`) y basura del sistema (Thumbs.db, etc.) se excluyen automáticamente.
- Configura cuántas copias conservar por archivo con el selector **Guardar copias** (1–100).

---

## Pausa y reanudación

- Haz clic en **PAUSA** para detener la vigilancia temporalmente - la lista de archivos se mantiene en memoria, sin necesidad de reescanear al reanudar.
- Haz clic en **REANUDAR** para continuar al instante.
- Usa la pausa cuando hagas muchas guardadas que aún no quieras respaldar.

---

## Recuperar una versión anterior

AutoBackup nunca modifica tus archivos de trabajo por sí mismo.

- Haz clic en **Restaurar...** para explorar todas tus versiones de respaldo con búsqueda, fechas y tamaños.
- Selecciona un archivo y haz clic en **Restaurar en...** para guardarlo en tu carpeta de trabajo (o donde elijas).
- O haz clic en **Abrir** para previsualizar un respaldo sin restaurarlo.

---

## Bueno saber

- Mantén AutoBackup abierto mientras trabajas - cerrarlo detiene la protección.
- La carpeta de respaldo **no** debe estar dentro de la carpeta de trabajo.
- La app detecta automáticamente el idioma de Windows (árabe, hebreo, ruso) o puedes cambiarlo desde el menú de idiomas (abajo a la derecha).
- Marca **Iniciar con Windows** para que AutoBackup se lance automáticamente al iniciar sesión.
- Marca **Sonido** para oír un chime sutil cuando se complete un respaldo (desactivado por defecto).
- El tamaño de la carpeta de respaldo se muestra junto al selector de copias.
- Es una ayuda para tus archivos de proyecto. No reemplaza las copias de seguridad completas del PC, el almacenamiento en la nube ni el software de respaldo profesional.

---

## Licencia

**Nuclear Waste Software License v1.0 (NWSL)** - [leer licencia](LICENSE)

Copyright (c) 2026 drLemis.

---


