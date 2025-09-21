# Changelog

## v0.4.0

This release has been simmering for a while. Rather than features, it brings some quality of life improvements to existing features.

Creating reminders is now more sane; you can't set a reminder for a few minutes ago any more and daylight saving time zone handling was improved to calculate the right offset year-round.
When inviting the bot to an existing room with recent messages, the bot will not anymore try to read and react to them, which would previously fail especially in encrypted rooms.

From the technical side, all dependencies have been updated, and Python 3.12 is now supported.
We have also added the GitHub container registry to our release CI, making releases available from both Docker Hub and GHCR at your choice.

Thanks to all who contributed to this release: [@svierne](https://github.com/svierne), [@th0mcat](https://github.com/th0mcat), [@cyb3rko](https://github.com/cyb3rko)!

### Features

* Add support for Python 3.12 ([#112](https://github.com/anoadragon453/matrix-reminder-bot/pull/112), [#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Ignore messages that were sent before the bot joined ([#141](https://github.com/anoadragon453/matrix-reminder-bot/pull/141))
* Improve formatting of cron reminders when listing ([#165](https://github.com/anoadragon453/matrix-reminder-bot/pull/165))
* List currently firing alarms ([#162](https://github.com/anoadragon453/matrix-reminder-bot/pull/162))
* Require setting a non-empty password ([#142](https://github.com/anoadragon453/matrix-reminder-bot/pull/142))
* Provide container images additionally via GHCR ([#132](https://github.com/anoadragon453/matrix-reminder-bot/pull/132), [#135](https://github.com/anoadragon453/matrix-reminder-bot/pull/135))

### Bugfixes

* Reminders can't be set in the recent past ([#145](https://github.com/anoadragon453/matrix-reminder-bot/pull/145), [#160](https://github.com/anoadragon453/matrix-reminder-bot/pull/160))
* Calculate current UTC offset with correct daylight saving time zone ([#147](https://github.com/anoadragon453/matrix-reminder-bot/pull/147))

### Documentation

* Add TWIM to release instructions ([a74b62e](https://github.com/anoadragon453/matrix-reminder-bot/commit/a74b62eb2f8d3ce792d4212d2ee6866df4c11711))
* Update container documentation ([#132](https://github.com/anoadragon453/matrix-reminder-bot/pull/132))
* Fix typo in blocklist config ([#171](https://github.com/anoadragon453/matrix-reminder-bot/pull/171)) - contributed by [@svierne](https://github.com/svierne)
* Prefer the native Python venv setup ([#181](https://github.com/anoadragon453/matrix-reminder-bot/pull/181))
* Reference MDAD installation method ([#185](https://github.com/anoadragon453/matrix-reminder-bot/pull/185))
* List related projects (#97)
* Add iOS shortcuts ([#144](https://github.com/anoadragon453/matrix-reminder-bot/pull/144)) - contributed by [@th0mcat](https://github.com/th0mcat)
* Update the badge to use the room summary API ([#192](https://github.com/anoadragon453/matrix-reminder-bot/pull/192)) - contributed by [@cyb3rko](https://github.com/cyb3rko)

### Internal Changes

* Make functions static ([#146](https://github.com/anoadragon453/matrix-reminder-bot/pull/146))
* Add issue template ([#179](https://github.com/anoadragon453/matrix-reminder-bot/pull/179))
* Only run publishing CI on upstream repo ([#201](https://github.com/anoadragon453/matrix-reminder-bot/pull/201))
* Bump `matrix-nio` to 0.24.0 ([#112](https://github.com/anoadragon453/matrix-reminder-bot/pull/112))
* Bump CI to Python 3.12 ([#163](https://github.com/anoadragon453/matrix-reminder-bot/pull/163))
* Bump `flake8` to 7.3.0 ([#133](https://github.com/anoadragon453/matrix-reminder-bot/pull/133), [#183](https://github.com/anoadragon453/matrix-reminder-bot/pull/183), [#188](https://github.com/anoadragon453/matrix-reminder-bot/pull/188), [#198](https://github.com/anoadragon453/matrix-reminder-bot/pull/198), [#199](https://github.com/anoadragon453/matrix-reminder-bot/pull/199))
* Bump `flake8-comprehensions` to 3.17.0 ([#187](https://github.com/anoadragon453/matrix-reminder-bot/pull/187), [#191](https://github.com/anoadragon453/matrix-reminder-bot/pull/191), [#203](https://github.com/anoadragon453/matrix-reminder-bot/pull/203))
* Bump `libolm` to 3.2.16 ([#112](https://github.com/anoadragon453/matrix-reminder-bot/pull/112))
* Bump `black` to 25.9.0 ([#140](https://github.com/anoadragon453/matrix-reminder-bot/pull/140), [#143](https://github.com/anoadragon453/matrix-reminder-bot/pull/143), [#152](https://github.com/anoadragon453/matrix-reminder-bot/pull/152), [#170](https://github.com/anoadragon453/matrix-reminder-bot/pull/170), [#173](https://github.com/anoadragon453/matrix-reminder-bot/pull/173), [#178](https://github.com/anoadragon453/matrix-reminder-bot/pull/178), [#189](https://github.com/anoadragon453/matrix-reminder-bot/pull/189), [#190](https://github.com/anoadragon453/matrix-reminder-bot/pull/190), [#194](https://github.com/anoadragon453/matrix-reminder-bot/pull/194), [#204](https://github.com/anoadragon453/matrix-reminder-bot/pull/204))
* Bump `Markdown` to 3.5.2 ([#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Bump `PyYAML` to 6.0.1 ([#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Bump `dateparser` to 1.2.0 ([#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Bump `apscheduler` to 3.10.4 ([#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Bump `pytz` to 2024.01 ([#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Bump `arrow` to 1.3.0 ([#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Bump `psychopg2` to 2.9.9 ([#151](https://github.com/anoadragon453/matrix-reminder-bot/pull/151))
* Bump `isort` to 6.0.1 ([#197](https://github.com/anoadragon453/matrix-reminder-bot/pull/197))
* Configure Dependabot to update GitHub actions ([#131](https://github.com/anoadragon453/matrix-reminder-bot/pull/131))
* Bump `actions/setup-python` to 6 ([#134](https://github.com/anoadragon453/matrix-reminder-bot/pull/134), [#202](https://github.com/anoadragon453/matrix-reminder-bot/pull/202))
* Bump `actions/checkout` to 5 ([#200](https://github.com/anoadragon453/matrix-reminder-bot/pull/200))
* Bump `docker/build-push-action` to 6 ([#184](https://github.com/anoadragon453/matrix-reminder-bot/pull/184))

## v0.3.0

This release brings you a new feature thanks to @svierne, who added allowlist and blocklist!
You can use either or both at the same time, giving you lots of options to manage access to your bot instance across the Matrix federation, and bringing a step up in security for everyone hosting an instance.
Both lists default to being disabled for backward compatibility with previous versions.
To make use of this feature, add the relevant new `allowlist` and `blocklist` sections from the updated [sample.config.yaml](https://github.com/anoadragon453/matrix-reminder-bot/blob/v0.3.0/sample.config.yaml) to your config.yaml.

Further, this release brings improved support for the Matrix specification's new `m.mentions`, fixes for missing and superfluous pills, updated dependencies, and we spent some time adding a lot of CI.

More details below:

### Features

* Implement allowlist and blocklist https://github.com/anoadragon453/matrix-reminder-bot/pull/120 by @svierne.
* Support Matrix v1.9 mentions https://github.com/anoadragon453/matrix-reminder-bot/pull/124 by @svierne.

### Bugfixes

* Add pills in missing places and remove invalid pills for room pings https://github.com/anoadragon453/matrix-reminder-bot/pull/124 by @svierne.
* Fixup for room pills https://github.com/anoadragon453/matrix-reminder-bot/pull/129.

### Documentation

* Update contributing guidelines https://github.com/anoadragon453/matrix-reminder-bot/pull/116.

### Internal Changes

* Add automatic Python dependency version update checking dependabot config https://github.com/anoadragon453/matrix-reminder-bot/pull/103.
* Bump `black` https://github.com/anoadragon453/matrix-reminder-bot/pull/103, https://github.com/anoadragon453/matrix-reminder-bot/pull/105, https://github.com/anoadragon453/matrix-reminder-bot/pull/113, https://github.com/anoadragon453/matrix-reminder-bot/pull/121.
* Bump `flake8` https://github.com/anoadragon453/matrix-reminder-bot/pull/106.
* Bump `isort` https://github.com/anoadragon453/matrix-reminder-bot/pull/107, https://github.com/anoadragon453/matrix-reminder-bot/pull/117, https://github.com/anoadragon453/matrix-reminder-bot/pull/119.
* Bump `flake8-comprehensions` https://github.com/anoadragon453/matrix-reminder-bot/pull/104.
* Bump the version of Python in the CI and docker image to 3.11 https://github.com/anoadragon453/matrix-reminder-bot/pull/108.
* Bump `libolm` to 3.2.15 https://github.com/anoadragon453/matrix-reminder-bot/pull/108.
* Add CI building containers with all supported Python versions and both amd64 and arm64 for PRs, pushes to master branch (`dev` tag), and releases. See https://github.com/anoadragon453/matrix-reminder-bot/pkgs/container/matrix-reminder-bot for development artifacts. https://github.com/anoadragon453/matrix-reminder-bot/pull/108, https://github.com/anoadragon453/matrix-reminder-bot/pull/110, https://github.com/anoadragon453/matrix-reminder-bot/pull/125.
* Bump GitHub actions https://github.com/anoadragon453/matrix-reminder-bot/pull/111.


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
