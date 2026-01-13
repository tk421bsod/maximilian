import sys

from common import show_not_executable

#Declarations and wrapper for constants used by the application.
#Some values are determined on startup and only have sane defaults here.
class GlobalConstants:

    #Default path for the virtual environment created by setup.py
    DEFAULT_VENV_DIR = ".venv"

    #Version string.
    VERSION = "2.0.0-prerelease"

    #Whether text formatting is enabled.
    TEXT_FORMATTING_ENABLED = not (("--no-text-formatting" in sys.argv) or ("-no-fmt" in sys.argv))

    #Whether debug logging is enabled.
    IS_DEBUG = bool([i for i in sys.argv if i in ['-v', '--verbose', '--debug']])

    #The minor version of the Python install we're running under.
    #Used for some compatibility checks.
    PYTHON_MINOR_VERSION = sys.version_info.minor

    #The language to load and use.
    #Sane default only, actual value is obtained from either arguments or config
    LANGUAGE = "en"

    #The name for the root logger.
    ROOT_LOGGER_NAME = "maximilian"

    #Whether we're in a virtual environment. See https://docs.python.org/3/library/sys.html#sys.exec_prefix
    WITHIN_VENV = (sys.exec_prefix != sys.base_exec_prefix)

    POTENTIALLY_DESTRUCTIVE_ARGS = []
    CHANGED_ARGS = {"--noupdate":"--no-update", "--noload":"--no-load"}

    #Minimum major/minor versions for things
    #Used for checking compatiblity in startup.check_version
    DPY_MIN_MAJOR_VERSION = 2
    DPY_MIN_MINOR_VERSION = 3

    PYTHON_MIN_MINOR_VERSION = 8
    PYTHON_MAX_APPROVED_MINOR_VERSION = 11

    #List of modules that must be loaded for the bot to function
    REQUIRED_MODULES = ["core", "errorhandling"]

if __name__ == "__main__":
    show_not_executable()
