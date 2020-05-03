# To build the image, run `docker build` command from the root of the
# synapse repository:
#
#    docker build -f docker/Dockerfile .
#
# There is an optional PYTHON_VERSION build argument which sets the
# version of python to build against. For example:
#
#    docker build -f docker/Dockerfile --build-arg PYTHON_VERSION=3.8 .
#
# If you are intending to connect to a Postgres database backend,
# you'll need to set the POSTGRES build argument to install the
# necessary dependencies. For example:
#
#    docker build -f docker/Dockerfile --build-arg POSTGRES=1 .
#

ARG PYTHON_VERSION=3.8

FROM anoadragon453/matrix-nio:python-${PYTHON_VERSION}

# (Optional) Install psycopg2 and needed dependencies
# We do all of this in one command in order to add and remove all
# build dependencies in the same docker layer, significantly saving
# space
ARG POSTGRES
RUN if [ -n "$POSTGRES" ]; then \
    apk add --no-cache --virtual .build-deps \
        gcc \
        python3-dev \
        musl-dev && \
            # These are our runtime dependencies. We want to keep them
            # around
            apk add --no-cache libpq postgresql-dev && \
                # Install psycopg2, the python postgres driver
                pip install psycopg2 && \
                    apk del .build-deps \
    ; fi

# Copy source code
COPY *.py *.md matrix-reminder-bot /src/

RUN mkdir /src/matrix_reminder_bot
COPY matrix_reminder_bot/*.py src/matrix_reminder_bot/

# Install python dependencies
# Once again, we pull the same trick of installing then deleting build
# dependencies
WORKDIR /src/
RUN apk add --no-cache --virtual .build-deps \
    gcc \
    python3-dev \
    musl-dev && \
        # Install needed python modules
        pip install -e . && \
            apk del .build-deps

# Holds config file, SQLite3 database, and matrix-nio store
VOLUME ["/data"]

ENTRYPOINT ["matrix-reminder-bot", "/data/config.yaml"]
