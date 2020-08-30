class ConfigError(RuntimeError):
    """An error encountered during reading the config file

    Args:
        msg (str): The message displayed to the bot operator on error
    """

    def __init__(self, msg: str):
        super().__init__("%s" % (msg,))


class CommandError(RuntimeError):
    """An error encountered while processing a command

    Args:
        msg: The message that is sent back to the user on error
    """

    def __init__(self, msg: str):
        super().__init__("%s" % (msg,))
        self.msg = msg


class CommandSyntaxError(RuntimeError):
    """An error encountered if syntax of a called command was violated"""

    def __init__(self):
        super().__init__()
