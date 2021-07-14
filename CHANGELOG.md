# Changelog

## v0.2.1

Quick patch to bump `matrix-nio` to version `>=0.18`, as otherwise that is required for the bot to work with Synapse 1.38+.
See https://github.com/anoadragon453/matrix-reminder-bot/issues/86 for details on the bug.

Otherwise, full changelog below:

### Features

* Improve the '!listreminders' output.
* Add one-letter aliases to each command.
* Add 'remind' as an alias for the 'remindme' command.
* Use a pill when reminding a user.

### Bugfixes

* Timezone errors due to daylight savings times will be corrected after a bridge restart.
* Prevent timezone-related errors when creating a reminder.
* Better parsing of reminders that have newlines.

### Documentation

* Add release instructions.

### Internal Changes

* Update setup.py to indicate Python 3.6+ is required.
* Bump minimum version of matrix-nio to 0.18.
* Bump the version of libolm to 3.2.4.
* Bump the version of Python in the CI to 3.9.


## v0.2.0

Lots of changes, updates and polishing! Find the list below:

### Features

* Better support for command prefixes other than the default `!`.
* Just writing `!silence` now silences the currently active alarm.
* The bot will now print the correct syntax of a command if the user fails to follow it.
* The bot will reply to events if it cannot decrypt them, as well as offer helpful tips that both the user and bot operator can try to fix things.

### Bugfixes

* Timezones. They should finally work correctly! ...no 100% guarantees though.
* Alarms were a bit broken. They're fixed now.
* Fix commands with formatting and newlines not being picked up by the bot.
* Fix non-latin characters preventing reminders from being deleted.

### Internal changes

* Add a dev-optimised Dockerfile for quicker iteration during development.
* Better wording revolving alarms. They're just reminders that alarm repeatedly when they go off.
* Log why the bot is unable to start.
* Don't print "Unknown help topic" in case the user is trying to ask another bot for help.
* The config dict is now a singleton.
* Type hints everywhere!

The minimum Python version is now 3.6.

## v0.1.0

Initial release, all known bugs squashed!
