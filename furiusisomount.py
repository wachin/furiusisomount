#!/usr/bin/env python3
import sys
import os
import subprocess
import hashlib
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
                            QPushButton, QComboBox, QLineEdit, QTreeWidget, QTreeWidgetItem,
                            QFileDialog, QMessageBox, QProgressBar, QRadioButton, QGroupBox,
                            QScrollArea, QFrame, QTabWidget)
from PyQt6.QtCore import Qt, QTimer, QUrl, QLocale, QLibraryInfo, QTranslator
from PyQt6.QtGui import QIcon, QFont, QDragEnterEvent, QDropEvent

class FuriusIsoMount(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Furius ISO Mount")
        self.setGeometry(100, 100, 800, 600)

        # Configuración inicial
        self.home_directory = os.path.expanduser('~')
        self.settings_directory = os.path.join(self.home_directory, '.furiusisomount')
        self.mount_log = os.path.join(self.settings_directory, 'FuriusMountLog.txt')
        self.mount_list = os.path.join(self.settings_directory, 'FuriusMountList.csv')
        self.history_list = os.path.join(self.settings_directory, 'FuriusMountHistory.txt')
        self.settings_file = os.path.join(self.settings_directory, 'settings.cfg')

        # Crear directorios si no existen
        self.create_directories()

        # Variables de estado
        self.mounted_images = []
        self.history = []
        self.current_image = ""
        self.current_mount_point = ""
        self.is_fuse = True
        self.is_brasero = True
        self.hash_calculating = False

        # Estado conversión
        self.current_cue_file = ""

        # Inicializar UI
        self.init_ui()

        # Cargar historial
        self.load_history()
        self.load_mounted_images()

        # Configurar drag and drop
        self.setAcceptDrops(True)

    def create_directories(self):
        if not os.path.exists(self.settings_directory):
            os.makedirs(self.settings_directory)
        if not os.path.exists(self.settings_file):
            with open(self.settings_file, 'w') as f:
                f.write('[mount_options]\nmount_point: %s' % self.home_directory)

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Pestañas principales
        tabs = QTabWidget()
        mount_tab = QWidget()
        convert_tab = QWidget()

        # === PESTAÑA DE MONTAJE ===
        mount_layout = QVBoxLayout()

        # Sección de selección de imagen
        image_group = QGroupBox("Seleccionar Imagen")
        image_layout = QHBoxLayout()
        self.image_combo = QComboBox()
        self.image_combo.setEditable(True)
        self.image_combo.addItems(self.history)
        browse_button = QPushButton("Examinar...")
        browse_button.clicked.connect(self.browse_image)
        image_layout.addWidget(QLabel("Imagen:"))
        image_layout.addWidget(self.image_combo, 1)
        image_layout.addWidget(browse_button)
        image_group.setLayout(image_layout)

        # Sección de opciones de montaje
        options_group = QGroupBox("Opciones")
        options_layout = QHBoxLayout()
        self.fuse_radio = QRadioButton("FUSE")
        self.fuse_radio.setChecked(True)
        self.loop_radio = QRadioButton("Loop")
        self.md5_radio = QRadioButton("MD5")
        self.md5_radio.setChecked(True)
        self.sha1_radio = QRadioButton("SHA1")
        options_layout.addWidget(QLabel("Método:"))
        options_layout.addWidget(self.fuse_radio)
        options_layout.addWidget(self.loop_radio)
        options_layout.addStretch()
        options_layout.addWidget(QLabel("Checksum:"))
        options_layout.addWidget(self.md5_radio)
        options_layout.addWidget(self.sha1_radio)
        options_group.setLayout(options_layout)

        # Sección de acciones
        actions_layout = QHBoxLayout()
        self.mount_button = QPushButton("Montar")
        self.mount_button.clicked.connect(self.mount_image)
        self.unmount_button = QPushButton("Desmontar")
        self.unmount_button.clicked.connect(self.unmount_image)
        self.unmount_button.setEnabled(False)
        self.checksum_button = QPushButton("Checksum")
        self.checksum_button.clicked.connect(self.calculate_checksum)
        self.burn_button = QPushButton("Grabar")
        self.burn_button.clicked.connect(self.burn_image)
        actions_layout.addWidget(self.mount_button)
        actions_layout.addWidget(self.unmount_button)
        actions_layout.addWidget(self.checksum_button)
        actions_layout.addWidget(self.burn_button)

        # Barra de progreso para checksum
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setFormat("No hay checksum calculado")

        # Lista de imágenes montadas
        self.mounted_list = QTreeWidget()
        self.mounted_list.setHeaderLabels(["Punto de montaje", "Archivo de imagen", "Método"])
        self.mounted_list.itemSelectionChanged.connect(self.update_selected_mount)

        # Layout principal montaje
        mount_layout.addWidget(image_group)
        mount_layout.addWidget(options_group)
        mount_layout.addLayout(actions_layout)
        mount_layout.addWidget(self.progress_bar)
        mounted_frame = QGroupBox("Imágenes montadas")
        mounted_layout = QVBoxLayout()
        mounted_layout.addWidget(self.mounted_list)
        mounted_frame.setLayout(mounted_layout)
        mount_layout.addWidget(mounted_frame)

        # Botones adicionales
        bottom_layout = QHBoxLayout()
        log_button = QPushButton("Ver Log")
        log_button.clicked.connect(self.view_log)
        delete_log_button = QPushButton("Borrar Log")
        delete_log_button.clicked.connect(self.delete_log)
        about_button = QPushButton("Acerca de")
        about_button.clicked.connect(self.show_about)
        bottom_layout.addWidget(log_button)
        bottom_layout.addWidget(delete_log_button)
        bottom_layout.addStretch()
        bottom_layout.addWidget(about_button)
        mount_layout.addLayout(bottom_layout)

        mount_tab.setLayout(mount_layout)

        # === PESTAÑA DE CONVERSIÓN BIN/CUE → ISO ===
        convert_layout = QVBoxLayout()

        cue_group = QGroupBox("Convertir BIN/CUE a ISO")
        cue_layout = QHBoxLayout()
        self.cue_line = QLineEdit()
        self.cue_line.setPlaceholderText("Selecciona el archivo .cue")
        cue_browse = QPushButton("Examinar...")
        cue_browse.clicked.connect(self.browse_cue)
        cue_layout.addWidget(self.cue_line)
        cue_layout.addWidget(cue_browse)
        cue_group.setLayout(cue_layout)

        # Botón de conversión
        self.convert_button = QPushButton("Convertir a ISO")
        self.convert_button.clicked.connect(self.convert_bin_cue)
        self.convert_button.setStyleSheet("font-weight: bold; color: green;")

        # Barra de progreso de conversión
        self.convert_progress = QProgressBar()
        self.convert_progress.setRange(0, 100)
        self.convert_progress.setFormat("Listo para convertir")

        convert_layout.addWidget(cue_group)
        convert_layout.addWidget(self.convert_button)
        convert_layout.addWidget(self.convert_progress)
        convert_layout.addStretch()

        convert_tab.setLayout(convert_layout)
        # ================================

        tabs.addTab(mount_tab, "Montar Imagen")
        tabs.addTab(convert_tab, "Convertir BIN/CUE")

        layout.addWidget(tabs)

        # Conectar señales
        self.image_combo.currentTextChanged.connect(self.update_current_image)
        self.fuse_radio.toggled.connect(self.update_mount_method)
        self.cue_line.textChanged.connect(self.update_cue_file)

    def update_current_image(self, text):
        self.current_image = text

    def update_mount_method(self, checked):
        self.is_fuse = checked

    def update_cue_file(self, text):
        self.current_cue_file = text.strip()

    def browse_image(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Seleccionar imagen",
                                                  self.home_directory,
                                                  "Imágenes (*.iso *.img *.bin *.mdf *.nrg)")
        if file_path:
            self.image_combo.setCurrentText(file_path)
            self.current_image = file_path

    def browse_cue(self):
        file_dialog = QFileDialog()
        file_path, _ = file_dialog.getOpenFileName(self, "Seleccionar archivo CUE",
                                                  self.home_directory,
                                                  "Archivos CUE (*.cue)")
        if file_path:
            self.cue_line.setText(file_path)
            self.current_cue_file = file_path

    def find_associated_bin(self, cue_path):
        base_dir = os.path.dirname(cue_path)
        cue_filename = os.path.basename(cue_path)
        bin_name = os.path.splitext(cue_filename)[0] + ".bin"
        bin_path = os.path.join(base_dir, bin_name)
        if os.path.exists(bin_path):
            return bin_path

        # Intentar encontrar cualquier .bin en la misma carpeta
        for f in os.listdir(base_dir):
            if f.lower().endswith('.bin'):
                return os.path.join(base_dir, f)

        return None

    def convert_bin_cue(self):
        if not self.current_cue_file or not os.path.exists(self.current_cue_file):
            QMessageBox.warning(self, "Error", "Por favor selecciona un archivo .cue válido")
            return

        bin_path = self.find_associated_bin(self.current_cue_file)
        if not bin_path:
            QMessageBox.critical(self, "Error", "No se encontró el archivo .bin asociado")
            return

        # Destino del ISO
        default_iso = os.path.splitext(os.path.basename(self.current_cue_file))[0] + ".iso"
        iso_path, _ = QFileDialog.getSaveFileName(self, "Guardar ISO como", default_iso, "Imágenes ISO (*.iso)")
        if not iso_path:
            return

        if not iso_path.lower().endswith('.iso'):
            iso_path += '.iso'

        # Directorio base sin extensión
        iso_base = os.path.splitext(iso_path)[0]

        # Comando bchunk
        cmd = ['bchunk', '-v', bin_path, self.current_cue_file, iso_base]

        self.convert_progress.setFormat("Iniciando conversión...")
        self.convert_progress.setValue(0)
        self.convert_button.setEnabled(False)

        try:
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)

            # Simulación de progreso basado en salida de bchunk
            total_tracks = 1  # Podría parsearse del .cue, pero bchunk no da % exacto
            completed = 0

            while True:
                output = process.stdout.readline()
                if output == "" and process.poll() is not None:
                    break
                if output:
                    self.log_message(f"[CONVERT] {output.strip()}")
                    # Buscar progreso (bchunk muestra [****] 100 %)
                    if "%" in output:
                        match = re.search(r"(\d+)%", output)
                        if match:
                            pct = int(match.group(1))
                            self.convert_progress.setValue(pct)
                            self.convert_progress.setFormat(f"Convirtiendo... {pct}%")

            rc = process.poll()
            if rc == 0:
                final_iso = iso_base + "01.iso"  # bchunk añade 01.iso
                if os.path.exists(final_iso):
                    # Mover y renombrar
                    os.rename(final_iso, iso_path)
                    self.convert_progress.setFormat("✅ Conversión completada")
                    self.log_message(f"Conversión exitosa: {iso_path}")
                    QMessageBox.information(self, "Éxito", f"ISO creado:\n{iso_path}")
                    # Añadir al historial y al combo
                    self.add_to_history(iso_path)
                    self.image_combo.setCurrentText(iso_path)
                    self.current_image = iso_path
                else:
                    raise Exception("No se generó el archivo ISO")
            else:
                raise Exception("bchunk falló con código de salida: " + str(rc))

        except Exception as e:
            self.log_message(f"Error en conversión: {str(e)}")
            QMessageBox.critical(self, "Error", f"No se pudo convertir:\n{str(e)}")
            self.convert_progress.setFormat("❌ Error en conversión")
        finally:
            self.convert_button.setEnabled(True)

    def mount_image(self):
        if not self.current_image or not os.path.exists(self.current_image):
            QMessageBox.warning(self, "Error", "Por favor seleccione un archivo de imagen válido")
            return

        image_name = os.path.basename(self.current_image)
        mount_point = os.path.join(self.home_directory, image_name.replace(' ', '_').replace('.', '_'))
        try:
            if os.path.exists(mount_point):
                os.rmdir(mount_point)
            os.mkdir(mount_point)

            if self.is_fuse:
                cmd = f"fuseiso '{self.current_image}' '{mount_point}'"
            else:
                cmd = f"udisksctl loop-setup -f '{self.current_image}' && udisksctl mount -b /dev/loop0"

            result = subprocess.run(cmd, shell=True, check=True)

            # Añadir a la lista de montados
            self.mounted_images.append({
                'mount_point': mount_point,
                'image_file': self.current_image,
                'method': 'FUSE' if self.is_fuse else 'Loop'
            })
            self.add_to_history(self.current_image)
            self.update_mounted_list()
            QMessageBox.information(self, "Éxito", f"Imagen montada en {mount_point}")

        except subprocess.CalledProcessError as e:
            QMessageBox.critical(self, "Error", f"No se pudo montar la imagen: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado: {str(e)}")

    def unmount_image(self):
        if not self.current_mount_point:
            return

        try:
            # Verificar si el directorio está en uso
            result = subprocess.run(['lsof', self.current_mount_point],
                                capture_output=True, text=True)
            if result.returncode == 0:
                # Hay procesos usando el directorio
                QMessageBox.warning(self, "No se puede desmontar",
                                "No se puede desmontar: el directorio está en uso.\n"
                                "Por favor, cierra cualquier ventana del administrador "
                                "de archivos que esté dentro de esta carpeta y vuelve a intentarlo.")
                return

            # Intentar desmontar
            if self.current_mount_method == 'FUSE':
                cmd = ['fusermount', '-u', self.current_mount_point]
            else:
                # Para loop: desmontar y eliminar loop
                dev = self.get_loop_device(self.current_mount_point)
                cmd_unmount = ['udisksctl', 'unmount', '-b', dev] if dev else None
                cmd_delete = ['udisksctl', 'loop-delete', '-b', dev] if dev else None
                if cmd_unmount:
                    subprocess.run(cmd_unmount, check=True)
                if cmd_delete:
                    subprocess.run(cmd_delete, check=True)
                os.rmdir(self.current_mount_point)
                self.mounted_images = [img for img in self.mounted_images
                                    if img['mount_point'] != self.current_mount_point]
                self.update_mounted_list()
                self.current_mount_point = ""
                self.unmount_button.setEnabled(False)
                QMessageBox.information(self, "Éxito", "Imagen desmontada correctamente")
                return

            # Ejecutar fusermount
            subprocess.run(cmd, check=True, capture_output=True)
            os.rmdir(self.current_mount_point)

            # Actualizar estado
            self.mounted_images = [img for img in self.mounted_images
                                if img['mount_point'] != self.current_mount_point]
            self.update_mounted_list()
            self.current_mount_point = ""
            self.unmount_button.setEnabled(False)
            QMessageBox.information(self, "Éxito", "Imagen desmontada correctamente")

        except subprocess.CalledProcessError as e:
            if "Device or resource busy" in str(e) or e.returncode == 1:
                QMessageBox.warning(self, "No se puede desmontar",
                                "No se puede desmontar: el directorio está ocupado.\n"
                                "Cierra cualquier ventana del administrador de archivos "
                                "que esté accediendo a esta carpeta y vuelve a intentarlo.")
            else:
                QMessageBox.critical(self, "Error", f"No se pudo desmontar: {e}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error inesperado: {str(e)}")

    def calculate_checksum(self):
        if not self.current_image or not os.path.exists(self.current_image):
            QMessageBox.warning(self, "Error", "Seleccione un archivo de imagen válido")
            return

        self.hash_calculating = True
        self.checksum_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_bar.setFormat("Calculando...")

        self.hash_timer = QTimer()
        self.hash_timer.timeout.connect(self.update_hash_progress)
        self.hash_timer.start(100)

        hash_obj = hashlib.md5() if self.md5_radio.isChecked() else hashlib.sha1()
        total_size = os.path.getsize(self.current_image)
        chunk_size = 1024 * 1024
        bytes_read = 0

        try:
            with open(self.current_image, 'rb') as f:
                while self.hash_calculating:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    hash_obj.update(chunk)
                    bytes_read += len(chunk)
                    progress = int((bytes_read / total_size) * 100)
                    self.progress_bar.setValue(progress)
                    QApplication.processEvents()

            if self.hash_calculating:
                checksum = hash_obj.hexdigest()
                self.progress_bar.setFormat(f"Checksum: {checksum}")
                self.log_message(f"Checksum calculado para {self.current_image}: {checksum}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error calculando checksum: {str(e)}")
        finally:
            self.hash_calculating = False
            self.checksum_button.setEnabled(True)
            self.hash_timer.stop()

    def get_loop_device(self, mount_point):
        """Obtiene el dispositivo loop asociado a un punto de montaje"""
        try:
            with open('/proc/mounts', 'r') as f:
                for line in f:
                    parts = line.split()
                    if len(parts) >= 2 and parts[1] == mount_point:
                        return parts[0]  # /dev/loopX
        except Exception as e:
            self.log_message(f"Error buscando loop device: {str(e)}")
        return None

    def update_hash_progress(self):
        pass

    def burn_image(self):
        if not self.current_image or not os.path.exists(self.current_image):
            QMessageBox.warning(self, "Error", "Seleccione un archivo de imagen válido")
            return
        try:
            if self.is_brasero:
                cmd = f"brasero --image '{self.current_image}'"
            else:
                cmd = f"wodim dev=/dev/sr0 '{self.current_image}'"
            subprocess.Popen(cmd, shell=True)
            self.log_message(f"Iniciando grabación de {self.current_image}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo iniciar la grabación: {str(e)}")

    def add_to_history(self, image_path):
        if image_path in self.history:
            self.history.remove(image_path)
        self.history.insert(0, image_path)
        self.history = self.history[:10]
        self.image_combo.clear()
        self.image_combo.addItems(self.history)
        try:
            with open(self.history_list, 'w') as f:
                f.write('\n'.join(self.history))
        except Exception as e:
            self.log_message(f"Error guardando historial: {str(e)}")

    def load_history(self):
        try:
            if os.path.exists(self.history_list):
                with open(self.history_list, 'r') as f:
                    self.history = [line.strip() for line in f.readlines()]
        except Exception as e:
            self.log_message(f"Error cargando historial: {str(e)}")

    def load_mounted_images(self):
        try:
            if os.path.exists(self.mount_list):
                with open(self.mount_list, 'r') as f:
                    for line in f.readlines():
                        parts = line.strip().split(',')
                        if len(parts) >= 3:
                            self.mounted_images.append({
                                'mount_point': parts[0],
                                'image_file': parts[1],
                                'method': parts[2]
                            })
                self.update_mounted_list()
        except Exception as e:
            self.log_message(f"Error cargando imágenes montadas: {str(e)}")

    def update_mounted_list(self):
        self.mounted_list.clear()
        for img in self.mounted_images:
            item = QTreeWidgetItem([img['mount_point'], img['image_file'], img['method']])
            self.mounted_list.addTopLevelItem(item)

    def update_selected_mount(self):
        selected = self.mounted_list.selectedItems()
        if selected:
            self.current_mount_point = selected[0].text(0)
            self.current_mount_method = selected[0].text(2)
            self.unmount_button.setEnabled(True)
        else:
            self.current_mount_point = ""
            self.unmount_button.setEnabled(False)

    def view_log(self):
        try:
            if os.path.exists(self.mount_log):
                subprocess.Popen(['xdg-open', self.mount_log])
            else:
                QMessageBox.information(self, "Información", "No hay archivo de log disponible")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo abrir el log: {str(e)}")

    def delete_log(self):
        try:
            if os.path.exists(self.mount_log):
                os.remove(self.mount_log)
                QMessageBox.information(self, "Éxito", "Archivo de log eliminado")
            else:
                QMessageBox.information(self, "Información", "No hay archivo de log para eliminar")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"No se pudo eliminar el log: {str(e)}")

    def show_about(self):
        about_text = """
        <h2>Furius ISO Mount</h2>
        <p>Versión 0.11.3.1</p>
        <p>Una aplicación simple para montar imágenes ISO, IMG, BIN, MDF y NRG sin necesidad de grabarlas a disco.</p>
        <p>Desarrollador original: Dean Harris <marcus_furius@hotmail.com></p>
        <p>Port a PyQt6 por [Tu nombre]</p>
        <p><b>Nueva función:</b> Conversión BIN/CUE → ISO con bchunk</p>
        <p>Licencia GPL v3</p>
        """
        QMessageBox.about(self, "Acerca de Furius ISO Mount", about_text)

    def log_message(self, message):
        try:
            with open(self.mount_log, 'a') as f:
                f.write(f"{message}\n")
        except Exception as e:
            print(f"Error escribiendo en log: {str(e)}")

    # Drag and Drop support
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        if urls and urls[0].isLocalFile():
            file_path = urls[0].toLocalFile()
            ext = file_path.lower()
            if ext.endswith(('.iso', '.img', '.bin', '.mdf', '.nrg')):
                self.image_combo.setCurrentText(file_path)
                self.current_image = file_path
            elif ext.endswith('.cue'):
                self.cue_line.setText(file_path)
                self.current_cue_file = file_path

if __name__ == "__main__":
    app = QApplication(sys.argv)

    # Cargar traducciones del sistema
    translator = QTranslator()
    translations_path = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
    locale = QLocale.system().name()  # ej: es_ES

    # Intentar con qtbase_es.qm (nombre usado en Debian)
    if translator.load(f"qtbase_{locale}", translations_path):
        app.installTranslator(translator)
        print(f"[INFO] Traducción cargada: qtbase_{locale}")
    elif locale.startswith("es") and translator.load("qtbase_es", translations_path):
        app.installTranslator(translator)
        print("[INFO] Traducción en español cargada (qtbase_es)")
    else:
        print("[INFO] No se pudo cargar la traducción del sistema.")

    window = FuriusIsoMount()
    window.show()
    sys.exit(app.exec())
