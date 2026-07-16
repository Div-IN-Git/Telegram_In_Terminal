from __future__ import annotations

try:
    from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt
except ImportError:  # pragma: no cover
    QAbstractListModel = object
    QModelIndex = object
    Qt = None


class ProjectListModel(QAbstractListModel):
    def __init__(self, projects=None):
        super().__init__()
        self.projects = projects or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.projects)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role not in (Qt.DisplayRole, Qt.UserRole):
            return None
        project = self.projects[index.row()]
        return project if role == Qt.UserRole else project.name

    def set_projects(self, projects):
        self.beginResetModel()
        self.projects = projects
        self.endResetModel()
