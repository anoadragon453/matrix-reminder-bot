# Changelog

## v0.3.0

This release brings you a new feature thanks to @svierne, who added allowlist and blocklist!
You can use either or both at the same time, giving you lots of options to manage access to your bot instance across the Matrix federation, and bringing a step up in security for everyone hosting an instance.
Both lists default to being disabled for backward compatibility with previous versions.
To make use of this feature, add the relevant new `allowlist` and `blocklist` sections from the updated [sample.config.yaml](https://github.com/anoadragon453/matrix-reminder-bot/blob/v0.3.0/sample.config.yaml) to your config.yaml.

Further, this release brings improved support for the Matrix specification's new `m.mentions`, fixes for missing and superfluous pills, updated dependencies, and we spent some time adding a lot of CI.

More details below:

### Features

* Implement allowlist and blocklist https://github.com/anoadragon453/matrix-reminder-bot/pull/120 by @svierne
* Support Matrix v1.9 mentions https://github.com/anoadragon453/matrix-reminder-bot/pull/124 by @svierne

### Bugfixes

* Add pills in missing places and remove invalid pills for room pings https://github.com/anoadragon453/matrix-reminder-bot/pull/124 by @svierne
* Fixup for room pills https://github.com/anoadragon453/matrix-reminder-bot/pull/129

### Documentation

* Update contributing guidelines https://github.com/anoadragon453/matrix-reminder-bot/pull/116

### Internal Changes

* Add automatic Python dependency version update checking dependabot config https://github.com/anoadragon453/matrix-reminder-bot/pull/103
* Bump `black` https://github.com/anoadragon453/matrix-reminder-bot/pull/103, https://github.com/anoadragon453/matrix-reminder-bot/pull/105, https://github.com/anoadragon453/matrix-reminder-bot/pull/113, https://github.com/anoadragon453/matrix-reminder-bot/pull/121
* Bump `flake8` https://github.com/anoadragon453/matrix-reminder-bot/pull/106, 
* Bump `isort` https://github.com/anoadragon453/matrix-reminder-bot/pull/107, https://github.com/anoadragon453/matrix-reminder-bot/pull/117, https://github.com/anoadragon453/matrix-reminder-bot/pull/119
* Bump `flake8-comprehensions` https://github.com/anoadragon453/matrix-reminder-bot/pull/104
* Bump the version of Python in the CI and docker image to 3.11 https://github.com/anoadragon453/matrix-reminder-bot/pull/108
* Bump `libolm` to 3.2.15 https://github.com/anoadragon453/matrix-reminder-bot/pull/108
* Add CI building containers with all supported Python versions and both amd64 and arm64 for PRs, pushes to master branch (`dev` tag), and releases. See https://github.com/anoadragon453/matrix-reminder-bot/pkgs/container/matrix-reminder-bot for development artifacts. https://github.com/anoadragon453/matrix-reminder-bot/pull/108, https://github.com/anoadragon453/matrix-reminder-bot/pull/110, https://github.com/anoadragon453/matrix-reminder-bot/pull/125
* Bump GitHub actions https://github.com/anoadragon453/matrix-reminder-bot/pull/111


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
