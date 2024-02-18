import unittest
from datetime import datetime, timedelta
from unittest import IsolatedAsyncioTestCase
from unittest.mock import MagicMock, patch, AsyncMock

from matrix_reminder_bot.bot_commands import Command

USER = "@alice:example.org"
REMINDER_TEXT = "test reminder text"
START_TIME = datetime(2024, 2, 17, 23, 10)
RECURSE_TIMEDELTA = timedelta(hours=1)
CRON_TAB = "0 * * * *"


class BaseTestBotCommands(IsolatedAsyncioTestCase):

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
        self.c._parse_reminder_command_args_for_cron = MagicMock(return_value=(CRON_TAB, REMINDER_TEXT))
        self.c._confirm_reminder = AsyncMock()
        self._overrides()

    @patch("matrix_reminder_bot.bot_commands.Reminder")
    async def asyncSetUp(self, mock_reminder_constructor) -> None:
        await self._run_test()

        # validate result
        reminder = mock_reminder_constructor.call_args
        self.args = reminder.args
        self.kwargs = reminder.kwargs

    def _overrides(self) -> None:
        pass

    async def _run_test(self) -> None:
        pass


class TestBotCommandsRemindMe(BaseTestBotCommands):

    async def _run_test(self) -> None:
        await self.c._remind_me()

    async def test_target_user(self) -> None:
        assert self.kwargs["target_user"] == USER

    async def test_alarm(self) -> None:
        assert not self.kwargs["alarm"]

    async def test_cron_tab(self) -> None:
        assert self.kwargs["cron_tab"] is None

    async def test_start_time(self) -> None:
        assert self.kwargs["start_time"] == START_TIME

    async def test_recurse_timedelta(self) -> None:
        assert self.kwargs["recurse_timedelta"] is None

    async def test_reminder_text(self) -> None:
        assert self.args[3] == REMINDER_TEXT


class TestBotCommandsRemindRoom(TestBotCommandsRemindMe):

    async def _run_test(self) -> None:
        await self.c._remind_room()

    async def test_target_user(self) -> None:
        assert self.kwargs["target_user"] is None


class TestBotCommandsAlarmMe(TestBotCommandsRemindMe):

    async def _run_test(self) -> None:
        await self.c._alarm_me()

    async def test_alarm(self) -> None:
        assert self.kwargs["alarm"]


class TestBotCommandsAlarmRoom(TestBotCommandsRemindMe):

    async def _run_test(self) -> None:
        await self.c._alarm_room()

    async def test_target_user(self) -> None:
        assert self.kwargs["target_user"] is None

    async def test_alarm(self) -> None:
        assert self.kwargs["alarm"]


class TestBotCommandsRemindMeEvery(TestBotCommandsRemindMe):

    def _overrides(self) -> None:
        self.c._parse_reminder_command_args = MagicMock(return_value=(START_TIME, REMINDER_TEXT, RECURSE_TIMEDELTA))

    async def _run_test(self) -> None:
        await self.c._remind_me()

    async def test_recurse_timedelta(self) -> None:
        assert self.kwargs["recurse_timedelta"] == RECURSE_TIMEDELTA


class TestBotCommandsRemindMeEveryRoom(TestBotCommandsRemindMeEvery):

    async def _run_test(self) -> None:
        await self.c._remind_room()

    async def test_target_user(self) -> None:
        assert self.kwargs["target_user"] is None


class TestBotCommandsAlarmMeEvery(TestBotCommandsRemindMeEvery):

    async def _run_test(self) -> None:
        await self.c._alarm_me()

    async def test_alarm(self) -> None:
        assert self.kwargs["alarm"]


class TestBotCommandsAlarmMeEveryRoom(TestBotCommandsRemindMeEvery):

    async def _run_test(self) -> None:
        await self.c._alarm_room()

    async def test_target_user(self) -> None:
        assert self.kwargs["target_user"] is None

    async def test_alarm(self) -> None:
        assert self.kwargs["alarm"]


class TestBotCommandsRemindMeCron(TestBotCommandsRemindMe):

    def _overrides(self) -> None:
        self.c.args = ["cron"]

    async def _run_test(self) -> None:
        await self.c._remind_me()

    async def test_cron_tab(self) -> None:
        assert self.kwargs["cron_tab"] == CRON_TAB

    async def test_start_time(self) -> None:
        assert self.kwargs["start_time"] is None


class TestBotCommandsRemindMeCronRoom(TestBotCommandsRemindMeCron):

    async def _run_test(self) -> None:
        await self.c._remind_room()

    async def test_target_user(self) -> None:
        assert self.kwargs["target_user"] is None


class TestBotCommandsAlarmMeCron(TestBotCommandsRemindMeCron):

    async def _run_test(self) -> None:
        await self.c._alarm_me()

    async def test_alarm(self) -> None:
        assert self.kwargs["alarm"]


class TestBotCommandsAlarmMeCronRoom(TestBotCommandsRemindMeCron):

    async def _run_test(self) -> None:
        await self.c._alarm_room()

    async def test_target_user(self) -> None:
        assert self.kwargs["target_user"] is None

    async def test_alarm(self) -> None:
        assert self.kwargs["alarm"]


if __name__ == "__main__":
    unittest.main()
