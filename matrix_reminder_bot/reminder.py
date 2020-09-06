import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple

from apscheduler.job import Job
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from apscheduler.util import timedelta_seconds
from nio import AsyncClient

from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.functions import send_text_to_room

logger = logging.getLogger(__name__)

# The object that runs callbacks at a certain time
SCHEDULER = AsyncIOScheduler()

# How often an alarm should sound after the reminder it's attached to
ALARM_TIMEDELTA = timedelta(minutes=5)


class Reminder(object):
    """An object containing information about a reminder, when it should go off,
    whether it is recurring, etc.

    Args:
        client: The matrix client
        store: A Storage object
        room_id: The ID of the room the reminder should appear in
        start_time: When the reminder should first go off
        timezone: The database name of the timezone this reminder should act within
        reminder_text: The text to include in the reminder message
        recurse_timedelta: Optional. How often to repeat the reminder
        target_user: Optional. A user ID of a specific user to mention in the room while
            reminding
        alarm: Whether this reminder is an alarm. Alarms are reminders that fire every 5m
            after they go off normally, until they are silenced.
    """

    def __init__(
        self,
        client: AsyncClient,
        store,
        room_id: str,
        reminder_text: str,
        start_time: Optional[datetime] = None,
        timezone: Optional[str] = None,
        recurse_timedelta: Optional[timedelta] = None,
        cron_tab: Optional[str] = None,
        target_user: Optional[str] = None,
        alarm: bool = False,
    ):
        self.client = client
        self.store = store
        self.room_id = room_id
        self.timezone = timezone
        self.start_time = start_time
        self.reminder_text = reminder_text
        self.cron_tab = cron_tab
        self.recurse_timedelta = recurse_timedelta
        self.target_user = target_user
        self.alarm = alarm

        # Schedule the reminder

        # Determine how the reminder is triggered
        if cron_tab:
            # Set up a cron trigger
            trigger = CronTrigger.from_crontab(cron_tab, timezone=timezone)
        elif recurse_timedelta:
            # Use an interval trigger (runs multiple times)
            trigger = IntervalTrigger(
                # timedelta.seconds does NOT give you the timedelta converted to seconds
                # Use a method from apscheduler instead
                seconds=int(timedelta_seconds(recurse_timedelta)),
                start_date=start_time,
                timezone=timezone,
            )
        else:
            # Use a date trigger (runs only once)
            trigger = DateTrigger(run_date=start_time, timezone=timezone)

        # Note down the job for later manipulation
        self.job = SCHEDULER.add_job(self._fire, trigger=trigger)

        self.alarm_job = None

    async def _fire(self):
        """Called when a reminder fires"""
        logger.debug("Reminder in room %s fired: %s", self.room_id, self.reminder_text)

        # Build the reminder message
        target = self.target_user if self.target_user else "@room"
        message = f"{target} {self.reminder_text}"

        # If this reminder has an alarm attached...
        if self.alarm:
            # Inform the user that an alarm will go off
            message += (
                f"\n\n(This reminder has an alarm. You will be reminded again in 5m. "
                f"Use the `{CONFIG.command_prefix}silence` command to stop)."
            )

            # Check that an alarm is not already ongoing from a previous run
            if not (self.room_id, self.reminder_text.upper()) in ALARMS:
                # Start alarming
                self.alarm_job = SCHEDULER.add_job(
                    self._fire_alarm,
                    trigger=IntervalTrigger(
                        # timedelta.seconds does NOT give you the timedelta converted to
                        # seconds. Use a method from apscheduler instead
                        seconds=int(timedelta_seconds(ALARM_TIMEDELTA)),
                    ),
                )
                ALARMS[(self.room_id, self.reminder_text.upper())] = self.alarm_job

        # Send the message to the room
        await send_text_to_room(self.client, self.room_id, message, notice=False)

        # If this was a one-time reminder, cancel and remove from the reminders dict
        if not self.recurse_timedelta and not self.cron_tab:
            # We set cancel_alarm to False here else the associated alarms wouldn't even
            # fire
            self.cancel(cancel_alarm=False)

    async def _fire_alarm(self):
        logger.debug("Alarm in room %s fired: %s", self.room_id, self.reminder_text)

        # Build the alarm message
        target = self.target_user if self.target_user else "@room"
        message = (
            f"Alarm: {target} {self.reminder_text} "
            f"(Use `{CONFIG.command_prefix}silence [reminder text]` to silence)."
        )

        # Send the message to the room
        await send_text_to_room(self.client, self.room_id, message, notice=False)

    def cancel(self, cancel_alarm: bool = True):
        """Cancels a reminder and all recurring instances

        Args:
            cancel_alarm: Whether to also cancel alarms of this reminder
        """
        logger.debug(
            "Cancelling reminder in room %s: %s", self.room_id, self.reminder_text
        )

        # Remove from the in-memory reminder and alarm dicts
        REMINDERS.pop((self.room_id, self.reminder_text.upper()), None)

        # Delete the reminder from the database
        self.store.delete_reminder(self.room_id, self.reminder_text)

        # Delete any ongoing jobs
        if self.job and SCHEDULER.get_job(self.job.id):
            self.job.remove()

        # Cancel alarms of this reminder if required
        if cancel_alarm:
            ALARMS.pop((self.room_id, self.reminder_text.upper()), None)

            if self.alarm_job and SCHEDULER.get_job(self.alarm_job.id):
                self.alarm_job.remove()


# Global dictionaries
#
# Both feature (room_id, reminder_text) tuples as keys
#
# reminder_text should be accessed and stored as uppercase in order to
# allow for case-insensitive matching when carrying out user actions
REMINDERS: Dict[Tuple[str, str], Reminder] = {}
ALARMS: Dict[Tuple[str, str], Job] = {}
