import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Tuple

import arrow
import dateparser
import pytz
from apscheduler.job import Job
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.date import DateTrigger
from apscheduler.triggers.interval import IntervalTrigger
from nio import AsyncClient, MatrixRoom
from nio.events.room_events import RoomMessageText
from pretty_cron import prettify_cron
from readabledelta import readabledelta

from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.errors import CommandError, CommandSyntaxError
from matrix_reminder_bot.functions import command_syntax, send_text_to_room
from matrix_reminder_bot.reminder import ALARMS, REMINDERS, SCHEDULER, Reminder
from matrix_reminder_bot.storage import Storage

logger = logging.getLogger(__name__)


def _get_datetime_now(tz: str) -> datetime:
    """Returns a timezone-aware datetime object of the current time"""
    # Get a datetime with no timezone information
    no_timezone_datetime = datetime.now()

    # Create a datetime.timezone object with the correct offset from UTC
    offset = timezone(pytz.timezone(tz).utcoffset(no_timezone_datetime))

    # Get datetime.now with that offset
    now = datetime.now(offset)

    # Round to the nearest second for nicer display
    return now.replace(microsecond=0)


def _parse_str_to_time(time_str: str, tz_aware: bool = True) -> datetime:
    """Converts a human-readable, future time string to a datetime object

    Args:
        time_str: The time to convert
        tz_aware: Whether the returned datetime should have associated timezone
            information

    Returns:
        datetime: A datetime if conversion was successful

    Raises:
        CommandError: if conversion was not successful, or time is in the past.
    """
    time = dateparser.parse(
        time_str,
        settings={
            "PREFER_DATES_FROM": "future",
            "TIMEZONE": CONFIG.timezone,
            "RETURN_AS_TIMEZONE_AWARE": tz_aware,
        },
    )
    if not time:
        raise CommandError(f"The given time '{time_str}' is invalid.")

    # Disallow times in the past
    tzinfo = pytz.timezone(CONFIG.timezone)
    if tzinfo.localize(time) < _get_datetime_now(CONFIG.timezone):
        raise CommandError(f"The given time '{time_str}' is in the past.")

    # Round datetime object to the nearest second for nicer display
    time = time.replace(microsecond=0)

    return time


class Command(object):
    def __init__(
        self,
        client: AsyncClient,
        store: Storage,
        command: str,
        room: MatrixRoom,
        event: RoomMessageText,
    ):
        """A command made by a user

        Args:
            client: The client to communicate to matrix with
            store: Bot storage
            command: The command and arguments
            room: The room the command was sent in
            event: The event describing the command
        """
        self.client = client
        self.store = store
        self.room = room
        self.event = event

        msg_without_prefix = command[
            len(CONFIG.command_prefix) :
        ]  # Remove the cmd prefix
        self.args = (
            msg_without_prefix.split()
        )  # Get a list of all items, split by spaces
        self.command = self.args.pop(
            0
        )  # Remove the first item and save as the command (ex. `remindme`)

    def _parse_reminder_command_args_for_cron(self) -> Tuple[str, str]:
        """Processes the list of arguments when a cron tab is present

        Returns:
            A tuple containing the cron tab and the reminder text.
        """

        # Retrieve the cron tab and reminder text

        # Remove "cron" from the argument list
        args = self.args[1:]

        # Combine arguments into a string
        args_str = " ".join(args)
        logger.debug("Parsing cron command arguments: %s", args_str)

        # Split into cron tab and reminder text
        try:
            cron_tab, reminder_text = args_str.split(";", maxsplit=1)
        except ValueError:
            raise CommandSyntaxError()

        return cron_tab, reminder_text.strip()

    def _parse_reminder_command_args(self) -> Tuple[datetime, str, Optional[timedelta]]:
        """Processes the list of arguments and returns parsed reminder information

        Returns:
            A tuple containing the start time of the reminder as a datetime, the reminder text,
            and a timedelta representing how often to repeat the reminder, or None depending on
            whether this is a recurring reminder.

        Raises:
            CommandError: if a time specified in the user command is invalid or in the past
        """
        args_str = " ".join(self.args)
        logger.debug("Parsing command arguments: %s", args_str)

        try:
            time_str, reminder_text = args_str.split(";", maxsplit=1)
        except ValueError:
            raise CommandSyntaxError()
        logger.debug("Got time: %s", time_str)

        # Clean up the input
        time_str = time_str.strip().lower()
        reminder_text = reminder_text.strip()

        # Determine whether this is a recurring command
        # Recurring commands take the form:
        # every <recurse time>, <start time>, <text>
        recurring = time_str.startswith("every")
        recurse_timedelta = None
        if recurring:
            # Remove "every" and retrieve the recurse time
            recurse_time_str = time_str[len("every") :].strip()
            logger.debug("Got recurring time: %s", recurse_time_str)

            # Convert the recurse time to a datetime object
            recurse_time = _parse_str_to_time(recurse_time_str)

            # Generate a timedelta between now and the recurring time
            # `recurse_time` is guaranteed to always be in the future
            current_time = _get_datetime_now(CONFIG.timezone)

            recurse_timedelta = recurse_time - current_time
            logger.debug("Recurring timedelta: %s", recurse_timedelta)

            # Extract the start time
            try:
                time_str, reminder_text = reminder_text.split(";", maxsplit=1)
            except ValueError:
                raise CommandSyntaxError()
            reminder_text = reminder_text.strip()

            logger.debug("Start time: %s", time_str)

        # Convert start time string to a datetime object
        time = _parse_str_to_time(time_str, tz_aware=False)

        return time, reminder_text, recurse_timedelta

    async def _confirm_reminder(self, reminder: Reminder):
        """Sends a message to the room confirming the reminder is set

        Args:
            reminder: The Reminder to confirm
        """
        if reminder.cron_tab:
            # Special-case cron-style reminders. We currently don't do any special
            # parsing for them
            await send_text_to_room(
                self.client, self.room.room_id, "OK, I will remind you!"
            )

            return

        # Convert a datetime to a formatted time (ex. May 25 2020, 01:31)
        start_time = pytz.timezone(reminder.timezone).localize(reminder.start_time)
        human_readable_start_time = start_time.strftime("%b %d %Y, %H:%M")

        # Get a textual representation of who will be notified by this reminder
        target = "you" if reminder.target_user else "everyone in the room"

        # Build the response string
        text = f"OK, I will remind {target} on {human_readable_start_time}"

        if reminder.recurse_timedelta:
            # Inform the user how often their reminder will repeat
            text += f", and again every {readabledelta(reminder.recurse_timedelta)}"

        # Add some punctuation
        text += "!"

        if reminder.alarm:
            # Inform the user that an alarm is attached to this reminder
            text += (
                f"\n\nWhen this reminder goes off, an alarm will sound every "
                f"5 minutes until silenced. Alarms may be silenced using the "
                f"`{CONFIG.command_prefix}silence` command."
            )

        # Send the message to the room
        await send_text_to_room(self.client, self.room.room_id, text)

    async def _remind(self, target: Optional[str] = None, alarm: bool = False):
        """Create a reminder or an alarm with a given target

        Args:
            target: A user ID if this reminder will mention a single user. If None,
                the reminder will mention the whole room
            alarm: Whether this reminder is an alarm. It will fire every 5m after it
                normally fires until silenced.
        """
        # Check whether the time is in human-readable format ("tomorrow at 5pm") or cron-tab
        # format ("* * * * 2,3,4 *"). We differentiate by checking if the time string starts
        # with "cron"
        cron_tab = None
        start_time = None
        recurse_timedelta = None
        if " ".join(self.args).lower().startswith("cron"):
            cron_tab, reminder_text = self._parse_reminder_command_args_for_cron()

            logger.debug(
                "Creating reminder in room %s with cron tab %s: %s",
                self.room.room_id,
                cron_tab,
                reminder_text,
            )
        else:
            (
                start_time,
                reminder_text,
                recurse_timedelta,
            ) = self._parse_reminder_command_args()

            logger.debug(
                "Creating reminder in room %s with delta %s: %s",
                self.room.room_id,
                recurse_timedelta,
                reminder_text,
            )

        if (self.room.room_id, reminder_text.upper()) in REMINDERS:
            await send_text_to_room(
                self.client,
                self.room.room_id,
                "A similar reminder already exists. Please delete that one first.",
            )
            return

        # Create the reminder
        reminder = Reminder(
            self.client,
            self.store,
            self.room.room_id,
            reminder_text,
            start_time=start_time,
            timezone=CONFIG.timezone,
            cron_tab=cron_tab,
            recurse_timedelta=recurse_timedelta,
            target_user=target,
            alarm=alarm,
        )

        # Record the reminder
        REMINDERS[(self.room.room_id, reminder_text.upper())] = reminder
        self.store.store_reminder(reminder)

        # Send a message to the room confirming the creation of the reminder
        await self._confirm_reminder(reminder)

    async def process(self):
        """Process the command"""
        if self.command in ["remindme", "remind", "r"]:
            await self._remind_me()
        elif self.command in ["remindroom", "rr"]:
            await self._remind_room()
        elif self.command in ["alarmme", "alarm", "a"]:
            await self._alarm_me()
        elif self.command in ["alarmroom", "ar"]:
            await self._alarm_room()
        elif self.command in ["listreminders", "listalarms", "list", "lr", "la", "l"]:
            await self._list_reminders()
        elif self.command in [
            "delreminder",
            "deletereminder",
            "removereminder",
            "cancelreminder",
            "delalarm",
            "deletealarm",
            "removealarm",
            "cancelalarm",
            "cancel",
            "rm",
            "cr",
            "ca",
            "d",
            "c",
        ]:
            await self._delete_reminder()
        elif self.command in ["silence", "s"]:
            await self._silence()
        elif self.command in ["help", "h"]:
            await self._help()

    @command_syntax("[every <recurring time>;] <start time>; <reminder text>")
    async def _remind_me(self):
        """Set a reminder that will remind only the user who created it"""
        await self._remind(target=self.event.sender)

    async def _insufficient_room_ping_pl(self):
        room_ping_pl = self.room.power_levels.defaults.notifications.get('room')
        sender_pl = self.room.power_levels.users.get(self.event.sender, 0)
        bot_pl = self.room.power_levels.users.get(self.client.user_id, 0)
        if sender_pl < room_ping_pl:
            insufficient = f"You (<code>{sender_pl}</code>) do"
        elif bot_pl < room_ping_pl:
            insufficient = f"The bot (<code>{bot_pl}</code>) does"

        if insufficient is not None:
            text = f"Insufficient rights: {insufficient} not have the required power level to ping the whole room (<code>{room_ping_pl}</code>)."
            await send_text_to_room(self.client, self.room.room_id, text)
            return True

    @command_syntax("[every <recurring time>;] <start time>; <reminder text>")
    async def _remind_room(self):
        if await self._insufficient_room_ping_pl():
            return

        """Set a reminder that will mention the room that the reminder was created in"""
        await self._remind()

    @command_syntax("[every <recurring time>;] <start time>; <reminder text>")
    async def _alarm_me(self):
        """Set a reminder with an alarm that will remind only the user who created it"""
        await self._remind(target=self.event.sender, alarm=True)

    @command_syntax("[every <recurring time>;] <start time>; <reminder text>")
    async def _alarm_room(self):
        """Set a reminder with an alarm that when fired will mention the room that the
        reminder was created in
        """
        await self._remind(alarm=True)

    @command_syntax("[<reminder text>]")
    async def _silence(self):
        """Silences an ongoing alarm"""

        # Attempt to find a reminder with an alarm currently going off
        reminder_text = " ".join(self.args)
        if reminder_text:
            # Find the alarm job via its reminder text
            alarm_job = ALARMS.get((self.room.room_id, reminder_text.upper()))

            if alarm_job:
                await self._remove_and_silence_alarm(alarm_job, reminder_text)
                text = f"Alarm '{reminder_text}' silenced."
            else:
                # We didn't find an alarm with that reminder text
                #
                # Be helpful and check if this is a known reminder without an alarm
                # currently going off
                reminder = REMINDERS.get((self.room.room_id, reminder_text.upper()))
                if reminder:
                    text = (
                        f"The reminder '{reminder_text}' does not currently have an "
                        f"alarm going off."
                    )
                else:
                    # Nope, can't find it
                    text = f"Unknown alarm or reminder '{reminder_text}'."

        else:
            # No reminder text provided. Check if there's a reminder currently firing
            # in the room instead then
            for alarm_info, job in ALARMS.items():
                if alarm_info[0] == self.room.room_id:
                    # Found one!
                    reminder_text = alarm_info[
                        1
                    ].capitalize()  # normalize the text a bit

                    await self._remove_and_silence_alarm(job, reminder_text)
                    text = f"Alarm '{reminder_text}' silenced."

                    # Prevent the `else` clause from being triggered
                    break
            else:
                # If we didn't find any alarms...
                text = "No alarms are currently firing in this room."

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _remove_and_silence_alarm(self, alarm_job: Job, reminder_text: str):
        # We found a reminder with an alarm. Remove it from the dict of current
        # alarms
        ALARMS.pop((self.room.room_id, reminder_text.upper()), None)

        if SCHEDULER.get_job(alarm_job.id):
            # Silence the alarm job
            alarm_job.remove()

    @command_syntax("")
    async def _list_reminders(self):
        """Format and show known reminders for the current room

        Sends a message listing them in the following format, using the alarm clock emoji ⏰ to indicate an alarm:

            1️⃣ One-time Reminders

            * [⏰] <start time>: <reminder text>

            📅 Cron Reminders

            * [⏰] m h d M wd (`m h d M wd`); next run in <rounded next time>; <reminder text>

            🔁 Repeating Reminders

            * [⏰] every <recurring time>; next run in <rounded next time>; <reminder text>

        or if there are no reminders set:

            There are no reminders for this room.
        """
        output = ""

        cron_reminder_lines = []
        one_shot_reminder_lines = []
        interval_reminder_lines = []

        # Sort the reminder types
        for reminder in REMINDERS.values():
            # Filter out reminders that don't belong to this room
            if reminder.room_id != self.room.room_id:
                continue

            # Organise alarms into markdown lists
            line = "- "
            if reminder.alarm:
                # Note that an alarm exists if available
                alarm_clock_emoji = "⏰"
                line += alarm_clock_emoji + " "

            # Print the duration before (next) execution
            next_execution = reminder.job.next_run_time
            next_execution = arrow.get(next_execution)

            # Cron-based reminders
            if isinstance(reminder.job.trigger, CronTrigger):
                # A human-readable cron tab, in addition to the actual tab
                line += f"{prettify_cron(reminder.cron_tab)} (`{reminder.cron_tab}`); next run {next_execution.humanize()}"

            # One-time reminders
            elif isinstance(reminder.job.trigger, DateTrigger):
                # Just print when the reminder will go off
                line += f"{next_execution.humanize()}"

            # Repeat reminders
            elif isinstance(reminder.job.trigger, IntervalTrigger):
                # Print the interval, and when it will next go off
                line += f"every {readabledelta(reminder.recurse_timedelta)}; next run {next_execution.humanize()}"

            # Add the reminder's text
            line += f'; *"{reminder.reminder_text}"*'

            # Output the status of each reminder. We divide up the reminders by type in order
            # to show them in separate sections, and display them differently
            if isinstance(reminder.job.trigger, CronTrigger):
                cron_reminder_lines.append(line)
            elif isinstance(reminder.job.trigger, DateTrigger):
                one_shot_reminder_lines.append(line)
            elif isinstance(reminder.job.trigger, IntervalTrigger):
                interval_reminder_lines.append(line)

        if (
            not one_shot_reminder_lines
            and not cron_reminder_lines
            and not interval_reminder_lines
        ):
            await send_text_to_room(
                self.client,
                self.room.room_id,
                "*There are no reminders for this room.*",
            )
            return

        if one_shot_reminder_lines:
            output += "\n\n" + "**1️⃣ One-time Reminders**" + "\n\n"
            output += "\n".join(one_shot_reminder_lines)

        if cron_reminder_lines:
            output += "\n\n" + "**📅 Cron Reminders**" + "\n\n"
            output += "\n".join(cron_reminder_lines)

        if interval_reminder_lines:
            output += "\n\n" + "**🔁 Repeating Reminders**" + "\n\n"
            output += "\n".join(interval_reminder_lines)

        await send_text_to_room(self.client, self.room.room_id, output)

    @command_syntax("<reminder text>")
    async def _delete_reminder(self):
        """Delete a reminder via its reminder text"""
        reminder_text = " ".join(self.args)
        if not reminder_text:
            raise CommandSyntaxError()

        logger.debug("Known reminders: %s", REMINDERS)
        logger.debug(
            "Deleting reminder in room %s: %s", self.room.room_id, reminder_text
        )

        reminder = REMINDERS.get((self.room.room_id, reminder_text.upper()))
        if reminder:
            # Cancel the reminder and associated alarms
            reminder.cancel()

            text = "Reminder cancelled."
        else:
            text = f"Unknown reminder '{reminder_text}'."

        await send_text_to_room(self.client, self.room.room_id, text)

    @command_syntax("")
    async def _help(self):
        """Show the help text"""
        # Ensure we don't tell the user to use something other than their configured command
        # prefix
        c = CONFIG.command_prefix

        if not self.args:
            text = (
                f"Hello, I am a reminder bot! Use `{c}help reminders` "
                f"to view available commands."
            )
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]

        # Simply way to check for plurals
        if topic.startswith("reminder"):
            text = f"""
**Reminders**

Create an optionally recurring reminder that notifies the reminder creator:

```
{c}remindme|remind|r [every <recurring time>;] <start time>; <reminder text>
```

Create an optionally recurring reminder that notifies the whole room.
(Note that the bot will need appropriate permissions to mention
the room):

```
{c}remindroom|rr [every <recurring time>;] <start time>; <reminder text>
```

List all active reminders for a room:

```
{c}listreminders|list|lr|l
```

Cancel a reminder:

```
{c}cancelreminder|cancel|cr|c <reminder text>
```

**Alarms**

Create a reminder that will repeatedly sound every 5m after its usual
fire time. Otherwise, the syntax is the same as a reminder:

```
{c}alarmme|alarm|a [every <recurring time>;] <start time>; <reminder text>
```

or for notifying the whole room:

```
{c}alarmroom|ar [every <recurring time>;] <start time>; <reminder text>
```

Once firing, an alarm can be silenced with:

```
{c}silence|s [<reminder text>]
```

**Cron-tab Syntax**

If you need more complicated recurring reminders, you can make use of
cron-tab syntax:

```
{c}remindme|remind|r cron <min> <hour> <day of month> <month> <day of week>; <reminder text>
```

This syntax is supported by any `{c}remind...` or `{c}alarm...` command above.
"""
        else:
            # Unknown help topic
            return

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        """Computer says 'no'."""
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown help topic '{self.command}'. Try the 'help' command for more "
            f"information.",
        )
