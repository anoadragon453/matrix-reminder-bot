import logging
import pytz
from datetime import datetime, timedelta
from typing import Dict

from apscheduler.util import timedelta_seconds

from matrix_reminder_bot.reminder import REMINDERS, Reminder

latest_migration_version = 1

logger = logging.getLogger(__name__)


class Storage(object):
    def __init__(self, db: Dict):
        """Setup the database

        Runs an initial setup or migrations depending on whether a database file has already
        been created

        Args:
            db: A dictionary containing the following keys:
                  * type: A string, one of "sqlite" or "postgres"
                  * connection_string: A string, featuring a connection string that
                        be fed to each respective db library's `connect` method
        """
        # Check which type of database has been configured
        self.conn = self._get_database_connection(db["type"], db["connection_string"])
        self.cursor = self.conn.cursor()
        self.db_type = db["type"]

        # Try to check the current migration version
        try:
            self._execute("SELECT version FROM migration_version")
            row = self.cursor.fetchone()

            if row[0] < latest_migration_version:
                self._run_db_migrations(row[0])
        except Exception:
            self._initial_db_setup()

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
        self._execute("""
            CREATE TABLE migration_version (
                version INTEGER PRIMARY KEY
            )
        """)

        # Initially set the migration version to 0
        self._execute("""
            INSERT INTO migration_version (
                version
            ) VALUES (?)
        """, (0,))

        # Set up the reminders table
        self._execute("""
            CREATE TABLE reminder (
                text TEXT,
                start_time TEXT NOT NULL,
                recurse_timedelta_s INTEGER,
                room_id TEXT NOT NULL,
                target_user TEXT,
                alarm BOOL NOT NULL
            )
        """)

        # Create a unique index on room_id, reminder text as no two reminders in the same
        # room can have the same reminder text
        self._execute("""
            CREATE UNIQUE INDEX reminder_room_id_text
            ON reminder(room_id, text)
        """)

        # Start executing db migrations from the beginning
        self._run_db_migrations(0)

    def _run_db_migrations(self, current_migration_version: int):
        """Execute database migrations. Migrates the database to the
        `latest_migration_version`

        Args:
            current_migration_version: The migration version that the database is
                currently at
        """
        if current_migration_version < 1:
            # Add cron_tab column, prevent start_time from being required
            #
            # As SQLite3 is quite limited, we need to create a new table and populate it
            # with existing data
            self._execute("ALTER TABLE reminder RENAME TO reminder_temp")

            self._execute("""
                CREATE TABLE reminder (
                    text TEXT,
                    start_time TEXT,
                    recurse_timedelta_s INTEGER,
                    cron_tab TEXT,
                    room_id TEXT NOT NULL,
                    target_user TEXT,
                    alarm BOOL NOT NULL
                )
           """)
            self._execute("""
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
           """)

            self._execute("""
                 DROP INDEX reminder_room_id_text
           """)
            self._execute("""
                CREATE UNIQUE INDEX reminder_room_id_text
                ON reminder(room_id, text)
           """)

            self._execute("""
                DROP TABLE reminder_temp
           """)

    def load_reminders(self, client):
        """Load reminders from the database

        Args:
            client: The matrix client

        Returns:
            A dictionary from tuple (room_id, reminder text) to Reminder object
        """
        self._execute("""
            SELECT
                text,
                start_time,
                recurse_timedelta_s,
                cron_tab,
                room_id,
                target_user,
                alarm
            FROM reminder
        """)
        rows = self.cursor.fetchall()
        logger.debug("Loaded reminder rows: %s", rows)

        for row in rows:
            # Extract reminder data
            reminder_text = row[0]
            start_time = datetime.fromisoformat(row[1]) if row[1] else None
            recurse_timedelta = timedelta(seconds=row[2]) if row[2] else None
            cron_tab = row[3]
            room_id = row[4]
            target_user = row[5]
            alarm = row[6]

            # If this is a one-off reminder whose start time is in the past, then it will
            # never fire. Ignore and delete the row from the db
            if (
                    not recurse_timedelta
                    and not cron_tab
                    and start_time < datetime.now(tz=pytz.utc)
            ):
                logger.debug(
                    "Deleting missed reminder in room %s: %s - %s",
                    room_id, reminder_text, start_time
                )

                self.delete_reminder(room_id, reminder_text)
                continue

            # Create and record the reminder
            REMINDERS[(room_id, reminder_text.upper())] = Reminder(
                client=client,
                store=self,
                reminder_text=reminder_text,
                start_time=start_time,
                recurse_timedelta=recurse_timedelta,
                cron_tab=cron_tab,
                room_id=room_id,
                target_user=target_user,
                alarm=alarm,
            )

    def store_reminder(self, reminder: Reminder):
        """Store a new reminder in the database"""
        # timedelta.seconds does NOT give you the timedelta converted to seconds
        # Use a method from apscheduler instead
        if reminder.recurse_timedelta:
            delta_seconds = int(timedelta_seconds(reminder.recurse_timedelta))
        else:
            delta_seconds = None

        self._execute("""
            INSERT INTO reminder (
                text,
                start_time,
                recurse_timedelta_s,
                cron_tab,
                room_id,
                target_user,
                alarm
            ) VALUES (
                ?, ?, ?, ?, ?, ?, ?
            )
        """, (
            reminder.reminder_text,
            reminder.start_time.isoformat() if reminder.start_time else None,
            delta_seconds,
            reminder.cron_tab,
            reminder.room_id,
            reminder.target_user,
            reminder.alarm,
        ))

    def delete_reminder(self, room_id: str, reminder_text: str):
        """Delete a reminder via its reminder text and the room it was sent in"""
        self._execute("""
            DELETE FROM reminder WHERE room_id = ? AND UPPER(text) = ?
        """, (room_id, reminder_text.upper(),))
