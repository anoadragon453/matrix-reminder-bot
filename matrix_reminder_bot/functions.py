import logging
from typing import Callable

from markdown import markdown
from nio import SendRetryError

from matrix_reminder_bot.errors import CommandSyntaxError

logger = logging.getLogger(__name__)


async def send_text_to_room(
    client, room_id, message, notice=True, markdown_convert=True
):
    """Send text to a matrix room

    Args:
        client (nio.AsyncClient): The client to communicate to matrix with

        room_id (str): The ID of the room to send the message to

        message (str): The message content

        notice (bool): Whether the message should be sent with an "m.notice" message type
            (will not ping users)

        markdown_convert (bool): Whether to convert the message content to markdown.
            Defaults to true.
    """
    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
    }

    if markdown_convert:
        content["formatted_body"] = markdown(message)

    try:
        await client.room_send(
            room_id, "m.room.message", content, ignore_unverified_devices=True,
        )
    except SendRetryError:
        logger.exception(f"Unable to send message response to {room_id}")


def command_syntax(syntax: str):
    """Defines the syntax for a function, and informs the user if it is violated

    This function is intended to be used as a decorator, allowing command-handler
    functions to define the syntax that the user is supposed to use for the
    command arguments.

    The command function, passed to `outer`, can signal that this syntax has been
    violated by raising a CommandSyntaxError exception. This will then catch that
    exception and inform the user of the correct syntax for that command.

    Args:
        syntax: The syntax for the command that the user should follow
    """

    def outer(command_func: Callable):
        async def inner(self, *args, **kwargs):
            try:
                # Attempt to execute the command function
                await command_func(self, *args, **kwargs)
            except CommandSyntaxError:
                # The function indicated that there was a command syntax error
                # Inform the user of the correct syntax
                #
                # Grab the bot's configured command prefix, and the current
                # command's name from the `self` object passed to the command
                text = (
                    f"Invalid syntax. Please use "
                    f"`{self.config.command_prefix}{self.command} {syntax}`."
                )
                await send_text_to_room(self.client, self.room.room_id, text)

        return inner

    return outer
