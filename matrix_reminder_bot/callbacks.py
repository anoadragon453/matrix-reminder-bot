import logging
import re
from typing import List

from nio import (
    AsyncClient,
    InviteMemberEvent,
    JoinError,
    MatrixRoom,
    MegolmEvent,
    RoomMessageText,
)

from matrix_reminder_bot.bot_commands import Command
from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.errors import CommandError
from matrix_reminder_bot.functions import is_allowed_user, send_text_to_room
from matrix_reminder_bot.storage import Storage

logger = logging.getLogger(__name__)


class Callbacks(object):
    """Callback methods that fire on certain matrix events

    Args:
        client: nio client used to interact with matrix
        store: Bot storage
    """

    def __init__(self, client: AsyncClient, store: Storage):
        self.client = client
        self.store = store

    @staticmethod
    def str_strip(s: str, phrases: List[str]) -> str:
        """
        Strip instances of a string in leading and trailing positions around another string.
        Like str.rstrip but with strings instead of individual characters.
        Also runs str.strip on s.

        Args:
            s: The string to strip.
            phrases: A list of strings to strip from s.
        """
        # Strip the string of whitespace
        s = s.strip()

        for phrase in phrases:
            # Use a regex to strip leading strings from another string
            #
            # We use re.S to treat the input text as one line (aka not strip leading
            # phrases from every line of the message.
            match = re.match(f"({phrase})*(.*)", s, flags=re.S)

            # Extract the text between the parentheses in the pattern above
            # Note that the above pattern is guaranteed to find a match, even with an empty str
            s = match.group(2)

            # Now attempt to strip trailing strings.
            match = re.match(f"(.*)({phrase})$", s, flags=re.S)
            if match:
                s = match.group(1)

        # After attempting to strip leading and trailing phrases from the string, return it
        return s

    async def message(self, room: MatrixRoom, event: RoomMessageText):
        """Callback for when a message event is received"""
        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        # Ignore messages from the past
        join_time = 0
        state = await self.client.room_get_state(room.room_id)
        for membership in state.events:
            if (
                membership.get("type") == "m.room.member"
                and membership.get("state_key") == self.client.user_id
            ):
                join_time = membership.get("origin_server_ts", 0)
        if join_time > event.server_timestamp:
            return

        # Ignore messages from disallowed users
        if not is_allowed_user(event.sender):
            logger.debug(
                f"Ignoring event {event.event_id} in room {room.room_id} as the sender {event.sender} is not allowed."
            )
            return

        # Ignore broken events
        if not event.body:
            return

        # We do some stripping just to remove any surrounding formatting
        formatting_chars = ["<p>", "\\n", "</p>"]
        body = self.str_strip(event.body, formatting_chars)
        formatted_body = (
            self.str_strip(event.formatted_body, formatting_chars)
            if event.formatted_body
            else None
        )

        # Use the formatted message text, or the basic text if no formatting is available
        msg = formatted_body or body
        if not msg:
            logger.info("No msg!")
            return

        # Check whether this is a command
        #
        # We use event.body here as formatted bodies can start with <p> instead of the
        # command prefix
        if not body.startswith(CONFIG.command_prefix):
            return

        logger.debug("Command received: %s", msg)

        # Assume this is a command and attempt to process
        command = Command(self.client, self.store, msg, room, event)

        try:
            await command.process()
        except CommandError as e:
            # An expected error occurred. Inform the user
            msg = f"Error: {e.msg}"
            await send_text_to_room(self.client, room.room_id, msg)

            # Print traceback
            logger.exception("CommandError while processing command:")
        except Exception as e:
            # An unknown error occurred. Inform the user
            msg = f"An unknown error occurred: {e}"
            await send_text_to_room(self.client, room.room_id, msg)

            # Print traceback
            logger.exception("Unknown error while processing command:")

    async def invite(self, room: MatrixRoom, event: InviteMemberEvent):
        """Callback for when an invite is received. Join the room specified in the invite"""
        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")

        # Don't respond to invites from disallowed users
        if not is_allowed_user(event.sender):
            logger.debug(f"{event.sender} is not allowed, not responding to invite.")
            return

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) is JoinError:
                logger.error(
                    f"Error joining room {room.room_id} (attempt %d): %s",
                    attempt,
                    result.message,
                )
            else:
                logger.info(f"Joined {room.room_id}")
                break

    async def decryption_failure(self, room: MatrixRoom, event: MegolmEvent):
        """Callback for when an event fails to decrypt. Inform the user"""
        logger.error(
            f"Failed to decrypt event '{event.event_id}' in room '{room.room_id}'!"
            f"\n\n"
            f"Tip: try using a different device ID in your config file and restart."
            f"\n\n"
            f"If all else fails, delete your store directory and let the bot recreate "
            f"it (your reminders will NOT be deleted, but the bot may respond to existing "
            f"commands a second time)."
        )

        user_msg = (
            "Unable to decrypt this message. "
            "Check whether you've chosen to only encrypt to trusted devices."
        )

        await send_text_to_room(
            self.client,
            room.room_id,
            user_msg,
            reply_to_event_id=event.event_id,
        )
