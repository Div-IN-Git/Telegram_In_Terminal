from __future__ import annotations

from bits_cli.ui.tables import human_size

try:
    from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
except ImportError:  # pragma: no cover
    QAbstractTableModel = object
    QModelIndex = object
    Qt = None


class VersionTableModel(QAbstractTableModel):
    HEADERS = ["Version", "Date", "Time", "Size", "Status", "Hash"]

    def __init__(self, versions=None):
        super().__init__()
        self.versions = versions or []

    def rowCount(self, parent=QModelIndex()):
        return len(self.versions)

    def columnCount(self, parent=QModelIndex()):
        return len(self.HEADERS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.HEADERS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or role != Qt.DisplayRole:
            return None
        record = self.versions[index.row()]
        values = [
            record.version_number,
            record.upload_date,
            record.upload_time,
            human_size(record.size_bytes),
            record.upload_status,
            record.sha256_hash[:12],
        ]
        return str(values[index.column()])

    def set_versions(self, versions):
        self.beginResetModel()
        self.versions = versions
        self.endResetModel()
