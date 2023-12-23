import logging
import os
import re
import sys
from typing import Any, List

import yaml

from matrix_reminder_bot.errors import ConfigError

logger = logging.getLogger()
logging.getLogger("peewee").setLevel(
    logging.INFO
)  # Prevent debug messages from peewee lib


class DatabaseConfig:
    def __init__(self):
        # The type of database. Supported types are 'sqlite' and 'postgres'
        self.type: str = ""
        self.connection_string: str = ""


class Config:
    def __init__(self):
        """
        Args:
            filepath: Path to the config file
        """
        # TODO: Add some comments for each of these
        # TODO: Also ensure that this commit diff is sane. Did I replace config everywhere?
        self.database: DatabaseConfig = DatabaseConfig()
        self.store_path: str = ""

        self.user_id: str = ""
        self.user_password: str = ""
        self.device_id: str = ""
        self.device_name: str = ""
        self.homeserver_url: str = ""

        self.command_prefix: str = ""

        self.timezone: str = ""

        self.allowlist_enabled: bool = False
        self.allowlist_regexes: list[re.Pattern] = []

        self.blocklist_enabled: bool = False
        self.blocklist_regexes: list[re.Pattern] = []

    def read_config(self, filepath: str):
        if not os.path.isfile(filepath):
            raise ConfigError(f"Config file '{filepath}' does not exist")

        # Load in the config file at the given filepath
        with open(filepath) as file_stream:
            self.config = yaml.safe_load(file_stream.read())

        # Logging setup
        formatter = logging.Formatter(
            "%(asctime)s | %(name)s [%(levelname)s] %(message)s"
        )

        log_level = self._get_cfg(["logging", "level"], default="INFO")
        logger.setLevel(log_level)

        file_logging_enabled = self._get_cfg(
            ["logging", "file_logging", "enabled"], default=False
        )
        file_logging_filepath = self._get_cfg(
            ["logging", "file_logging", "filepath"], default="bot.log"
        )
        if file_logging_enabled:
            handler = logging.FileHandler(file_logging_filepath)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        console_logging_enabled = self._get_cfg(
            ["logging", "console_logging", "enabled"], default=True
        )
        if console_logging_enabled:
            handler = logging.StreamHandler(sys.stdout)
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        # Storage setup
        database_path = self._get_cfg(["storage", "database"], required=True)

        # We support both SQLite and Postgres backends
        # Determine which one the user intends
        sqlite_scheme = "sqlite://"
        postgres_scheme = "postgres://"
        if database_path.startswith(sqlite_scheme):
            self.database.type = "sqlite"
            self.database.connection_string = database_path[len(sqlite_scheme) :]
        elif database_path.startswith(postgres_scheme):
            self.database.type = "postgres"
            self.database.connection_string = database_path
        else:
            raise ConfigError("Invalid connection string for storage.database")

        self.store_path = self._get_cfg(["storage", "store_path"], default="store")

        # Create the store folder if it doesn't exist
        if not os.path.isdir(self.store_path):
            if not os.path.exists(self.store_path):
                os.mkdir(self.store_path)
            else:
                raise ConfigError(
                    f"storage.store_path '{self.store_path}' is not a directory"
                )

        # Matrix bot account setup
        user_id = self._get_cfg(["matrix", "user_id"], required=True)
        if not re.match("@.*:.*", user_id):
            raise ConfigError("matrix.user_id must be in the form @name:domain")
        self.user_id = user_id

        self.user_password = self._get_cfg(["matrix", "user_password"], required=True)
        self.device_id = self._get_cfg(["matrix", "device_id"], required=True)
        self.device_name = self._get_cfg(
            ["matrix", "device_name"], default="nio-template"
        )
        self.homeserver_url = self._get_cfg(["matrix", "homeserver_url"], required=True)

        self.command_prefix = self._get_cfg(["command_prefix"], default="!")

        # Reminder configuration
        self.timezone = self._get_cfg(["reminders", "timezone"], default="Etc/UTC")

        # Allowlist configuration
        allowlist_enabled = self._get_cfg(["allowlist", "enabled"], required=True)
        if not isinstance(allowlist_enabled, bool):
            raise ConfigError("allowlist.enabled must be a boolean value")
        self.allowlist_enabled = allowlist_enabled

        allowlist_strings = self._get_cfg(["allowlist", "regexes"], required=True)
        if not isinstance(allowlist_strings, list) or (
            isinstance(allowlist_strings, list)
            and any(not isinstance(x, str) for x in allowlist_strings)
        ):
            raise ConfigError("allowlist.regexes must be a list of strings")

        allowlist_regexes = []
        for regex in allowlist_strings:
            try:
                allowlist_regexes.append(re.compile(regex))
            except re.error:
                raise ConfigError(
                    f"'{regex}' contained in allowlist.regexes is not a valid regular expression"
                )
        self.allowlist_regexes = allowlist_regexes

        # Blocklist configuration
        blocklist_enabled = self._get_cfg(["blocklist", "enabled"], required=True)
        if not isinstance(blocklist_enabled, bool):
            raise ConfigError("blocklist.enabled must be a boolean value")
        self.blocklist_enabled = blocklist_enabled

        blocklist_strings = self._get_cfg(["blocklist", "regexes"], required=True)
        if not isinstance(blocklist_strings, list) or (
            isinstance(blocklist_strings, list)
            and any(not isinstance(x, str) for x in blocklist_strings)
        ):
            raise ConfigError("blocklist.regexes must be a list of strings")

        blocklist_regexes = []
        for regex in blocklist_strings:
            try:
                blocklist_regexes.append(re.compile(regex))
            except re.error:
                raise ConfigError(
                    f"'{regex}' contained in blocklist.regexes is not a valid regular expression"
                )
        self.blocklist_regexes = blocklist_regexes

    def _get_cfg(
        self,
        path: List[str],
        default: Any = None,
        required: bool = True,
    ) -> Any:
        """Get a config option from a path and option name, specifying whether it is
        required.

        Raises:
            ConfigError: If required is specified and the object is not found
                (and there is no default value provided), this error will be raised
        """
        # Sift through the the config until we reach our option
        config = self.config
        for name in path:
            config = config.get(name)

            # If at any point we don't get our expected option...
            if config is None:
                # Raise an error if it was required
                if required and not default:
                    raise ConfigError(f"Config option {'.'.join(path)} is required")

                # or return the default value
                return default

        # We found the option. Return it
        return config


CONFIG: Config = Config()
