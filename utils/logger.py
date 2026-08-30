import logging
from enum import Enum


class LoggerLevel(Enum):
    ONLY_ERRORS = logging.ERROR
    ALL_WARNINGS = logging.WARNING
    VERBOSE = logging.INFO


def create_logger(name: str):
    logger = logging.getLogger(f"JobMailer.{name}")
    logger.propagate = False
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        console_handler = logging.StreamHandler()
        format = "%(asctime)s - %(levelname)s - %(name)s - %(message)s"
        formatter = logging.Formatter(format)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
    return logger


def set_logger_level(level: LoggerLevel = LoggerLevel.VERBOSE):
    """ Adjusts the logger's level. This function allows the logging level to be changed at runtime. """
    for logger_name in logging.root.manager.loggerDict:
        if logger_name.startswith("JobSpy:"):
            logging.getLogger(logger_name).setLevel(level.value)
