#!/usr/bin/env python3

import asyncio
import logging
import sys
from time import sleep

from aiohttp import ClientConnectionError, ServerDisconnectedError
from nio import (AsyncClient, AsyncClientConfig, InviteMemberEvent,
                 LocalProtocolError, LoginError, RoomMessageText)

from matrix_reminder_bot.callbacks import Callbacks
from matrix_reminder_bot.config import Config
from matrix_reminder_bot.reminder import SCHEDULER
from matrix_reminder_bot.storage import Storage

logger = logging.getLogger(__name__)


async def main():
    # Read config file

    # A different config file path can be specified as the first command line arg
    if len(sys.argv) > 1:
        config_filepath = sys.argv[1]
    else:
        config_filepath = "config.yaml"
    config = Config(config_filepath)

    # Configure the database
    store = Storage(config)

    # Configure the python job scheduler
    SCHEDULER.configure({"apscheduler.timezone": config.timezone})

    # Configuration options for the AsyncClient
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=True,
    )

    # Initialize the matrix client
    client = AsyncClient(
        config.homeserver_url,
        config.user_id,
        device_id=config.device_id,
        store_path=config.store_path,
        config=client_config,
    )

    # Initialize reminders
    store.load_reminders(client)

    # Set up event callbacks
    callbacks = Callbacks(client, store, config)
    client.add_event_callback(callbacks.message, (RoomMessageText,))
    client.add_event_callback(callbacks.invite, (InviteMemberEvent,))

    # Keep trying to reconnect on failure (with some time in-between)
    while True:
        try:
            # Try to login with the configured username/password
            try:
                login_response = await client.login(
                    password=config.user_password,
                    device_name=config.device_name,
                )

                # Check if login failed. Usually incorrect password
                if type(login_response) == LoginError:
                    logger.error(f"Failed to login: %s", login_response.message)
                    return False
            except LocalProtocolError as e:
                # There's an edge case here where the user hasn't installed the correct C
                # dependencies. In that case, a LocalProtocolError is raised on login.
                logger.fatal(
                    "Failed to login. Have you installed the correct dependencies? "
                    "https://github.com/poljar/matrix-nio#installation "
                    "Error: %s", e
                )
                return False

            # Login succeeded!

            # Sync encryption keys with the server
            # Required for participating in encrypted rooms
            if client.should_upload_keys:
                await client.keys_upload()

            logger.info(f"Logged in as {config.user_id}")
            logger.info(f"Startup complete")

            # Allow jobs to fire
            SCHEDULER.start()

            await client.sync_forever(timeout=30000, full_state=True)

        except (ClientConnectionError, ServerDisconnectedError):
            logger.warning("Unable to connect to homeserver, retrying in 15s...")

            # Sleep so we don't bombard the server with login requests
            sleep(15)
        finally:
            # Make sure to close the client connection on disconnect
            await client.close()

if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
