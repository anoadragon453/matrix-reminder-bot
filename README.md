# Matrix Reminder Bot

![example of interacting with the bot](screenshot.png)

A short bot written with [nio-template](https://github.com/anoadragon453/nio-template).

## Features

* Set reminders
* Have the bot remind you or the whole room
* Reminders persist between bot restarts
* Alarms - persistent notifications for a reminder until silenced
* Supports end-to-end encrypted rooms

## Install

matrix-reminder-bot requires
[matrix-nio](https://github.com/matrix-org/matrix-nio), which supports
participation in end-to-end encryption rooms! To do so, it makes use of the
[libolm](https://gitlab.matrix.org/matrix-org/olm) C library.  This library
must be installed to allow for end-to-end encryption functionality, and
unfortunately it is *also* required for functional message polling, so it is
practically a hard required for this program.

Unfortunately, installation of this library can be non-trivial on some
platforms. However, with the power of docker, dependencies can be handled with
little fuss, and it is thus the recommended method of installing
`matrix-reminder-bot`. Native installation instructions are also provided, but
be aware that they are more complex.

### Docker

Follow the docker [installation instructions](docker/README.md#setup).

### Native installation

#### Install libolm

You can install [libolm](https://gitlab.matrix.org/matrix-org/olm) from source,
or alternatively, check your system's package manager. Note that version
`3.0.0` or greater is required.

**(Optional) postgres development headers**

If you want to use postgres as a database backend (see the Configuration
section for more details), you'll need to install postgres development
headers:

Debian/Ubuntu:

```
sudo apt install libpq-dev libpq5
```

Arch:

```
sudo pacman -S postgresql-libs
```

#### Install Python dependencies

Create and activate a Python 3 virtual environment:

```
virtualenv -p python3 env
source env/bin/activate
```

Install python dependencies:

```
pip install matrix-reminder-bot
```

If you want to use postgres as a database backend (see the Configuration
section for more details), use the following command to install postgres
dependencies alongside those that are necessary:

```
pip install "matrix-reminder-bot[postgres]"
```

## Configuration

Copy the sample configuration file to a new `config.yaml` file.

```
cp sample.config.yaml config.yaml
```

Edit the config file. The `matrix` section must be modified at least.

#### (Optional) Set up a Postgres database

By default, matrix-reminder-bot uses SQLite as its storage backend. This is
fine for a few hundred users, but if you plan to support a much higher volume
of requests, you may consider using Postgres as a database backend instead.

Create a postgres user and database for matrix-reminder-bot:

```
sudo -u postgresql psql createuser matrix-reminder-bot -W  # prompts for a password
sudo -u postgresql psql createdb -O matrix-reminder-bot matrix-reminder-bot
```

Edit the `storage.database` config option, replacing the `sqlite://...` string with `postgres://...`. The syntax is:

```
database: "postgres://username:password@localhost/dbname?sslmode=disable"
```

See also the comments in `sample.config.yaml`.

## Running

### Docker

Refer to the docker [run instructions](docker/README.md#running).

### Native installation

Make sure to source your python environment if you haven't already:

```
source env/bin/activate
```

Then simply run the bot with:

```
matrix-reminder-bot
```

By default, the bot will run with the config file at `./config.yaml`. However, an
alternative relative or absolute filepath can be specified after the command:

```
matrix-reminder-bot other-config.yaml
```

## Usage

Invite the bot to a room and it should accept the invite and join.

### Setting a reminder

Have the bot ping you in the room about something:

```
!remindme <time>, <reminder text>
```

* `<time>` is an amount of time expressed in the following form:
  `5m` for 5 minutes, `3h` for 3 hours, `10d` for 10 days. These
  cannot be combined together.
* `<reminder text>` is the text that the bot will remind you with.

Have the bot ping you and everyone else in the room about something
(assuming the bot has permissions to do so):

```
!remindroom <time>, <reminder text>
```

### Recurring reminders

To create a recurring reminder, put `every` followed by a length of
time, then the time that the reminder should first go off, and then
the reminder text:

```
!remindme every 1w, tuesday, take out the trash
```

```
!remindroom every 5m, 1m, you are loved
```

### Cron-style reminders

If you need more complicated functionality for your reminder's
timing, you can make use of cron tabs. You can read a guide on
cron tabs [here](https://www.adminschoice.com/crontab-quick-reference).

In short they allow you to execute more complicated, recurring
reminders, such as those that should only fire during weekdays.

```
!remindme cron * 9 * * mon-fri, time for the daily stand up
```

The above reminder would fire each weekday at 9:00am.

```
!remindme cron 0/30 9-18 * * mon,wed,fri, take a short break
```

The above reminder would fire every 30 minutes after 9:00am,
until 6:30pm, and only on Monday, Wednesday and Friday.

### List upcoming reminders

```
!listreminders
```

This will output a list of reminders and when they will fire next:

```
sometime Do the dishes (every 1d)
sometime Take out the trash
sometime Send email to Grandma
```

### Cancel a reminder

```
!cancelreminder <reminder text>
```

### Setting an alarm

Alarms are the same as a reminder, but they will repeat every 5 minutes
after firing until they are silenced.

Creating an alarm is the same syntax as creating a reminder, besides a
different command:

```
!alarmme <time>, <reminder text>
```

```
!alarmroom every <recurring time>, <start time>, <reminder text>
```

### Silencing an alarm

An alarm can be silenced with the following command:

```
!silence <reminder text>
```
