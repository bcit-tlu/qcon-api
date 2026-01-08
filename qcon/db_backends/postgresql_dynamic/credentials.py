import logging
import threading
from pathlib import Path

from django.conf import settings


logger = logging.getLogger(__name__)


_DEFAULT_CREDENTIAL_DIR = "/etc/secrets/db-credentials"

# Map secret file names to Django DATABASES keys
_SECRET_FILE_MAPPING = {
    "POSTGRES_DB": "NAME",
    "POSTGRES_USER": "USER",
    "POSTGRES_PASSWORD": "PASSWORD",
    "POSTGRES_HOST": "HOST",
}


class _CredentialState:
    """In-memory snapshot of database credentials and file stats."""

    __slots__ = ("creds", "file_stats")

    def __init__(self, creds, file_stats):
        self.creds = creds  # dict of NAME/USER/PASSWORD/HOST
        self.file_stats = file_stats  # {filename: (inode, mtime, size)}


_state_lock = threading.Lock()
_cached_state = None  # type: _CredentialState | None


def _get_credential_dir() -> Path:
    base_dir = getattr(settings, "DYNAMIC_DB_CREDENTIAL_DIR", _DEFAULT_CREDENTIAL_DIR)
    return Path(base_dir)


def _stat_file(path: Path):
    stat = path.stat()
    return stat.st_ino, stat.st_mtime, stat.st_size


def _read_credentials_from_disk(cred_dir: Path) -> _CredentialState:
    creds = {}
    file_stats = {}

    for filename, db_key in _SECRET_FILE_MAPPING.items():
        path = cred_dir / filename
        if not path.exists():
            raise RuntimeError(f"Missing required database credential file: {path}")

        raw = path.read_text(encoding="utf-8").strip()
        if not raw:
            raise RuntimeError(f"Empty value in database credential file: {path}")

        creds[db_key] = raw
        file_stats[filename] = _stat_file(path)

    return _CredentialState(creds=creds, file_stats=file_stats)


def _credentials_files_changed(cred_dir: Path, state: _CredentialState) -> bool:
    for filename, old_stats in state.file_stats.items():
        path = cred_dir / filename
        try:
            new_stats = _stat_file(path)
        except FileNotFoundError:
            return True

        if new_stats != old_stats:
            return True

    return False


def get_current_credentials() -> dict:
    """Return latest database credentials from the secret directory.

    This function caches the last known good credentials and only reloads
    when one of the underlying secret files changes. If a reload fails
    but cached credentials exist, the cached values are returned.
    """

    global _cached_state

    cred_dir = _get_credential_dir()

    with _state_lock:
        if _cached_state is None:
            # First-time load: any error should be fatal so the app fails fast
            state = _read_credentials_from_disk(cred_dir)
            _cached_state = state
            logger.info("Loaded initial database credentials from %s", cred_dir)
            return dict(state.creds)

        # Check if any credential file has changed
        try:
            changed = _credentials_files_changed(cred_dir, _cached_state)
        except Exception:
            # If we cannot even stat the files, log and fall back to cache
            logger.warning(
                "Error while checking database credential files for changes; "
                "continuing to use cached credentials",
                exc_info=True,
            )
            return dict(_cached_state.creds)

        if not changed:
            return dict(_cached_state.creds)

        # Attempt to reload credentials
        try:
            new_state = _read_credentials_from_disk(cred_dir)
        except Exception:
            logger.warning(
                "Failed to reload database credentials from %s; "
                "continuing to use cached credentials",
                cred_dir,
                exc_info=True,
            )
            return dict(_cached_state.creds)

        _cached_state = new_state
        logger.info("Reloaded database credentials from %s", cred_dir)
        return dict(new_state.creds)
