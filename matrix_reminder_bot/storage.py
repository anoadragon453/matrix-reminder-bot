import logging
from datetime import datetime, timedelta
from typing import Dict

from apscheduler.util import timedelta_seconds

from matrix_reminder_bot.reminder import REMINDERS, Reminder

latest_migration_version = 0

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

        self._execute(f"""
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
        # No migrations yet
        pass

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
                room_id,
                target_user,
                alarm
            FROM reminder
        """)
        rows = self.cursor.fetchall()
        logger.debug("Loaded reminder rows: %s", rows)

        for row in rows:
            REMINDERS[(row[3], row[0])] = Reminder(
                client=client,
                store=self,
                reminder_text=row[0],
                start_time=datetime.fromisoformat(row[1]),
                recurse_timedelta=timedelta(seconds=row[2]) if row[2] else None,
                room_id=row[3],
                target_user=row[4],
                alarm=row[5],
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
                room_id,
                target_user,
                alarm
            ) VALUES (
                ?, ?, ?, ?, ?, ?
            )
        """, (
            reminder.reminder_text,
            reminder.start_time,
            delta_seconds,
            reminder.room_id,
            reminder.target_user,
            reminder.alarm,
        ))

    def delete_reminder(self, reminder_text: str):
        """Delete a reminder via its reminder text"""
        self._execute("""
            DELETE FROM reminder WHERE text = ?
        """, (reminder_text,))
