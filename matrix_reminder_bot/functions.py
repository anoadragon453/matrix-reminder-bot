import logging
from typing import Callable, Optional

from markdown import markdown
from nio import AsyncClient, SendRetryError

from matrix_reminder_bot.config import CONFIG
from matrix_reminder_bot.errors import CommandSyntaxError

logger = logging.getLogger(__name__)


async def send_text_to_room(
    client: AsyncClient,
    room_id: str,
    message: str,
    notice: bool = True,
    markdown_convert: bool = True,
    reply_to_event_id: Optional[str] = None,
    mentions_room: bool = False,
    mentions_user_ids: Optional[list[str]] = None,
):
    """Send text to a matrix room.

    Args:
        client: The client to communicate to matrix with.

        room_id: The ID of the room to send the message to.

        message: The message content.

        notice: Whether the message should be sent with an "m.notice" message type
            (will not ping users).

        markdown_convert: Whether to convert the message content to markdown.
            Defaults to true.

        reply_to_event_id: Whether this message is a reply to another event. The event
            ID this is message is a reply to.

        mentions_room: Whether or not this message mentions the whole room.
            Defaults to false.

        mentions_user_ids: An optional list of MXIDs this message mentions.
    """

    # Determine whether to ping room members or not
    msgtype = "m.notice" if notice else "m.text"

    content = {
        "msgtype": msgtype,
        "format": "org.matrix.custom.html",
        "body": message,
        "m.mentions": {},
    }

    if markdown_convert:
        content["formatted_body"] = markdown(message)

    if reply_to_event_id:
        content["m.relates_to"] = {"m.in_reply_to": {"event_id": reply_to_event_id}}

    if mentions_room:
        content["m.mentions"]["room"] = True

    if mentions_user_ids is not None:
        content["m.mentions"]["user_ids"] = mentions_user_ids

    try:
        await client.room_send(
            room_id,
            "m.room.message",
            content,
            ignore_unverified_devices=True,
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
                    f"`{CONFIG.command_prefix}{self.command} {syntax}`. "
                    f"Use `!help reminders` to see all help."
                )
                await send_text_to_room(self.client, self.room.room_id, text)

        return inner

    return outer


def make_pill(user_id: str, displayname: str = None) -> str:
    """Convert a user ID (and optionally a display name) to a formatted user 'pill'

    Args:
        user_id: The MXID of the user.
        displayname: An optional displayname. Clients like Element will figure out the
            correct display name no matter what, but other clients may not.

    Returns:
        The formatted user pill.
    """
    if not displayname:
        # Use the user ID as the displayname if not provided
        displayname = user_id

    return f'<a href="https://matrix.to/#/{user_id}">{displayname}</a>'


def is_allowed_user(user_id: str) -> bool:
    """Returns if the bot is allowed to interact with the given user

    Args:
        user_id: The MXID of the user.

    Returns:
        True, if the bot is allowed to interact with the given user.
    """
    allowed = not CONFIG.allowlist_enabled

    if CONFIG.allowlist_enabled:
        for regex in CONFIG.allowlist_regexes:
            if regex.fullmatch(user_id):
                allowed = True
                break

    if CONFIG.blocklist_enabled:
        for regex in CONFIG.blocklist_regexes:
            if regex.fullmatch(user_id):
                allowed = False
                break

    return allowed
