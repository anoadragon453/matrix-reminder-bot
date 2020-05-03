class ConfigError(RuntimeError):
    """An error encountered during reading the config file

    Args:
        msg (str): The message displayed to the bot operator on error
    """
    def __init__(self, msg: str):
        super(ConfigError, self).__init__("%s" % (msg,))


class CommandError(RuntimeError):
    """An error encountered while processing a command

    Args:
        msg: The message that is sent back to the user on error
    """
    def __init__(self, msg: str):
        super(CommandError, self).__init__("%s" % (msg,))
        self.msg = msg
