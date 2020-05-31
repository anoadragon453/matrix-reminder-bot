# Docker

The docker image will run matrix-reminder-bot with a SQLite database and
end-to-end encryption dependencies included. For larger deployments, a
connection to a Postgres database backend is recommended.

## Setup

### The `/data` volume

The docker container expects the `config.yaml` file to exist at
`/data/config.yaml`. To easily configure this, it is recommended to create a
directory on your filesystem, and mount it as `/data` inside the container:

```
mkdir data
# We'll then mount this when running the container using `docker run`'s `-v` flag
```

### Creating a config file

Copy `sample.config.yaml` to a file named `config.yaml` inside of your newly
created `data` directory. Fill it out as you normally would, with a few minor
differences:

* The bot store directory should reside inside of the data directory so that it
  is not wiped on container restart. Change it from the default to `/data/store`.
  There is no need to create this directory yourself, matrix-reminder-bot will
  create it on startup if it does not exist.

* Choose whether you want to use SQLite or Postgres as your database backend. If
  using SQLite, ensure your database file is stored inside the `/data` directory:

  ```
  database: "sqlite:///data/bot.db"
  ```

  If using postgres, point to your postgres instance instead:

  ```
  database: "postgres://username:password@postgres/matrix-reminder-bot?sslmode=disable
  ```

Change any other config values as necessary. For instance, you may also want to
store log files in the `/data` directory.

## Running

Once you have a valid configuration file and data directory, you can start
matrix-reminder-bot with:

```
docker run -d --name matrix-reminder-bot \
    -v /path/to/data-directory:/data \
    anoa/matrix-reminder-bot:latest
```

You can then check that it started correctly with:

```
docker logs matrix-reminder-bot
```

## Building the Image

To build the image from source, use the following `docker build` command from
the repo's root:

```
docker build -t anoa/matrix-reminder-bot:latest -f docker/Dockerfile .
```
