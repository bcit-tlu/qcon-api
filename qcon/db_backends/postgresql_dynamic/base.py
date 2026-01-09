import logging

from django.db.backends.postgresql.base import DatabaseWrapper as PostgresDatabaseWrapper

from .credentials import get_current_credentials


logger = logging.getLogger(__name__)


class DatabaseWrapper(PostgresDatabaseWrapper):
    def get_connection_params(self):
        """Return connection params, applying dynamically loaded credentials.

        This ensures every new database connection uses the latest values from
        the secret-backed credential files, while falling back to the base
        implementation for non-credential options (e.g. PORT, OPTIONS).
        """

        params = super().get_connection_params()

        try:
            creds = get_current_credentials()
        except Exception:
            logger.error("Failed to obtain dynamic database credentials", exc_info=True)
            raise

        name = creds.get("NAME")
        if name is not None:
            params["dbname"] = name

        user = creds.get("USER")
        if user is not None:
            params["user"] = user

        password = creds.get("PASSWORD")
        if password is not None:
            params["password"] = password

        host = creds.get("HOST")
        if host is not None:
            params["host"] = host

        return params
