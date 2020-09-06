import logging
from datetime import datetime, timedelta
from typing import Dict, Tuple

import pytz
from apscheduler.util import timedelta_seconds
from nio import AsyncClient

from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.reminder import REMINDERS, Reminder

latest_migration_version = 3

logger = logging.getLogger(__name__)


class Storage(object):
    def __init__(self, client: AsyncClient):
        """Setup the database

        Runs an initial setup or migrations depending on whether a database file has already
        been created

        Args:
            client: The matrix client
        """
        # Check which type of database has been configured
        self.client = client
        self.conn = self._get_database_connection(
            CONFIG.database.type, CONFIG.database.connection_string
        )
        self.cursor = self.conn.cursor()
        self.db_type = CONFIG.database.type

        # Try to check the current migration version
        migration_level = 0
        try:
            self._execute("SELECT version FROM migration_version")
            row = self.cursor.fetchone()
            migration_level = row[0]
        except Exception:
            self._initial_db_setup()
        finally:
            if migration_level < latest_migration_version:
                self._run_db_migrations(migration_level)

        # Load reminders from the db
        REMINDERS.update(self._load_reminders())

        logger.info(f"Database initialization of type '{self.db_type}' complete")

    def _get_database_connection(self, database_type: str, connection_string: str):
        if database_type == "sqlite":
            import sqlite3

            # Initialize a connection to the database, with autocommit on
            return sqlite3.connect(connection_string, isolation_level=None)
        elif database_type == "postgres":
            import psycopg2

            conn = psycopg2.connect(connection_string)

            # Autocommit on
            conn.set_isolation_level(0)

            return conn

    def _execute(self, *args):
        """A wrapper around cursor.execute that transforms ?'s to %s for postgres"""
        if self.db_type == "postgres":
            self.cursor.execute(args[0].replace("?", "%s"), *args[1:])
        else:
            self.cursor.execute(*args)

    def _initial_db_setup(self):
        """Initial setup of the database"""
        logger.info("Performing initial database setup...")

        # Set up the migration_version table
        self._execute(
            """
            CREATE TABLE migration_version (
                version INTEGER PRIMARY KEY
            )
        """
        )

        # Initially set the migration version to 0
        self._execute(
            """
            INSERT INTO migration_version (
                version
            ) VALUES (?)
        """,
            (0,),
        )

        # Set up the reminders table
        self._execute(
            """
            CREATE TABLE reminder (
                text TEXT,
                start_time TEXT NOT NULL,
                recurse_timedelta_s INTEGER,
                room_id TEXT NOT NULL,
                target_user TEXT,
                alarm BOOL NOT NULL
            )
        """
        )

        # Create a unique index on room_id, reminder text as no two reminders in the same
        # room can have the same reminder text
        self._execute(
            """
            CREATE UNIQUE INDEX reminder_room_id_text
            ON reminder(room_id, text)
        """
        )

    def _run_db_migrations(self, current_migration_version: int):
        """Execute database migrations. Migrates the database to the
        `latest_migration_version`

        Args:
            current_migration_version: The migration version that the database is
                currently at
        """
        logger.debug("Checking for necessary database migrations...")

        if current_migration_version < 1:
            logger.info("Migrating the database from v0 to v1...")

            # Add cron_tab column, prevent start_time from being required
            #
            # As SQLite3 is quite limited, we need to create a new table and populate it
            # with existing data
            self._execute("ALTER TABLE reminder RENAME TO reminder_temp")

            self._execute(
                """
                CREATE TABLE reminder (
                    text TEXT,
                    start_time TEXT,
                    recurse_timedelta_s INTEGER,
                    cron_tab TEXT,
                    room_id TEXT NOT NULL,
                    target_user TEXT,
                    alarm BOOL NOT NULL
                )
           """
            )
            self._execute(
                """
                INSERT INTO reminder (
                    text,
                    start_time,
                    recurse_timedelta_s,
                    room_id,
                    target_user,
                    alarm
                )
                SELECT
                    text,
                    start_time,
                    recurse_timedelta_s,
                    room_id,
                    target_user,
                    alarm
                FROM reminder_temp;
           """
            )

            self._execute(
                """
                 DROP INDEX reminder_room_id_text
           """
            )
            self._execute(
                """
                CREATE UNIQUE INDEX reminder_room_id_text
                ON reminder(room_id, text)
           """
            )

            self._execute(
                """
                DROP TABLE reminder_temp
           """
            )

            self._execute(
                """
                 UPDATE migration_version SET version = 1
            """
            )

            logger.info("Database migrated to v1")

        if current_migration_version < 2:
            logger.info("Migrating the database from v1 to v2...")

            # Add a timezone column to the reminder database, so we can easily keep
            # track of which timezone a reminder was created in
            self._execute(
                """
                ALTER TABLE reminder
                    ADD COLUMN timezone TEXT
            """
            )

            # Assume the currently configured database timezone for all rows
            self._execute(
                """
                UPDATE reminder SET timezone = ?
            """,
                (CONFIG.timezone,),
            )

            self._execute(
                """
                 UPDATE migration_version SET version = 2
            """
            )

            logger.info("Database migrated to v2")

        if current_migration_version < 3:
            logger.info("Migrating the database from v2 to v3...")

            # Remove current timezone information from all start_time entries (as an older
            # version of the code used to insert them)
            self._execute(
                """
                SELECT text, room_id, start_time FROM reminder
                    WHERE start_time LIKE '%+%'
                    OR start_time LIKE '%-%'
            """
            )
            rows = self.cursor.fetchall()
            logger.debug("Loaded reminder rows with tz info: %s", rows)

            # Update start_time rows in the db with their non-timezone versions
            for row in rows:
                text = row[0]
                room_id = row[1]
                start_time = datetime.fromisoformat(row[2])

                # Remove timezone information from start_time
                start_time = start_time.replace(tzinfo=None)

                logger.debug(
                    "Updating (%s, %s) with new start_time: %s",
                    text,
                    room_id,
                    start_time,
                )
                self._execute(
                    """
                    UPDATE reminder SET start_time = ?
                        WHERE text = ? AND room_id = ?
                """,
                    (start_time, text, room_id),
                )

            self._execute(
                """
                 UPDATE migration_version SET version = 3
            """
            )

            logger.info("Database migrated to v3")

    def _load_reminders(self) -> Dict[Tuple[str, str], Reminder]:
        """Load reminders from the database

        Returns:
            A dictionary from (room_id, reminder text) to Reminder object
        """
        self._execute(
            """
            SELECT
                text,
                start_time,
                timezone,
                recurse_timedelta_s,
                cron_tab,
                room_id,
                target_user,
                alarm
            FROM reminder
        """
        )
        rows = self.cursor.fetchall()
        logger.debug("Loaded reminder rows: %s", rows)
        reminders = {}

        for row in rows:
            # Extract reminder data
            reminder_text = row[0]
            start_time = datetime.fromisoformat(row[1]) if row[1] else None
            timezone = row[2]
            recurse_timedelta = timedelta(seconds=row[3]) if row[3] else None
            cron_tab = row[4]
            room_id = row[5]
            target_user = row[6]
            alarm = row[7]

            if start_time:
                # If this is a one-off reminder whose start time is in the past, then it will
                # never fire. Ignore and delete the row from the db
                if not recurse_timedelta and not cron_tab:
                    now = datetime.now(tz=pytz.timezone(timezone))

                    # We don't replace the timezone in start_time itself as Reminder.__init__
                    # will add the timezone later (and doing so twice will produce strange
                    # behaviour)
                    if start_time.replace(tzinfo=pytz.timezone(timezone)) < now:
                        logger.debug(
                            "Deleting missed reminder in room %s: %s - %s",
                            room_id,
                            reminder_text,
                            start_time,
                        )

                        self.delete_reminder(room_id, reminder_text)
                        continue

            # Create and record the reminder
            reminders[(room_id, reminder_text.upper())] = Reminder(
                client=self.client,
                store=self,
                reminder_text=reminder_text,
                start_time=start_time,
                timezone=timezone,
                recurse_timedelta=recurse_timedelta,
                cron_tab=cron_tab,
                room_id=room_id,
                target_user=target_user,
                alarm=alarm,
            )

        return reminders

    def store_reminder(self, reminder: Reminder):
        """Store a new reminder in the database"""
        # timedelta.seconds does NOT give you the timedelta converted to seconds
        # Use a method from apscheduler instead
        if reminder.recurse_timedelta:
            delta_seconds = int(timedelta_seconds(reminder.recurse_timedelta))
        else:
            delta_seconds = None

        if reminder.start_time:
            # Remove timezone from start_time. We only want to store the timezone str
            # in the database
            reminder.start_time = reminder.start_time.replace(tzinfo=None)

        self._execute(
            """
            INSERT INTO reminder (
                text,
                start_time,
                timezone,
                recurse_timedelta_s,
                cron_tab,
                room_id,
                target_user,
                alarm
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?
            )
        """,
            (
                reminder.reminder_text,
                reminder.start_time.isoformat() if reminder.start_time else None,
                reminder.timezone,
                delta_seconds,
                reminder.cron_tab,
                reminder.room_id,
                reminder.target_user,
                reminder.alarm,
            ),
        )

    def delete_reminder(self, room_id: str, reminder_text: str):
        """Delete a reminder via its reminder text and the room it was sent in"""
        self._execute(
            """
            DELETE FROM reminder WHERE room_id = ? AND text = ?
        """,
            (room_id, reminder_text),
        )
