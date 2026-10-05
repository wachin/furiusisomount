# Furius ISO Mount

Aplicación sencilla (PyQt6) para **montar imágenes de disco** (ISO, IMG, BIN, MDF y NRG)
sin necesidad de grabarlas, con herramientas extra: checksum MD5/SHA1, grabación de
imágenes y conversión **BIN/CUE → ISO**.

*A simple PyQt6 application to mount ISO/IMG/BIN/MDF/NRG disc images without burning
them, with MD5/SHA1 checksums, image burning and BIN/CUE → ISO conversion.*

---

## Acerca de

| | |
|---|---|
| **Versión** | 0.11.3.1 |
| **Autor original** | Dean Harris &lt;marcus_furius@hotmail.com&gt; |
| **Fork PyQt6 y modular** | Washington Indacochea Delgado |
| **Correo** | [linuxfrontier@proton.me](mailto:linuxfrontier@proton.me) |
| **Sitio web** | <https://github.com/wachin/furiusisomount> |
| **Licencia** | GPL v3 |
| **Tecnologías** | Python 3, PyQt6, fuseiso, udisks2, bchunk, brasero/wodim |

El proyecto original (<https://github.com/prachpub/furiusisomount>) fue abandonado hace
años; este fork lo moderniza: **arquitectura modular**, **interfaz multilenguaje**
(Qt Linguist), correcciones de bugs y un diálogo *Acerca de* renovado.

## Requisitos

```bash
# Debian / Ubuntu
sudo apt install python3-pyqt6 fuseiso bchunk udisks2 brasero lsof
# Fedora
sudo dnf install python3-qt6 fuseiso bchunk udisks2 brasero lsof
```

## Ejecutar

```bash
python3 main.py
```

Idioma forzado (opcional):

```bash
FURIUSISOMOUNT_LANG=es python3 main.py
```

## Estructura del proyecto

```
furiusisomount/
├── main.py                    # punto de entrada
├── furiusisomount/            # paquete principal
│   ├── app_info.py            # metadatos (versión, créditos, licencia)
│   ├── paths.py               # rutas de configuración/recursos
│   ├── i18n.py                # carga de traducciones (Qt Linguist)
│   ├── core/                  # lógica independiente de la interfaz
│   │   ├── mounts.py          # montar/desmontar (FUSE y loop/udisks2)
│   │   ├── checksum.py        # MD5/SHA1 con progreso y cancelación
│   │   ├── converter.py       # BIN/CUE → ISO (bchunk)
│   │   ├── burner.py          # grabación (brasero/wodim)
│   │   └── history.py         # historial, lista de montajes y registro
│   └── ui/                    # interfaz PyQt6
│       ├── main_window.py     # ventana principal (pestañas + drag&drop)
│       ├── mount_tab.py       # pestaña "Montar imagen"
│       ├── convert_tab.py     # pestaña "Convertir BIN/CUE"
│       ├── about_dialog.py    # diálogo "Acerca de"
│       └── workers.py         # hilos de trabajo (checksum/conversión)
├── resources/icons/           # icono del programa
├── translations/              # archivos .ts / .qm de Qt Linguist
├── scripts/update_translations.sh
├── data/furiusisomount.desktop
└── tests/test_core.py         # pruebas de la lógica (sin GUI)
```

## Multilenguaje (Qt Linguist)

El idioma base es el **inglés**: todas las cadenas usan `self.tr("...")` y se extraen
automáticamente.

```bash
# 1. Extraer cadenas y crear/actualizar los .ts (por defecto: es y fr)
./scripts/update_translations.sh
LANGS="es fr pt de" ./scripts/update_translations.sh

# 2. Traducir con Qt Linguist
linguist translations/furiusisomount_pt.ts

# 3. Compilar a .qm (lo hace el script si encuentra lrelease)
./scripts/update_translations.sh
```

Idiomas incluidos: **inglés** (código fuente) más **español, francés, portugués,
alemán, italiano, japonés, ruso y chino simplificado** (todos completos, 81/81
cadenas, en `.ts` y `.qm`).

En tiempo de ejecución se carga `furiusisomount_<locale>.qm` según el idioma del
sistema (o `FURIUSISOMOUNT_LANG`), junto a las traducciones estándar de Qt
(botones de los diálogos del sistema).

## Correcciones respecto a la versión original

- **`re` no estaba importado** pero se usaba al parsear la salida de `bchunk`
  (error en tiempo de ejecución al convertir).
- **Cálculo de checksum en el hilo principal** congelaba la interfaz: ahora corre en
  un `QThread`, con barra de progreso real y botón de **cancelar**.
- **Conversión BIN/CUE bloqueante** (leía la salida del proceso en el hilo GUI):
  también movida a un hilo, con progreso real.
- **Dispositivo loop hardcodeado** (`/dev/loop0`): ahora se detecta el que asigna
  `udisksctl` y se registra su punto de montaje real.
- **Comandos con `shell=True`** y comillas manuales: sustituidos por listas de
  argumentos (sin problemas de espacios ni inyección de comandos).
- **Salida de `bchunk` supuesta** (`base01.iso`): se descubre con `glob` y se limpian
  pistas sobrantes.
- **`fusermount3`** soportado (con retrocompatibilidad con `fusermount`).
- **Selección del desplegable se perdía** al añadir elementos al historial; ahora se
  preserva (y no emite señales espurias).
- **Punto de montaje duplicado** si ya existía el directorio: ahora genera nombres
  únicos y saneados.
- **Ciclo de vida de los hilos** al cerrar la aplicación (apagado ordenado).
- **Configuración (`settings.cfg`) sin usar**: ahora define la carpeta base de montaje.

## Instalación (opcional)

```bash
# Icono y acceso directo de escritorio
sudo cp resources/icons/furiusisomount.png /usr/share/icons/hicolor/256x256/apps/
sudo cp data/furiusisomount.desktop /usr/share/applications/
# Traducciones compiladas
sudo mkdir -p /usr/share/furiusisomount/translations
sudo cp translations/*.qm /usr/share/furiusisomount/translations/
```

## Licencia

GNU General Public License v3 (GPL v3).
