import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

import dateparser
from nio import AsyncClient, MatrixRoom
from nio.events.room_events import RoomMessageText
from readabledelta import readabledelta

from matrix_reminder_bot.chat_functions import send_text_to_room
from matrix_reminder_bot.config import Config
from matrix_reminder_bot.errors import CommandError
from matrix_reminder_bot.reminder import ALARMS, REMINDERS, SCHEDULER, Reminder
from matrix_reminder_bot.storage import Storage

logger = logging.getLogger(__name__)


class Command(object):
    def __init__(
            self,
            client: AsyncClient,
            store: Storage,
            config: Config,
            command: str,
            room: MatrixRoom,
            event: RoomMessageText,
    ):
        """A command made by a user

        Args:
            client: The client to communicate to matrix with
            store: Bot storage
            config: Bot configuration parameters
            command: The command and arguments
            room: The room the command was sent in
            event: The event describing the command
        """
        self.client = client
        self.store = store
        self.config = config
        self.room = room
        self.event = event

        msg_without_prefix = command[len(config.command_prefix):]  # Remove the cmd prefix
        self.args = msg_without_prefix.split()  # Get a list of all items, split by spaces
        self.command = self.args.pop(0)  # Remove the first item and save as the command (ex. `remindme`)

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
        cron_tab, reminder_text = args_str.split(";", maxsplit=1)

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

        time_str, reminder_text = args_str.split(";", maxsplit=1)
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
            recurse_time_str = time_str[len("every"):].strip()
            logger.debug("Got recurring time: %s", recurse_time_str)

            # Convert the recurse time to a datetime object
            recurse_time = self._parse_str_to_time(recurse_time_str)

            # Generate a timedelta between now and the recurring time
            # `recurse_time` is guaranteed to always be in the future
            # Round datetime.now() to the nearest second for better time display
            current_time = datetime.now(tz=self.config.timezone).replace(microsecond=0)
            recurse_timedelta = recurse_time - current_time
            logger.debug("Recurring timedelta: %s", recurse_timedelta)

            # Extract the start time
            time_str, reminder_text = reminder_text.split(";", maxsplit=1)
            reminder_text = reminder_text.strip()

            logger.debug("Start time: %s", time_str)

        # Convert start time string to a datetime object
        time = self._parse_str_to_time(time_str)

        return time, reminder_text, recurse_timedelta

    def _parse_str_to_time(self, time_str: str) -> datetime:
        """Converts a human-readable, future time string to a datetime object

        Args:
            time_str: The time to convert

        Returns:
            datetime: A datetime if conversion was successful

        Raises:
            CommandError: if conversion was not successful, or time is in the past.
        """
        time = dateparser.parse(
            time_str,
            settings={
                "PREFER_DATES_FROM": "future",
                "RETURN_AS_TIMEZONE_AWARE": True,
                "TIMEZONE": self.config.timezone.zone,
            }
        )
        if not time:
            raise CommandError(f"The given time '{time_str}' is invalid.")

        # Disallow times in the past
        if time < datetime.now(tz=self.config.timezone):
            raise CommandError(f"The given time '{time_str}' is in the past.")

        # Round datetime object to the nearest second for nicer display
        time = time.replace(microsecond=0)

        return time

    async def _confirm_reminder(self, reminder: Reminder):
        """Sends a message to the room confirming the reminder is set

        Args:
            reminder: The Reminder to confirm
        """
        if reminder.cron_tab:
            # Special-case cron-style reminders. We currently don't do any special
            # parsing for them
            await send_text_to_room(
                self.client, self.room.room_id, "Ok, I will remind you!"
            )

            return

        # Convert a timedelta to a formatted time (ex. May 25 2020, 01:31)
        human_readable_start_time = reminder.start_time.strftime("%b %d %Y, %H:%M")

        # Get a textual representation of who will be notified by this reminder
        target = "you" if reminder.target_user else "everyone in the room"

        # Build the response string
        text = f"Ok, I will remind {target} on {human_readable_start_time}"

        if reminder.recurse_timedelta:
            # Inform the user how often their reminder will repeat
            human_readable_recurse_timedelta = readabledelta(reminder.recurse_timedelta)
            text += f", and again every {human_readable_recurse_timedelta}"

        # Add some punctuation
        text += "!"

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
                self.room.room_id, cron_tab, reminder_text,
            )
        else:
            start_time, reminder_text, recurse_timedelta = self._parse_reminder_command_args()

            logger.debug(
                "Creating reminder in room %s with delta %s: %s",
                self.room.room_id, recurse_timedelta, reminder_text,
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
        if self.command == "remindme":
            await self._remind_me()
        elif self.command == "remindroom":
            await self._remind_room()
        elif self.command == "alarmme":
            await self._alarm_me()
        elif self.command == "alarmroom":
            await self._alarm_room()
        elif self.command in ["listreminders", "listalarms"]:
            await self._list_reminders()
        elif self.command in [
            "delreminder", "deletereminder", "removereminder", "cancelreminder",
            "delalarm", "deletealarm", "removealarm", "cancelalarm",
        ]:
            await self._delete_reminder()
        elif self.command == "silence":
            await self._silence()
        elif self.command == "help":
            await self._help()

    async def _remind_me(self):
        """Set a reminder that will remind only the user who created it"""
        await self._remind(target=self.event.sender)

    async def _remind_room(self):
        """Set a reminder that will mention the room that the reminder was created in"""
        await self._remind()

    async def _alarm_me(self):
        """Set a reminder with an alarm that will remind only the user who created it"""
        await self._remind(target=self.event.sender, alarm=True)

    async def _alarm_room(self):
        """Set a reminder with an alarm that when fired will mention the room that the
        reminder was created in
        """
        await self._remind(alarm=True)

    async def _silence(self):
        """Silences an ongoing alarm"""
        # Attempt to find a reminder with an alarm currently going off
        reminder_text = " ".join(self.args)
        alarm_job = ALARMS.get((self.room.room_id, reminder_text.upper()))

        if alarm_job:
            # We found a reminder with an alarm
            ALARMS.pop((self.room.room_id, reminder_text.upper()), None)

            if SCHEDULER.get_job(alarm_job.id):
                # Silence the alarm
                alarm_job.remove()

            text = "Alarm silenced."
        else:
            # We didn't find an alarm that's currently firing...
            # Be helpful and check if this is a known reminder without an alarm
            # currently going off
            reminder = REMINDERS.get((self.room.room_id, reminder_text.upper()))
            if reminder:
                text = (
                    f"The reminder '{reminder_text}' does not currently have an "
                    f"alarm going off."
                )
            else:
                text = f"Unknown alarm or reminder '{reminder_text}'."

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _list_reminders(self):
        """Format and show known reminders for the current room

        Sends a message listing them in the following format:

            Reminders for this room:

            <start time>: <reminder text> [(every <recurring time>)] [(has alarm)]

        or if there are no reminders set:

            There are no reminders for this room.
        """
        reminders = []
        for reminder in REMINDERS.values():
            # Filter out reminders that don't belong to this room
            if reminder.room_id != self.room.room_id:
                continue

            # If this is a cron-style reminder, just print the cron tab
            if reminder.cron_tab:
                line = f"`{reminder.cron_tab}`: {reminder.reminder_text}"
                reminders.append(line)
                continue

            # Format the start time into something readable
            human_readable_start_time = reminder.start_time.strftime("%b %d %Y, %H:%M")

            line = f"{human_readable_start_time}: {reminder.reminder_text}"

            # Display a recurring time if available
            if reminder.recurse_timedelta:
                human_readable_recurse_timedelta = readabledelta(reminder.recurse_timedelta)

                line += f" (every {human_readable_recurse_timedelta})"

            # Note that an alarm exists if available
            if reminder.alarm:
                line += " (has alarm)"

            reminders.append(line)

        if reminders:
            text = "Reminders for this room:\n\n"
            text += "\n\n".join(reminders)
        else:
            text = "There are no reminders for this room."

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _delete_reminder(self):
        """Delete a reminder via its reminder text"""
        reminder_text = " ".join(self.args)

        logger.debug("Known reminders: %s", REMINDERS)
        logger.debug("Deleting reminder in room %s: %s", self.room.room_id, reminder_text)

        reminder = REMINDERS.get((self.room.room_id, reminder_text.upper()))
        if reminder:
            # Cancel the reminder
            reminder.cancel()

            text = "Reminder cancelled."
        else:
            text = f"Unknown reminder '{reminder_text}'."

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _help(self):
        """Show the help text"""
        if not self.args:
            text = ("Hello, I am a reminder bot! Use `help commands` to view available "
                    "commands.")
            await send_text_to_room(self.client, self.room.room_id, text)
            return

        topic = self.args[0]
        if topic == "commands":
            text = """
**Reminders**

Create an optionally recurring reminder that notifies the reminder creator:

```
!remindme [every <recurring time>;] <start time>; <reminder text>
```

Create an optionally recurring reminder that notifies the whole room.
(Note that the bot will need appropriate permissions to mention
the room):

```
!remindroom [every <recurring time>;] <start time>; <reminder text>
```

List all active reminders for a room:

```
!listreminders
```

Cancel a reminder:

```
!cancelreminder <reminder text>
```

**Alarms**

Create a reminder that will repeatedly sound every 5m after its usual
fire time. Otherwise, the syntax is the same as a reminder:

```
!alarmme [every <recurring time>;] <start time>; <reminder text>
```

or for notifying the whole room:

```
!alarmroom [every <recurring time>;] <start time>; <reminder text>
```

Once firing, an alarm can be silenced with:

```
!silence <reminder text>
```

**Cron-tab Syntax**

If you need more complicated recurring reminders, you can make use of
cron-tab syntax:

```
!remindme cron <min> <hour> <day of month> <month> <day of week>; <reminder text>
```

This syntax is supported by any `!remind...` or `!alarm...` command above.
"""
        else:
            text = "Unknown help topic!"

        await send_text_to_room(self.client, self.room.room_id, text)

    async def _unknown_command(self):
        """Computer says 'no'."""
        await send_text_to_room(
            self.client,
            self.room.room_id,
            f"Unknown command '{self.command}'. Try the 'help' command for more information.",
        )
