from __future__ import annotations

from pathlib import Path

from bitscore import BitsAPI

from bits_gui.models.project_model import ProjectListModel
from bits_gui.models.version_table_model import VersionTableModel

try:
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (
        QFileDialog,
        QHBoxLayout,
        QInputDialog,
        QLabel,
        QListView,
        QMainWindow,
        QMessageBox,
        QPushButton,
        QSplitter,
        QStatusBar,
        QTableView,
        QToolBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError:  # pragma: no cover
    QMainWindow = object


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.api = BitsAPI()
        self.setWindowTitle("bits")

        self.project_model = ProjectListModel()
        self.version_model = VersionTableModel()

        self.projects = QListView()
        self.projects.setModel(self.project_model)
        self.projects.selectionModel().selectionChanged.connect(self.on_project_selected)

        self.versions = QTableView()
        self.versions.setModel(self.version_model)
        self.versions.setSortingEnabled(False)
        self.versions.doubleClicked.connect(self.download_selected)

        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.addWidget(QLabel("Projects"))
        left_layout.addWidget(self.projects)

        right = QWidget()
        right_layout = QVBoxLayout(right)
        self.breadcrumb = QLabel("Home")
        right_layout.addWidget(self.breadcrumb)
        right_layout.addWidget(self.versions)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setStretchFactor(1, 4)
        self.setCentralWidget(splitter)

        toolbar = QToolBar("Main")
        self.addToolBar(toolbar)
        self._add_button(toolbar, "Upload", self.upload_dialog)
        self._add_button(toolbar, "Download", self.download_selected)
        self._add_button(toolbar, "Delete", self.delete_selected)
        self._add_button(toolbar, "Refresh", self.refresh)
        self._add_button(toolbar, "Health", self.health)

        self.setStatusBar(QStatusBar())
        self.refresh()

    def _add_button(self, toolbar, label: str, slot) -> None:
        button = QPushButton(label)
        button.clicked.connect(slot)
        toolbar.addWidget(button)

    def refresh(self) -> None:
        self.project_model.set_projects(self.api.list_projects())
        self.statusBar().showMessage("Ready")

    def selected_project(self):
        indexes = self.projects.selectedIndexes()
        if not indexes:
            return None
        return self.project_model.data(indexes[0], Qt.UserRole)

    def selected_version(self):
        rows = self.versions.selectionModel().selectedRows()
        if not rows:
            return None
        return self.version_model.versions[rows[0].row()]

    def on_project_selected(self) -> None:
        project = self.selected_project()
        if not project:
            return
        self.breadcrumb.setText(f"Home > {project.name}")
        try:
            self.version_model.set_versions(self.api.list_versions(project.name))
        except Exception:
            self.version_model.set_versions([])

    def upload_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Choose a file to upload")
        if not path:
            return
        try:
            self.api.stage(Path(path))
            name, ok = QInputDialog.getText(self, "Project name", "Project name:", text=Path(path).stem)
            if not ok:
                return
            record = self.api.upload_plate(project_name=name or None)
            QMessageBox.information(self, "Uploaded", f"{record.project_name} Version {record.version_number} uploaded.")
            self.refresh()
        except Exception as exc:
            QMessageBox.critical(self, "Upload failed", str(exc))

    def download_selected(self) -> None:
        record = self.selected_version()
        if not record:
            return
        folder = QFileDialog.getExistingDirectory(self, "Download to")
        if not folder:
            return
        try:
            path = self.api.download(record.project_name, version=record.version_number, dest=Path(folder))
            QMessageBox.information(self, "Downloaded", f"Downloaded to {path}")
        except Exception as exc:
            QMessageBox.critical(self, "Download failed", str(exc))

    def delete_selected(self) -> None:
        record = self.selected_version()
        if not record:
            return
        if QMessageBox.question(self, "Delete", f"Delete {record.project_name} Version {record.version_number}?") != QMessageBox.Yes:
            return
        try:
            self.api.delete_version(record.project_name, version=record.version_number)
            self.on_project_selected()
        except Exception as exc:
            QMessageBox.critical(self, "Delete failed", str(exc))

    def health(self) -> None:
        report = self.api.run_diagnostics(include_telegram=False)
        QMessageBox.information(
            self,
            "Health",
            f"DB: {report.db_integrity}\nProjects: {report.stats.project_count}\nVersions: {report.stats.version_count}\nTelegram configured: {report.telegram['configured']}",
        )
