import logging
import sys

from setup import constants

class SetupLogFormatter(logging.Formatter):

    def __init__(self):
        self.DEBUG_LOG_FORMAT = "%(levelname)s:%(name)s:%(funcName)s:%(message)s"
        self.INFO_LOG_FORMAT = "%(message)s"
        self.ERROR_LOG_FORMAT = f"\x1b[{constants.TEXT_STYLES['bold']};39;59m%(levelname)s - %(funcName)s:%(message)s{constants.TEXT_END}"
        super().__init__()
    
    def format(self, record):
        if record.levelno == logging.DEBUG:
            self._style._fmt = self.DEBUG_LOG_FORMAT
        elif record.levelno == logging.INFO:
            self._style._fmt = self.INFO_LOG_FORMAT
        else:
            self._style._fmt = self.ERROR_LOG_FORMAT
        return super().format(record)
    
def initialize_logging():
    #Determine the initial logging level
    if constants.IS_DEBUG:
        log_level = logging.DEBUG
    else:
        log_level = logging.WARN
    #Initialize loggers
    root_logger = logging.getLogger("setup")
    root_logger.setLevel(log_level)
    log_handler = logging.StreamHandler(sys.stdout)
    log_formatter = SetupLogFormatter()
    log_handler.setFormatter(log_formatter)
    log_handler.setLevel(log_level)
    root_logger.addHandler(log_handler)
    root_logger.debug("Logging initialized")