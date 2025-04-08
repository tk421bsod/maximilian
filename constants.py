import sys

#Declarations and wrapper for constants used by the application.
#Some values are determined on startup and only have sane defaults here.
class GlobalConstants:

    #Version string.
    VERSION = "2.0.0-prerelease"

    #Whether text formatting is enabled.
    TEXT_FORMATTING_ENABLED = not (("--no-text-formatting" in sys.argv) or ("-no-fmt" in sys.argv))

    #Whether debug logging is enabled.
    IS_DEBUG = bool([i for i in sys.argv if i in ['-v', '--verbose', '--debug']])

    #The minor version of the Python we're running under.
    #Used for some compatibility checks.
    PYTHON_MINOR_VERSION = sys.version_info.minor

    #The language to load and use.
    #Sane default only, actual value is obtained from either arguments or config
    LANGUAGE = "en"

    #Minimum major/minor version for discord.py.
    #Used for checking compatiblity in startup.check_version
    DPY_MIN_MAJOR_VERSION = 2
    DPY_MIN_MINOR_VERSION = 3

    PYTHON_MIN_MINOR_VERSION = 8
    PYTHON_MAX_APPROVED_MAJOR_VERSION = 11
