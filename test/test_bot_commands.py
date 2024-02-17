import unittest
from datetime import datetime
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch, AsyncMock

from matrix_reminder_bot.bot_commands import Command

USER = "@alice:example.org"
REMINDER_TEXT = "test reminder text"
START_TIME = datetime(2024, 2, 17, 23, 10)


class TestBotCommands(IsolatedAsyncioTestCase):

    def setUp(self) -> None:
        self.mock_client = MagicMock()
        self.mock_store = MagicMock()
        self.mock_store.store_reminder = MagicMock()
        self.mock_command = MagicMock()
        self.mock_room = MagicMock()
        self.mock_event = MagicMock()
        self.mock_event.sender = USER

        self.c = Command(client=self.mock_client, store=self.mock_store, command=self.mock_command, room=self.mock_room,
                         event=self.mock_event)
        self.c._parse_reminder_command_args = MagicMock(return_value=(START_TIME, REMINDER_TEXT, None))
        self.c._confirm_reminder = AsyncMock()

    async def test_bot_commands(self) -> None:
        pass


class TestBotCommandsRemindMe(TestBotCommands):

    @patch("matrix_reminder_bot.bot_commands.Reminder")
    async def test_remind_me(self, mock_reminder_constructor) -> None:
        # run test
        await self.c._remind_me()

        # validate result
        reminder = mock_reminder_constructor.call_args
        args = reminder.args
        kwargs = reminder.kwargs
        assert kwargs["target_user"] == USER
        assert not kwargs["alarm"]
        assert kwargs["cron_tab"] is None
        assert kwargs["start_time"] == START_TIME
        assert kwargs["recurse_timedelta"] is None
        assert args[3] == REMINDER_TEXT


class TestBotCommandsRemindRoom(TestBotCommands):

    @patch("matrix_reminder_bot.bot_commands.Reminder")
    async def test_remind_room(self, mock_reminder_constructor) -> None:
        # run test
        await self.c._remind_room()

        # validate result
        reminder = mock_reminder_constructor.call_args
        args = reminder.args
        kwargs = reminder.kwargs
        assert kwargs["target_user"] is None
        assert not kwargs["alarm"]
        assert kwargs["cron_tab"] is None
        assert kwargs["start_time"] == START_TIME
        assert kwargs["recurse_timedelta"] is None
        assert args[3] == REMINDER_TEXT


class TestBotCommandsAlarmMe(TestBotCommands):

    @patch("matrix_reminder_bot.bot_commands.Reminder")
    async def test_alarm_me(self, mock_reminder_constructor) -> None:
        # run test
        await self.c._alarm_me()

        # validate result
        reminder = mock_reminder_constructor.call_args
        args = reminder.args
        kwargs = reminder.kwargs
        assert kwargs["target_user"] == USER
        assert kwargs["alarm"]
        assert kwargs["cron_tab"] is None
        assert kwargs["start_time"] == START_TIME
        assert kwargs["recurse_timedelta"] is None
        assert args[3] == REMINDER_TEXT


class TestBotCommandsAlarmRoom(TestBotCommands):

    @patch("matrix_reminder_bot.bot_commands.Reminder")
    async def test_alarm_room(self, mock_reminder_constructor) -> None:
        # run test
        await self.c._alarm_room()

        # validate result
        reminder = mock_reminder_constructor.call_args
        args = reminder.args
        kwargs = reminder.kwargs
        assert kwargs["target_user"] is None
        assert kwargs["alarm"]
        assert kwargs["cron_tab"] is None
        assert kwargs["start_time"] == START_TIME
        assert kwargs["recurse_timedelta"] is None
        assert args[3] == REMINDER_TEXT


if __name__ == "__main__":
    unittest.main()
