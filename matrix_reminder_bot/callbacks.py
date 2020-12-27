import logging

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
from matrix_reminder_bot.functions import send_text_to_room
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

    async def message(self, room: MatrixRoom, event: RoomMessageText):
        """Callback for when a message event is received"""
        # Extract the formatted message text, or the basic text if no formatting is available
        msg = event.formatted_body or event.body
        if not msg:
            return

        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        # Check whether this is a command
        #
        # We use event.body here as formatted bodies can start with <p> instead of the
        # command prefix
        if not event.body.startswith(CONFIG.command_prefix):
            return

        # It's possible to erraneous HTML tags to appear before the command prefix when
        # making use of event.formatted_body. Typically <p> when commands include newlines
        # This can cause the command code to break.
        #
        # We've already determined this is a command, so strip everything in the msg before
        # the first instance of the command prefix as a workaround
        prefix_index = msg.find(CONFIG.command_prefix)
        if prefix_index != -1:
            msg = msg[prefix_index:]
        else:
            # This formatted body doesn't contain the command prefix for some reason.
            # Use event.body instead then
            msg = event.body

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

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) == JoinError:
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
