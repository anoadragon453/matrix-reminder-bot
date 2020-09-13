# Changelog

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