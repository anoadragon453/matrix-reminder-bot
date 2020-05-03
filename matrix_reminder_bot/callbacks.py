import logging

from nio import AsyncClient, JoinError

from matrix_reminder_bot.bot_commands import Command
from matrix_reminder_bot.chat_functions import send_text_to_room
from matrix_reminder_bot.config import Config
from matrix_reminder_bot.errors import CommandError
from matrix_reminder_bot.storage import Storage

logger = logging.getLogger(__name__)


class Callbacks(object):
    """Callback methods that fire on certain matrix events

    Args:
        client: nio client used to interact with matrix
        store: Bot storage
        config: Bot configuration parameters
    """

    def __init__(
            self,
            client: AsyncClient,
            store: Storage,
            config: Config,
    ):
        self.client = client
        self.store = store
        self.config = config
        self.command_prefix = config.command_prefix

    async def message(self, room, event):
        """Callback for when a message event is received

        Args:
            room (nio.rooms.MatrixRoom): The room the event came from

            event (nio.events.room_events.RoomMessageText): The event defining the message

        """
        # Extract the message text
        msg = event.body

        # Ignore messages from ourselves
        if event.sender == self.client.user:
            return

        logger.debug(
            f"Bot message received for room {room.display_name} | "
            f"{room.user_name(event.sender)}: {msg}"
        )

        # Check whether this is a command
        if not msg.startswith(self.command_prefix):
            logger.debug("Message did not start with %s", self.command_prefix)
            return

        logger.debug("Command received: %s", msg)

        # Assume this is a command and attempt to process
        command = Command(
            self.client,
            self.store,
            self.config,
            msg,
            room,
            event,
        )

        try:
            await command.process()
        except CommandError as e:
            # An expected error occurred. Inform the user
            msg = f"Error: {e.msg}"
            await send_text_to_room(self.client, room.room_id, msg)
        except Exception as e:
            # An unknown error occurred. Inform the user
            msg = f"An unknown error occurred: {e}"
            await send_text_to_room(self.client, room.room_id, msg)

    async def invite(self, room, event):
        """Callback for when an invite is received. Join the room specified in the invite"""
        logger.debug(f"Got invite to {room.room_id} from {event.sender}.")

        # Attempt to join 3 times before giving up
        for attempt in range(3):
            result = await self.client.join(room.room_id)
            if type(result) == JoinError:
                logger.error(
                    f"Error joining room {room.room_id} (attempt %d): %s",
                    attempt, result.message,
                )
            else:
                logger.info(f"Joined {room.room_id}")
                break
