import getpass
from pathlib import Path

from PySide6 import QtCore, QtGui, QtWidgets
from shiboken6 import wrapInstance

from playblast_publisher import maya_utils, versioning

RESOLUTIONS = {
    "1920x1080": (1920, 1080),
    "1280x720": (1280, 720),
    "960x540": (960, 540),
}

class PublisherDialog(QtWidgets.QDialog):
    """Playblast Publisher window."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Playblast Publisher")
        self.setMinimumWidth(420)
        self.settings = QtCore.QSettings("PlayblastPublisher", "PlayblastPublisher")
        
        self.build_widgets()
        self.fill_in_values()
        self.connect_signals()
        self.update_preview()
        
    def build_widgets(self):
        self.root_edit = QtWidgets.QLineEdit()
        self.browse_button = QtWidgets.QPushButton("Browse...")
        root_row = QtWidgets.QHBoxLayout()  # H = horizontal
        root_row.addWidget(self.root_edit)
        root_row.addWidget(self.browse_button)
        
        self.shot_edit = QtWidgets.QLineEdit()
        self.shot_edit.setPlaceholderText("sh010")
        
        self.dept_combo = QtWidgets.QComboBox()
        self.dept_combo.addItems(versioning.DEPARTMENTS)
        
        self.camera_combo = QtWidgets.QComboBox()
        
        # frames
        self.start_spin = QtWidgets.QSpinBox()
        self.end_spin = QtWidgets.QSpinBox()
        self.start_spin.setRange(-100000, 100000)
        self.end_spin.setRange(-100000, 100000)
        self.timeline_button = QtWidgets.QPushButton("From timeline")
        frames_row = QtWidgets.QHBoxLayout()
        frames_row.addWidget(self.start_spin)
        frames_row.addWidget(QtWidgets.QLabel("to"))
        frames_row.addWidget(self.end_spin)
        frames_row.addWidget(self.timeline_button)
        
        self.res_combo = QtWidgets.QComboBox()
        self.res_combo.addItems(RESOLUTIONS.keys())
        
        self.format_combo = QtWidgets.QComboBox()
        
        self.notes_edit = QtWidgets.QPlainTextEdit()
        self.notes_edit.setPlaceholderText("What changed in this version?")
        self.notes_edit.setFixedHeight(70)
        
        form = QtWidgets.QFormLayout()
        form.addRow("Publish root", root_row)
        form.addRow("Shot", self.shot_edit)
        form.addRow("Department", self.dept_combo)
        form.addRow("Camera", self.camera_combo)
        form.addRow("Frames", frames_row)
        form.addRow("Resolution", self.res_combo)
        form.addRow("Format", self.format_combo)
        form.addRow("Notes", self.notes_edit)
        
        self.preview_label = QtWidgets.QLabel()
        self.cancel_button = QtWidgets.QPushButton("Cancel")
        self.publish_button = QtWidgets.QPushButton("Publish")
        bottom_row = QtWidgets.QHBoxLayout()
        bottom_row.addWidget(self.preview_label, stretch=1)
        bottom_row.addWidget(self.cancel_button)
        bottom_row.addWidget(self.publish_button)
        
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.addLayout(form)
        main_layout.addLayout(bottom_row)
    
    def fill_in_values(self):
        default_root = str(Path.home() / "playblasts")
        self.root_edit.setText(self.settings.value("publish_root", default_root))
        self.shot_edit.setText(versioning.guess_shot(maya_utils.scene_path()))
        self.camera_combo.addItems(maya_utils.list_cameras())
        
        self.format_combo.addItem("PNG Sequence")
        if maya_utils.movie_supported():
            self.format_combo.addItem("Movie (H.264)")
        
        self.use_timeline()
        
    def connect_signals(self):
        self.browse_button.clicked.connect(self.browse)
        self.timeline_button.clicked.connect(self.use_timeline)
        self.cancel_button.clicked.connect(self.reject)
        self.publish_button.clicked.connect(self.publish)
        
        self.root_edit.textChanged.connect(self.update_preview)
        self.shot_edit.textChanged.connect(self.update_preview)
        self.dept_combo.currentTextChanged.connect(self.update_preview)
        self.start_spin.valueChanged.connect(self.update_preview)
        self.end_spin.valueChanged.connect(self.update_preview)
        
    def browse(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Choose publish root", self.root_edit.text()
        )
        if folder:
            self.root_edit.setText(folder)
            
    def use_timeline(self):
        start, end = maya_utils.frame_range()
        self.start_spin.setValue(start)
        self.end_spin.setValue(end)
        
    def find_problem(self):
        """Return the first thing that would stop a publish, or an empty string if all looks good."""
        if not self.root_edit.text().strip():
            return "Choose a publish root."
        shot_error = versioning.validate_shot(self.shot_edit.text())
        if shot_error:
            return shot_error
        if not self.camera_combo.currentText():
            return "The scene has no camera to playblast."
        if self.start_spin.value() > self.end_spin.value():
            return "Start fram is after end frame."
        return ""
    
    def update_preview(self, *args):
        problem = self.find_problem()
        self.publish_button.setEnabled(problem == "")
        
        if problem:
            self.preview_label.setText(f"<span style='color:#e5534b'>{problem}</span>")
            return
        
        shot = self.shot_edit.text()
        dept = self.dept_combo.currentText()
        dept_folder = Path(self.root_edit.text()) / shot / dept
        version = versioning.next_version(dept_folder)
        self.preview_label.setText(f"Will publish <b>{shot}_{dept}_v{version:03d}</b>")
        
    def publish(self):
        # read everything from the form
        root = self.root_edit.text().strip()
        shot = self.shot_edit.text()
        dept = self.dept_combo.currentText()
        camera = self.camera_combo.currentText()
        start = self.start_spin.value()
        end = self.end_spin.value()
        width, height = RESOLUTIONS[self.res_combo.currentText()]
        movie = self.format_combo.currentText().startswith("Movie")
        
        # show busy cursor while creating
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        paths = None
        try:
            # make version folder, playblast, write metadata
            paths = versioning.build_publish_paths(root, shot, dept)
            media = maya_utils.playblast(
                paths["media_prefix"], camera, start, end, width, height, movie
            )
            versioning.write_metadata(paths["metadata"], {
                "shot": shot,
                "department": dept,
                "version": paths["version"],
                "artist": getpass.getuser(),
                "scene": maya_utils.scene_path(),
                "camera": camera,
                "frame_start": start,
                "frame_end": end,
                "fps": maya_utils.scene_fps(),
                "resolution": [width, height],
                "media": str(media),
                "notes": self.notes_edit.toPlainText().strip(),
            })
        except Exception as error:
            # error and tell the user why
            folder_is_empty = paths and not any(paths["folder"].iterdir())
            if folder_is_empty:
                paths["folder"].rmdir()
            QtWidgets.QApplication.restoreOverrideCursor()
            QtWidgets.QMessageBox.critical(self, "Publish failed", str(error))
            return
        
        QtWidgets.QApplication.restoreOverrideCursor()
        self.settings.setValue("publish_root", root)
        self.update_preview()
        
        answer = QtWidgets.QMessageBox.question(
            self, "Published", f"Published {paths['metadata'].stem}.\n\nOpen the folder?"
        )
        if answer == QtWidgets.QMessageBox.Yes:
            folder_url = QtCore.QUrl.fromLocalFile(str(paths["folder"]))
            QtGui.QDesktopServices.openUrl(folder_url)
            
# opening window inside maya
dialog = None   # reference so python doesn't delete window

def maya_main_window():
    """Maya's main window, as a Qt widget we can use as a parent"""
    from maya import OpenMayaUI
    pointer = OpenMayaUI.MQtUtil.mainWindow()
    return wrapInstance(int(pointer), QtWidgets.QWidget)

def show():
    """Open the Playblast Publisher, closing any copy that's already open"""
    global dialog
    if dialog is not None:
        dialog.close()
        dialog.deleteLater()
    dialog = PublisherDialog(parent=maya_main_window())
    dialog.show()