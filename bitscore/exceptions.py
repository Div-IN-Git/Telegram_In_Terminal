class BitsError(Exception):
    """Base exception with a stable machine-readable code."""

    code = "bits_error"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code


class ConfigError(BitsError):
    code = "config_error"


class StorageUnavailableError(BitsError):
    code = "storage_unavailable"


class DuplicateUploadError(BitsError):
    code = "duplicate_upload"


class NotFoundError(BitsError):
    code = "not_found"


class DatabaseCorruptError(BitsError):
    code = "database_corrupt"


class PlateEmptyError(BitsError):
    code = "plate_empty"
