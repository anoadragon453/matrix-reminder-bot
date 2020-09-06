#!/usr/bin/env python3
import asyncio
import logging
import sys
from time import sleep

from aiohttp import ClientConnectionError, ServerDisconnectedError
from apscheduler.schedulers import SchedulerAlreadyRunningError
from nio import (
    AsyncClient,
    AsyncClientConfig,
    InviteMemberEvent,
    LocalProtocolError,
    LoginError,
    MegolmEvent,
    RoomMessageText,
)

from matrix_reminder_bot.callbacks import Callbacks
from matrix_reminder_bot.config import CONFIG
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
    CONFIG.read_config(config_filepath)

    # Configure the python job scheduler
    SCHEDULER.configure({"apscheduler.timezone": CONFIG.timezone})

    # Configuration options for the AsyncClient
    client_config = AsyncClientConfig(
        max_limit_exceeded=0,
        max_timeouts=0,
        store_sync_tokens=True,
        encryption_enabled=True,
    )

    # Initialize the matrix client
    client = AsyncClient(
        CONFIG.homeserver_url,
        CONFIG.user_id,
        device_id=CONFIG.device_id,
        store_path=CONFIG.store_path,
        config=client_config,
    )

    # Configure the database
    store = Storage(client)

    # Set up event callbacks
    callbacks = Callbacks(client, store)
    client.add_event_callback(callbacks.message, (RoomMessageText,))
    client.add_event_callback(callbacks.invite, (InviteMemberEvent,))
    client.add_event_callback(callbacks.decryption_failure, (MegolmEvent,))

    # Keep trying to reconnect on failure (with some time in-between)
    while True:
        try:
            # Try to login with the configured username/password
            try:
                login_response = await client.login(
                    password=CONFIG.user_password, device_name=CONFIG.device_name,
                )

                # Check if login failed. Usually incorrect password
                if type(login_response) == LoginError:
                    logger.error("Failed to login: %s", login_response.message)
                    logger.warning("Trying again in 15s...")

                    # Sleep so we don't bombard the server with login requests
                    sleep(15)
                    continue
            except LocalProtocolError as e:
                # There's an edge case here where the user hasn't installed the correct C
                # dependencies. In that case, a LocalProtocolError is raised on login.
                logger.fatal(
                    "Failed to login. Have you installed the correct dependencies? "
                    "https://github.com/poljar/matrix-nio#installation "
                    "Error: %s",
                    e,
                )
                return False

            # Login succeeded!

            logger.info(f"Logged in as {CONFIG.user_id}")
            logger.info("Startup complete")

            # Allow jobs to fire
            try:
                SCHEDULER.start()
            except SchedulerAlreadyRunningError:
                pass

            await client.sync_forever(timeout=30000, full_state=True)

        except (ClientConnectionError, ServerDisconnectedError, TimeoutError):
            logger.warning("Unable to connect to homeserver, retrying in 15s...")

            # Sleep so we don't bombard the server with login requests
            sleep(15)
        except Exception:
            logger.exception("Unknown exception occurred:")
            logger.warning("Restarting in 15s...")

            # Sleep so we don't bombard the server with login requests
            sleep(15)
        finally:
            # Make sure to close the client connection on disconnect
            await client.close()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
