import os
import subprocess
import json
import cv2
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QFileDialog, QMessageBox, QComboBox, QSpinBox, QTabWidget, QMainWindow, QAction
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QImage, QPainter, QColor, QPen

# Configuration file path
CONFIG_FILE = r"Configs\Cc.json"
# Ensure Configs folder exists
os.makedirs("Configs", exist_ok=True)


class PreviewLabel(QLabel):
    """Custom QLabel for displaying preview image/video with interactive crop box."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.crop_x = 0
        self.crop_y = 0
        self.crop_w = 100
        self.crop_h = 100
        self.dragging = False
        self.drag_start_pos = None
        self.setMouseTracking(True)

    def set_crop_box(self, x, y, w, h):
        """Update crop box dimensions and repaint overlay."""
        self.crop_x = x
        self.crop_y = y
        self.crop_w = w
        self.crop_h = h
        self.update()  # Trigger repaint

    def paintEvent(self, event):
        """Draw the red crop rectangle over the preview."""
        super().paintEvent(event)
        painter = QPainter(self)
        pen = QPen(Qt.red, 2, Qt.SolidLine)
        painter.setPen(pen)
        painter.drawRect(self.crop_x, self.crop_y, self.crop_w, self.crop_h)

    def mousePressEvent(self, event):
        """Enable dragging if mouse pressed inside crop box."""
        if event.button() == Qt.LeftButton:
            if self.is_inside_crop_box(event.pos()):
                self.dragging = True
                self.drag_start_pos = event.pos()

    def mouseMoveEvent(self, event):
        """Update crop box position while dragging."""
        if self.dragging and self.drag_start_pos:
            dx = event.x() - self.drag_start_pos.x()
            dy = event.y() - self.drag_start_pos.y()
            self.crop_x += dx
            self.crop_y += dy
            # Prevent crop box from going out of preview bounds
            self.crop_x = max(0, min(self.crop_x, self.width() - self.crop_w))
            self.crop_y = max(0, min(self.crop_y, self.height() - self.crop_h))
            self.drag_start_pos = event.pos()
            self.update()
            if self.main_window:
                self.main_window.update_offsets_from_drag(self.crop_x, self.crop_y)

    def mouseReleaseEvent(self, event):
        """Stop dragging when mouse released."""
        if event.button() == Qt.LeftButton:
            self.dragging = False

    def is_inside_crop_box(self, pos):
        """Check if a position is inside the crop box."""
        return (self.crop_x <= pos.x() <= self.crop_x + self.crop_w and
                self.crop_y <= pos.y() <= self.crop_y + self.crop_h)


class MediaCropperApp(QMainWindow):
    """Main application window for cropping images and videos."""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Media Cropper App")
        self.export_dir = os.getcwd()  # Default export directory
        self.last_ratio = "16:9"
        self.last_offset_x = 0
        self.last_offset_y = 0

        # Load previous configuration if available
        self.load_config()

        # Initialize menu and main UI
        self.init_menu()
        self.init_ui()

        # Timer for updating video preview frames
        self.video_timer = QTimer()
        self.video_timer.timeout.connect(self.update_video_frame)
        self.current_video_path = None
        self.cap = None  # OpenCV VideoCapture object

    def init_menu(self):
        """Create the top menu bar with file actions."""
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")

        # Import single file
        import_action = QAction("Import File", self)
        import_action.triggered.connect(self.import_file)
        file_menu.addAction(import_action)

        # Change export directory
        change_dir_action = QAction("Change Export Directory", self)
        change_dir_action.triggered.connect(self.change_export_dir)
        file_menu.addAction(change_dir_action)

        # Exit application
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def init_ui(self):
        """Initialize main UI layout with preview, file list, and controls."""
        central_widget = QWidget()
        self.original_image_size = None
        self.original_video_size = None
        self.setCentralWidget(central_widget)

        self.tabs = QTabWidget()
        self.crop_tab = QWidget()
        self.tabs.addTab(self.crop_tab, "Cropper")

        # Preview display
        self.preview_label = PreviewLabel(self)
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFixedSize(640, 360)

        # File list
        self.file_list = QListWidget()
        self.file_list.currentTextChanged.connect(self.on_file_selected)

        # Buttons
        self.select_button = QPushButton("Select Folder")
        self.select_button.clicked.connect(self.select_folder)
        self.export_button = QPushButton("Export Crop")
        self.export_button.clicked.connect(self.export_crop)

        # Aspect ratio selection
        self.aspect_ratio = QComboBox()
        self.aspect_ratio.addItems(["1:1", "1:2", "2:1", "2:3", "3:2", "3:5", "5:3", "9:16", "16:9"])
        self.aspect_ratio.setCurrentText(self.last_ratio)

        # Offset controls
        self.offset_x = QSpinBox()
        self.offset_y = QSpinBox()
        self.offset_x.setMaximum(10000)
        self.offset_y.setMaximum(10000)
        self.offset_x.setValue(self.last_offset_x)
        self.offset_y.setValue(self.last_offset_y)
        self.offset_x.valueChanged.connect(self.trigger_crop_overlay_update)
        self.offset_y.valueChanged.connect(self.trigger_crop_overlay_update)
        self.aspect_ratio.currentIndexChanged.connect(self.trigger_crop_overlay_update)

        # Layout controls horizontally
        controls = QHBoxLayout()
        controls.addWidget(self.select_button)
        controls.addWidget(QLabel("Aspect Ratio:"))
        controls.addWidget(self.aspect_ratio)
        controls.addWidget(QLabel("Offset X:"))
        controls.addWidget(self.offset_x)
        controls.addWidget(QLabel("Offset Y:"))
        controls.addWidget(self.offset_y)
        controls.addWidget(self.export_button)

        # Layout vertically
        layout = QVBoxLayout()
        layout.addWidget(self.preview_label)
        layout.addLayout(controls)
        layout.addWidget(self.file_list)
        self.crop_tab.setLayout(layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.tabs)
        central_widget.setLayout(main_layout)

    def select_folder(self):
        """Open dialog to select a folder and populate file list."""
        try:
            folder = QFileDialog.getExistingDirectory(self, "Select Folder")
            if folder:
                self.file_list.clear()
                for fname in os.listdir(folder):
                    if fname.lower().endswith((".png", ".jpg", ".jpeg", ".mp4", ".mov", ".mkv")):
                        self.file_list.addItem(os.path.join(folder, fname))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to select folder:\n{e}")

    def import_file(self):
        """Import a single file to the file list."""
        try:
            file, _ = QFileDialog.getOpenFileName(self, "Import File", "", "Media Files (*.png *.jpg *.jpeg *.mp4 *.mov *.mkv)")
            if file:
                self.file_list.addItem(file)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to import file:\n{e}")

    def change_export_dir(self):
        """Open dialog to select export directory."""
        try:
            new_dir = QFileDialog.getExistingDirectory(self, "Select Export Directory")
            if new_dir:
                self.export_dir = new_dir
                self.save_config()
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to change export directory:\n{e}")

    def on_file_selected(self, path):
        """Handle selection of a file from the list."""
        try:
            if path.lower().endswith((".mp4", ".mov", ".mkv")):
                self.preview_video(path)
            else:
                self.show_image_preview(path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to preview file:\n{e}")

    def show_image_preview(self, path):
        """Display image preview and update crop overlay."""
        try:
            if self.cap:
                self.cap.release()
                self.cap = None
                self.video_timer.stop()
            image = cv2.imread(path)
            if image is None:
                QMessageBox.warning(self, "Error", f"Could not open image: {path}")
                return
            self.original_image_size = (image.shape[1], image.shape[0])
            frame = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            height, width, _ = frame.shape
            qimage = QImage(frame.data, width, height, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)
            scaled_pixmap = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio)
            self.preview_label.setPixmap(scaled_pixmap)
            self.scaled_pixmap_size = (scaled_pixmap.width(), scaled_pixmap.height())
            self.update_crop_box_overlay(*self.scaled_pixmap_size)
            self.current_video_path = None
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to display image preview:\n{e}")

    # Video preview, crop updates, export, etc., all wrapped in try/except similarly
    def preview_video(self, path):
        """Open video file and start preview using QTimer."""
        try:
            if self.cap:
                self.cap.release()
            self.cap = cv2.VideoCapture(path)
            if not self.cap.isOpened():
                QMessageBox.warning(self, "Error", f"Could not open video: {path}")
                return

            # Store original video resolution
            self.original_video_size = (
                int(self.cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(self.cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
            self.current_video_path = path
            self.video_timer.start(33)  # ~30 FPS
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to preview video:\n{e}")

    def update_video_frame(self):
        """Read next frame from video and update preview."""
        try:
            if not self.cap:
                return
            ret, frame = self.cap.read()
            if not ret:
                # Loop back to start
                self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                return
            rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            h, w, _ = rgb_frame.shape
            qimage = QImage(rgb_frame.data, w, h, QImage.Format_RGB888)
            pixmap = QPixmap.fromImage(qimage)
            scaled_pixmap = pixmap.scaled(self.preview_label.size(), Qt.KeepAspectRatio)
            self.preview_label.setPixmap(scaled_pixmap)
            self.scaled_pixmap_size = (scaled_pixmap.width(), scaled_pixmap.height())
            self.update_crop_box_overlay(*self.scaled_pixmap_size)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update video frame:\n{e}")

    def update_crop_box_overlay(self, img_w, img_h):
        """Calculate and display crop box overlay according to aspect ratio and offsets."""
        try:
            original_size = self.original_image_size or self.original_video_size
            if not original_size:
                return
            original_w, original_h = original_size
            offset_x = self.offset_x.value()
            offset_y = self.offset_y.value()
            scale = self.aspect_ratio.currentText()
            rw, rh = map(int, scale.split(":")) if ":" in scale else (1, 1)
            target_ratio = rw / rh

            # Determine display dimensions
            display_w = self.preview_label.width()
            display_h = self.preview_label.height()
            if original_w / original_h > display_w / display_h:
                scaled_w = display_w
                scaled_h = int(display_w * original_h / original_w)
            else:
                scaled_h = display_h
                scaled_w = int(display_h * original_w / original_h)
            self.scaled_pixmap_size = (scaled_w, scaled_h)

            # Center the preview
            x_offset = (display_w - scaled_w) // 2
            y_offset = (display_h - scaled_h) // 2

            # Calculate crop box dimensions
            if scaled_w / scaled_h > target_ratio:
                crop_h = scaled_h
                crop_w = int(crop_h * target_ratio)
            else:
                crop_w = scaled_w
                crop_h = int(crop_w / target_ratio)

            # Apply offset
            scaled_x = int((offset_x / original_w) * scaled_w)
            scaled_y = int((offset_y / original_h) * scaled_h)
            crop_x = x_offset + min(scaled_x, scaled_w - crop_w)
            crop_y = y_offset + min(scaled_y, scaled_h - crop_h)

            self.preview_label.set_crop_box(crop_x, crop_y, crop_w, crop_h)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update crop box overlay:\n{e}")

    def trigger_crop_overlay_update(self):
        """Update crop overlay based on current preview image/video."""
        try:
            pixmap = self.preview_label.pixmap()
            if pixmap:
                self.update_crop_box_overlay(pixmap.width(), pixmap.height())
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to trigger crop overlay update:\n{e}")

    def update_offsets_from_drag(self, crop_x, crop_y):
        """Update X/Y offsets based on drag of crop box in preview."""
        try:
            original_size = self.original_image_size or self.original_video_size
            if not self.scaled_pixmap_size or not original_size:
                return
            scaled_w, scaled_h = self.scaled_pixmap_size
            original_w, original_h = original_size
            display_w = self.preview_label.width()
            display_h = self.preview_label.height()
            x_offset = (display_w - scaled_w) // 2
            y_offset = (display_h - scaled_h) // 2
            rel_x = crop_x - x_offset
            rel_y = crop_y - y_offset
            img_x = int((rel_x / scaled_w) * original_w)
            img_y = int((rel_y / scaled_h) * original_h)
            self.offset_x.setValue(img_x)
            self.offset_y.setValue(img_y)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to update offsets from drag:\n{e}")

    def export_crop(self):
        """Export the currently selected crop for image or video."""
        try:
            item = self.file_list.currentItem()
            if not item:
                QMessageBox.warning(self, "No file selected", "Please select a file first.")
                return
            path = item.text()
            self.save_config()
            if path.lower().endswith((".mp4", ".mov", ".mkv")):
                self.export_video_crop(path)
            else:
                self.export_image_crop(path)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export crop:\n{e}")

    def export_image_crop(self, path):
        """Crop and save an image according to current settings."""
        try:
            crop_x, crop_y = self.offset_x.value(), self.offset_y.value()
            scale = self.aspect_ratio.currentText()
            image = cv2.imread(path)
            if image is None:
                QMessageBox.warning(self, "Error", f"Could not open image: {path}")
                return
            h, w, _ = image.shape
            rw, rh = map(int, scale.split(":")) if ":" in scale else (1, 1)
            crop_w = min(w, int(h * rw / rh))
            crop_h = min(h, int(w * rh / rw))
            cropped = image[crop_y:crop_y + crop_h, crop_x:crop_x + crop_w]
            if cropped.size == 0:
                QMessageBox.warning(self, "Error", "Crop area is empty or invalid.")
                return
            filename = os.path.basename(path)
            output_path = os.path.join(self.export_dir, f"cropped_{filename}")
            cv2.imwrite(output_path, cropped)
            QMessageBox.information(self, "Success", f"Image saved to:\n{output_path}")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export image crop:\n{e}")

    def export_video_crop(self, path):
        """Crop and save a video using ffmpeg with GPU acceleration if available."""
        try:
            crop_x, crop_y = self.offset_x.value(), self.offset_y.value()
            scale = self.aspect_ratio.currentText()
            w, h = self.get_crop_dimensions(path, scale)
            filename = os.path.basename(path)
            output_path = os.path.join(self.export_dir, f"cropped_{filename}")
            ffmpeg_cmd = [
                'ffmpeg', '-y', '-hwaccel', 'cuda', '-i', path,
                '-filter:v', f'crop={w}:{h}:{crop_x}:{crop_y}',
                '-c:v', 'hevc_nvenc', '-preset', 'p7', '-rc', 'vbr_hq',
                '-cq', '19', '-b:v', '0', '-c:a', 'aac', '-b:a', '256k', output_path
            ]
            subprocess.run(ffmpeg_cmd, check=True)
            QMessageBox.information(self, "Success", f"Saved to:\n{output_path}")
        except subprocess.CalledProcessError as e:
            QMessageBox.warning(self, "FFmpeg Error", str(e))
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to export video crop:\n{e}")

    def get_crop_dimensions(self, path, scale):
        """Calculate crop width/height for video based on aspect ratio."""
        try:
            cap = cv2.VideoCapture(path)
            w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            cap.release()
            rw, rh = map(int, scale.split(":")) if ":" in scale else (1, 1)
            new_w = int(h * rw / rh)
            new_h = int(w * rh / rw)
            return min(new_w, w), min(new_h, h)
        except Exception:
            return w, h  # Fallback to original dimensions

    def load_config(self):
        """Load saved configuration from JSON file."""
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.export_dir = config.get("export_dir", self.export_dir)
                    self.last_ratio = config.get("aspect_ratio", self.last_ratio)
                    self.last_offset_x = config.get("offset_x", 0)
                    self.last_offset_y = config.get("offset_y", 0)
            except Exception:
                # Ignore errors, fallback to defaults
                pass

    def save_config(self):
        """Save current configuration to JSON file."""
        try:
            config = {
                "export_dir": self.export_dir,
                "aspect_ratio": self.aspect_ratio.currentText(),
                "offset_x": self.offset_x.value(),
                "offset_y": self.offset_y.value(),
            }
            with open(CONFIG_FILE, 'w') as f:
                json.dump(config, f, indent=4)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to save configuration:\n{e}")


if __name__ == '__main__':
    try:
        app = QApplication([])
        window = MediaCropperApp()
        window.show()
        app.exec_()
    except Exception as e:
        QMessageBox.critical(None, "Fatal Error", f"Application failed:\n{e}")