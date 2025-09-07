"""A Python implementation of setup.sh.
Will replace setup.sh for easier maintenance and platform independence in the future.
"""

if __name__ == "__main__":
    print("Setup is starting.\n")

import copy
import functools
import getpass
import importlib
import logging
import os
import sys
from time import sleep
import traceback
import typing

import common
import constants
import updater  

#Deep copy from builtins to ensure we have a copy of the original print()
#This is to prevent infinite original_print calls if calling importlib.reload(setup) when testing
if __name__ == "__main__":
    original_print = copy.deepcopy(__builtins__.print)
else:
    #builtins is a dict for some reason when running in interactive mode
    original_print = copy.deepcopy(__builtins__["print"])

#Special control characters for text formatting
TEXT_END = "\x1b[0m"
TEXT_STYLES = {"none":0, "bold":1, "underline":2, "negative1":3, "negative2":5, "black":30, "red":31, "green":32, "yellow":33, "blue":34, "purple":35, "cyan":36, "white":37}

OS_TYPE = os.name
FORMATTING_ENABLED = True
IS_DEBUG = "-v" in sys.argv
skip_pre_setup = False

class SetupLogFormatter(logging.Formatter):

    def __init__(self):
        self.DEBUG_LOG_FORMAT = "%(levelname)s:%(name)s:%(funcName)s:%(message)s"
        self.INFO_LOG_FORMAT = "%(message)s"
        #            Begin styling, make text white on black + bold, {levelName} - {funcName}:{message}, clear styling.
        self.ERROR_LOG_FORMAT = f"\x1b[{TEXT_STYLES['bold']};39;59m%(levelname)s - %(funcName)s:%(message)s{TEXT_END}"
        super().__init__()
    
    def format(self, record):
        if record.levelno == logging.DEBUG:
            self._style._fmt = self.DEBUG_LOG_FORMAT
        elif record.levelno == logging.INFO:
            self._style._fmt = self.INFO_LOG_FORMAT
        else:
            self._style._fmt = self.ERROR_LOG_FORMAT
        return super().format(record)

class SetupState:

    def __init__(self):
        root_logger.debug("Initializing global state")
        self.pw = ""
        self.ip = "%"        
        self.current_menu = SetupConstants.MAIN_MENU
        self.menu_stack = [SetupConstants.MAIN_MENU]
        self.LOCK_FILE_HANDLER = None
        self.install_in_progress = None
        self.db_available = False
        self.remote = None
        self.ip = "localhost"
        self.config_found = True
        temp_config_exists = os.path.exists("config.tmp")
        lock_file_exists = os.path.exists("setup.lock")
        setup_state_exists = os.path.exists("setup_state.tmp")
        root_logger.debug(f"Temp config: {temp_config_exists} | Lock file: {lock_file_exists} | Saved state: {setup_state_exists}")
        if setup_state_exists:
            self.config = common.load_config("setup_state.tmp")
            root_logger.debug(self.config)
            root_logger.debug(f"Saved state detected. Restart reason: {self.config['restart_reason']}")
            os.unlink("setup_state.tmp")
            return
        try:
            if lock_file_exists:
                print("Setup exited unexpectedly.", style=TEXT_STYLES["bold"])
                if temp_config_exists and not setup_state_exists:
                    print("Your configuration data from that session was lost.", style=TEXT_STYLES["bold"])
                    print("You must finish the setup process to save your configuration data.")
                    os.unlink("config.tmp")
                else:
                    print("No configuration data was lost.")
            elif temp_config_exists and not setup_state_exists:
                print("You exited Setup before a task was finished.\nYour configuration data from that session was lost.", style=TEXT_STYLES["bold"])
                print("You must finish the setup process to save your configuration data.")
                os.unlink("config.tmp")
            if __name__ == "__main__":
                root_logger.debug("Loading config.")
                self.config = common.load_config()
                root_logger.debug("Creating lock file.")
                self.LOCK_FILE_HANDLER = open("setup.lock", "w")
            else:
                self.config = {}
        except FileNotFoundError:
            root_logger.debug("Config not found.")
            self.config = {}
            self.config_found = False
        except:
            root_logger.debug("Could not load/parse config. See exc info below")
            root_logger.debug(traceback.format_exc())
            print("The configuration file couldn't be loaded. Run setup.py with -v to show more information.")
            print("This file will be overwritten if you use any options from the 'Install' menu.")
            self.config = {}
            self.config_found = False

    def save_state(self, reason="None"):
        """Save the current config to setup_state.tmp"""
        root_logger.debug(f"Temporarily saving current config with reason '{reason}'.")
        self.config["restart_reason"] = reason
        SetupUtils.write_config("setup_state.tmp")
        root_logger.debug("Temporary config saved")

    def load_state(self):
        """Load saved temporary config from setup_state.tmp"""
        if not os.path.isfile("setup_state.tmp"):
            root_logger.debug("No saved temporary config found")
            return None
        config = common.load_config('setup_state.tmp')
        self.config.update(config)

class MarkdownUtils():
    @staticmethod
    def _find_separator_pairs(source : str, separator : str):
        """Find all pairs of `separator` in the string `source`.
        Returns their indexes as a list of tuples.
        """
        pairs = []
        cur = 0
        #Find the first occurrence.
        ret = source.find(separator)
        cur = ret
        while cur < len(source):
            #If we've run out of occurrences, return the list of pairs.
            if cur == -1:
                return pairs
            #Otherwise just append the current index to the current pair.
            pair.append(cur)
            #Find the next occurrence.
            ret = source.find(separator, cur + 1)
            cur = ret
            #Add the pair to the list of pairs if it's full.
            if len(pair) == 2:
                pairs.append(pair)
                pair = []
        return pairs

    @staticmethod
    def apply_markdown(text : str):
        """Apply markdown in strings to be printed. Just makes it a little easier to write things that require formatting, ya know?
        Like instead of adding style=TEXT_STYLES['bold'] to EVERY SINGLE print() call I can just put asterisks around the text I want formatted :)
    """
        while True:
            final = ""
            #Check for separators in our text. Replace separators with their style, then print the resulting string.
            for separator, style in [("**", f"\x1b[{TEXT_STYLES['bold']};39;59m"), ("~~", f"\x1b[{TEXT_STYLES['underline']};39;59m"), ("[red]", f"\x1b[0;{TEXT_STYLES['red']};59m"), ("[green]", f"\x1b[0;{TEXT_STYLES['green']};59m")]:
                pairs = MarkdownUtils._find_separator_pairs(text, separator)
                processed = ""
                for pair in pairs:
                    #Replace the first part of the pair with a separator.
                    processed += style + text[pair[0]+len(separator):pair[1]]
                    #End the styled portion.
                    processed += TEXT_END
                    final += processed
            return final

#Yes, we're modifying builtins.
#Sorry
def print(text, *, ignore_markdown=True, end=TEXT_END+"\n", fg=39, style=0, bg=49):
    if not FORMATTING_ENABLED:
        original_print(text, end=end)
        return
    if not ignore_markdown:
        ret = MarkdownUtils.apply_markdown()
        if ret: #some markdown was applied?
            return #don't care about styling.
    bg = bg + 10
    text = f"\x1b[{style};{fg};{bg}m{text}"
    original_print(text, end=end)

def potentially_destructive(func):
    def potentially_destructive_inner(*args, **kwargs):
        """Warn about a potentially destructive operation"""
        print(f"\nAre you sure that you want to do this?", style=TEXT_STYLES["bold"])
        print("If you don't know what you are doing, this option may cause a loss of data or break your installation.")
        potentially_destructive_menu = SetupUtils.BooleanMenu(prompt="")
        ret = potentially_destructive_menu.handle_menu()
        if ret["choice"]:
            func(*args, **kwargs)
    return potentially_destructive_inner

class CleanExit(BaseException):
    """Raised to break out of higher level loops."""
    pass

class GitCommandFailed(BaseException):
    """Raised to indicate a Git command failed within a task. Includes the output of the run_command call that failed."""

    def __init__(self, context):
        self.context = context

class TaskFailure(BaseException):
    """Raised to indicate that a task failed. Includes a slot for the return value of the task."""
    
    __slots__ = ("ret")
    
    def __init__(self, ret=None):
        self.ret = ret

class TaskExitStatus:
    SUCCESS = 0
    FAILURE = 1
    EXCEPTION = 2

class TaskResults:
    """Returned from SetupTaskHandler."""
    
    def __init__(self, status, ret, context=None):
        self.status : TaskExitStatus = status
        self.ret = ret
        self.context : typing.Optional[Exception] = context

def empty_callback():
    return None

class SetupStrings:
    """Various string constants used by Setup."""

    INTRO_HEADER = "---- Maximilian Setup ----"
    INTRO_DESC = "This script helps automate Maximilian's initial setup process. \nIt can also assist with a few common maintenance tasks."
    MAIN_MENU_PROMPT = "Choose an option from the list below, or 'Help' for explanations:"
    MORE_PROMPT = "These options aren't used very often but may be able to help.\nChoose one from the list below, 'Help' for assistance, or 'Main Menu' to go back:"
    INSTALL_MENU_PROMPT = "Choose an installation type, 'Help' for assistance, or 'Main Menu' to go back:"
    DATABASE_MENU_PROMPT = "Choose a database action to perform, 'Help' for assistance, or 'Main Menu' to go back:"
    REPAIR_MENU_PROMPT = "Choose an option, 'Help' for assistance, or 'Main Menu' to go back:"

    MAIN_MENU_HELP = """\n---- Setup Help ----
Want to install Maximilian? Choose **Install**.
For database maintenance, choose **Database options**.
Migrating to 2.0? Choose **Migrate to 2.0.**
Want to check for updates now? Choose **Run updater**.
Something else? Choose **More**.
"""
    MORE_HELP = """\n---- More Help ----
Want to free up some space? Choose **Clear caches**. Some things may take longer to load afterwards.
Have an issue? Try **Repair**.
Want to return to the main menu? Choose **Main Menu**.
"""
    DATABASE_MENU_HELP = """\n---- Database Options Help ----
Having an issue and need to reinstall the database? Choose **Reinstall database**. This will not clear your data.
Need to start the database? Choose **Start database**.
Want to back up your data? Choose **Back up database**.
Restoring from a backup? Choose **Restore database**.
Want to uninstall? Choose **Uninstall options** from the main menu.
"""
    INSTALL_MENU_HELP = """\n---- Install Help ----
**Full install** will install Maximilian and its database.
**Install without database** will only install Maximilian.
**Install database only** will only set up the database.
Want to uninstall? Choose **Uninstall options** from the main menu.
"""
    UNINSTALL_MENU_HELP = """\n---- Uninstall Help ----
**    
"""

    POSIX_HELP_STRINGS = {
        "DATABASE_NOT_STARTED":"Did you enter the correct password when prompted?"


    }
    NT_HELP_STRINGS = {
        "DATABASE_NOT_STARTED":"\n*You might not have permission to start the database.\nTry running 'net start mysql' or 'net start MariaDB' from an Administrator Command Prompt.\\n\n*FOR MARIADB INSTALLS: You might not have installed MariaDB as a service.\nRun the installer again and ensure that 'Install as service' is checked. The service name must be either 'mysql' or 'MariaDB'."
                       
    
    }
    GIT_COMMAND_FAILED_WITHIN_TASK = "A Git command failed. This task cannot continue."
    GIT_COMMAND_FAILED_FATAL = "A Git command failed. Setup cannot continue."
    GIT_COMMAND_FAILED_MORE = "Read the above output carefully, then check HOSTING.md for more information."

class SetupUtils:
    """Various utilities used by Setup."""

    @staticmethod
    def convert_config():
        "Convert configuration data from a dict to a string to write."
        config = ""
        root_logger.debug("Converting config to string")
        for k, v in SetupGlobalState.config.items():
            config += f"{k}:{v}\n"
        root_logger.debug(f"Resulting config string: {config}")
        return config

    @staticmethod
    def write_config(path):
        "Write configuration data from convert_config to a file at 'path'. Overwrites config file contents."
        config = SetupUtils.convert_config()
        root_logger.debug(f"Writing config to file {path}")
        with open(path, "w") as configfile:
            configfile.write(config)

    @staticmethod
    def load_database_api():
        """Attempt to import the database API. If the import fails, returns False. Upon success, returns True."""
        try:
            SetupDatabaseClient.db = importlib.import_module("db_utils.db")
        except:
            traceback.print_exc()
            return False
        return True
    
    @staticmethod
    def get_venv_working_directory():
        venv_dir = common.get_value(SetupGlobalState.config, "venv_dir")
        return venv_dir if os.path.exists(venv_dir) else constants.GlobalConstants.DEFAULT_VENV_DIR

    @staticmethod
    def run_os_dependent_command(linux_command, windows_command):
        root_logger.debug(f"Running OS dependent command, linux: {linux_command} windows: {windows_command}")
        if OS_TYPE == "nt":
            return common.run_command(windows_command)
        elif OS_TYPE == "posix":
            return common.run_command(linux_command)
        
    @staticmethod
    def run_git_command(cmd):
        """Run a Git command and raise GitCommandFailed if it fails."""
        root_logger.debug("Running Git command")
        ret = common.run_command(cmd)
        if ret["returncode"]:
            raise GitCommandFailed(ret)
        return ret

    @staticmethod
    def check_for_git():
        """Check for an active Git repository in the current working directory. Use before tasks that perform Git operations."""
        ret = SetupUtils.run_git_command("git status")

    class MenuWithCallbacks:
        """
        Base class for a menu that maps callbacks to options.
        Menus subclassing this must initialize this, then call handle_callback for callbacks to run.
        """

        def _has_callback(self, option):
            """Check if a menu option has a callback attached to it."""
            if type(option) != dict:
                return False
            return True

        def _handle_callback(self, option):
            """Handle a callback mapped to a menu option.

            Returns the return value of the callback if available, otherwise returns None.
            """
            #Return None if there isn't an attached callback.
            if not self._has_callback(option):
                return None
            #Get the attached callback.
            callback = list(option.values())[0]
            if not callable(callback):
                print("Menu callbacks must be callable! Returning None.", fg=TEXT_STYLES["red"])
                return None
            #Run the callback and return its return value.
            ret = callback()
            return ret

    class IntMenu(MenuWithCallbacks):
        """
        A menu for choosing from a list of options.
        Provide a list of options and a prompt for input at initialization then call handle_menu.
        handle_menu will return a dict with the format {"choice":<index of chosen option>, "return":<callback return, None if no callback>}
        Can be reused if you desire.

        Options must be provided as a list. They can also be a list of dicts if you wish to execute a callback when a menu option is chosen.
        Callbacks need to be callable.
        You can also mix the two types within the list if some options don't need callbacks.
        For example, ["Option 1", {"Option 2":some_callback}]
        """

        __slots__ = ("options", "prompt", "allow_all")

        def __init__(self, options, prompt, allow_all=False):
            """Initialize an IntMenu.
            You must call handle_menu for the menu to be shown.
            `allow_all` controls whether to allow an `all` option separate from the normal options.
            When this is enabled, a response of `all` returns `-1` from `handle_menu`.

            See class documentation for the required format for `options`.
            """
            self.options = options
            self.prompt = prompt
            self.allow_all = allow_all
            super().__init__()

        def _handle_input(self):
            ret = input().strip().lower()
            print("")
            if self.allow_all and ret == "all":
                return -1
            try:
                ret = int(ret)
                if ret < 1 or ret > len(self.options):
                    print(f"Enter a number between 1 and {len(self.options)}.\n ")
                    return -2
                return ret-1
            except ValueError:
                print("Enter a number.\n")
            return -2
        
        def handle_menu(self):
            if self.prompt:
                self.prompt = "\n" + self.prompt
            print(self.prompt)
            print("---------------")
            for index, option in enumerate(self.options):
                if self._has_callback(option):
                    print(f"{index+1}) {list(option.keys())[0]}")
                else:
                    print(f"{index+1}) {option}")
            print("---------------")
            if len(self.options) == 1:
                print("Automatically selecting the only option available.")
                ret = self._handle_callback(self.options[0])
                return {"choice":0, "return":ret}
            while True:
                index = self._handle_input()
                if index != -2:
                    ret = self._handle_callback(self.options[index])
                    return {"choice":index, "return":ret}
                
    class BooleanMenu(IntMenu):
        """A menu for choosing between 'Yes' and 'No'."""

        #We need NO_CALLBACK to default to an empty callback to allow for only specifying YES_CALLBACK.
        def __init__(self, prompt, YES_CALLBACK=empty_callback, NO_CALLBACK=empty_callback):
            options = [{"Yes":YES_CALLBACK}, {"No":NO_CALLBACK}]
            super().__init__(options, prompt, False)

        def handle_menu(self):
            """Displays and handles input for the BooleanMenu. Returns the answer provided."""
            ret = super().handle_menu()
            #handle_menu returns the index of the chosen item.
            #Yes returns 0, No returns 1.
            #Converting to a boolean, then getting its inverse, converts the answer to its boolean counterpart.
            ret["choice"] = not ret["choice"]
            return ret
        
class InstallUtils:
    
    @staticmethod
    def get_token():
        print("Enter a token. This allows Maximilian to log in to Discord.")
        print("Your input will be hidden to keep it secret.")
        print("(Unsure? Enter ? for help.)")
        while True:
            token = getpass.getpass("").strip()
            if token == "?":
                print("\nA token allows a bot to log in under a special account.")
                print("Need one? Open the Discord Developer Portal, create an application, go to the Bot tab, create a bot account, and copy the token.")
                print("Then paste it here.")
                print("When you're ready, enter your token below.")
                continue
            elif token == "":
                print("\nYou must enter a token to continue.")
                continue
            print("\nToken set.")
            break
        return token

    @staticmethod
    def get_database_password():
        print("\nNext, enter a database password. This will be what Maximilian uses to access the database.")
        if SetupGlobalState.remote:
            print("Since the database is set up on a different computer, enter the password for that database.")
        print("Your input will be hidden to keep it secret.")
        while True:
            dbp = getpass.getpass("").strip()
            if dbp == "":
                print("\nYou must enter a password to continue.")
                continue
            print("\nGreat. Enter the same password again to confirm it.")
            dbp_confirmation = getpass.getpass("").strip()
            if dbp_confirmation != dbp:
                print("\nThe two passwords didn't match. You'll need to enter the password again.")
                continue
            print("Database password set.")
            break
        return dbp

    @staticmethod
    def get_owner_id():
        print("Enter the ID for your Discord account. This enables error reporting and gives you more control over Maximilian.")
        print("You *can* leave this blank, but your experience will be better if you include it.")
        print("(Unsure of how to get your ID or just want some more info? Enter ?.)")
        while True:
            owner_id = input().strip()
            if owner_id == "?":
                print("\nA user ID is a unique number that identifies a specific Discord account.")
                print("Maximilian uses this ID to determine where to send error messages.")
                print("This ID is also used to enable some more advanced commands.")
                print("These commands allow you to perform maintenance and debugging without access to the command line.")
                print("This also allows you to use the Jishaku module. See HOSTING.md for more details on that.")
                print("You can get your ID by right-clicking on yourself in the member list, then clicking 'Copy User ID' in the context menu.")
                print("If you don't see this option, enable 'Developer Mode' in Settings -> Advanced, and try again.")
                print("When you're ready, enter your ID below.")
                continue
            elif owner_id == "":
                print("\nOwner ID not set.\nError reporting, 'utils' commands, and Jishaku have been disabled.") 
                print("")
                break
            if not owner_id.isnumeric():
                print("The ID must be a number.")
                continue
            print("\nOwner ID set.")
            break
        return owner_id

class InstallHandler:

    """Container for methods used by the installation process.
    
    Set single_use upon initialization if only using the instance once.
    This prevents methods from outputting contextual information used during a full install.
    """

    def __init__(self, single_use=False):
        self.overwrite_config = False
        self.overwrite_config_menu = SetupUtils.BooleanMenu("It looks like you already have configuration data saved.\nDo you want to overwrite it?")
        self.dbp = None
        self.owner_id = None
        self.token = None
        self.automatic_updates_enabled = None
        self.single_use = single_use
        SetupGlobalState.install_in_progress = self
        if SetupGlobalState.remote is None:
            SetupGlobalState.remote = SetupUtils.BooleanMenu("Is the database already set up on a different computer?").handle_menu()["choice"]

    def set_config_value(self, k, v):
        if self.overwrite_config:
            SetupGlobalState.config[k] = v
        else:
            root_logger.debug(f"Not overwriting config key '{k}' with '{v}'")

    def prepare(self):
        """Prepare for the install."""
        if SetupGlobalState.config_found:
            self.overwrite_config = self.overwrite_config_menu.handle_menu()["choice"]
        else:
            self.overwrite_config = True
        if OS_TYPE == "nt":
            print("Since you're on Windows, you'll need to install some software on your own.", style=TEXT_STYLES["bold"])
            print("Please install:\n*Python 3.9 or above, ensure it's on your PATH and that 'Install pip' is checked during installation\n*MySQL / MariaDB server\n*FFmpeg (must be on PATH, only for music features)")
            if not SetupGlobalState.remote:
                print("Also, please complete the initial setup process for your database software, and start the database server.")
            print("Once you're finished, press Enter to continue with setup.")
            input()
        
    def prep_initial_config(self):
        #A pound sign in a key is interpreted as a comment when loading configuration data.
        #This is a little janky but it should work?
        self.set_config_value("# Configuration data for Maximilian.\n# This file was automatically generated. Editing may break stuff unless you know what you're doing.\n# This file contains sensitive information that could compromise your account. Do not share it with anyone. ", "")
        self.set_config_value("theme_color", "0x3498db")
        #Create a file to indicate that configuration data needs to be saved.
        open("config.tmp", "x")
        print("")
        print("Initial configuration data created.", style=TEXT_STYLES["bold"])
        print("This will be saved after the setup process finishes.")

    def gather_information(self):
        """Gather information used later on."""
        if not self.overwrite_config:
            print("\nYou chose to not overwrite configuration data.")
            print("Skipping the information gathering step.")
            return
        self.prep_initial_config()
        print("")
        print("There's a few things Setup needs from you.\n", style=TEXT_STYLES["bold"])
        self.token = InstallUtils.get_token()
        self.set_config_value("token", self.token)
        self.dbp = InstallUtils.get_database_password()
        self.set_config_value("dbp", self.dbp)
        self.owner_id = InstallUtils.get_owner_id()
        self.set_config_value("owner_id", self.owner_id)

        print("Would you like to enable automatic updates?")
        self.automatic_updates_enabled = SetupUtils.BooleanMenu("Would you like to enable automatic updates?\nIf enabled, Maximilian will attempt to update itself on startup once every 14 days.").handle_menu()["choice"]
        if self.automatic_updates_enabled:
            self.set_config_value("automatic_updates", "1")
            print("Automatic updates enabled.")
        else:
            self.set_config_value("automatic_updates", "0")
            print("Automatic updates disabled.")

    def install_packages(self):
        if OS_TYPE == "posix":
            print("Updating package index...")
            print("You may be prompted to enter your password.")
            ret = common.run_command("sudo apt-get update")
            if ret["returncode"] == 127:
                print("Your Linux distribution doesn't use the 'apt' package manager.")
                print("You'll need to install the required packages manually to get started.")
                print(f"Install {','.join(SetupConstants.REQUIRED_PACKAGES[:-1])}, and {SetupConstants.REQUIRED_PACKAGES[-1]}.") 
                if not self.single_use:
                    print("Then press Enter to continue.")
                    input()
                    print("Great. Continuing with the installation.")
                return
            print("Installing required packages...")
            ret = common.run_command(f"sudo apt-get install -y {' '.join(SetupConstants.REQUIRED_PACKAGES)}")
            if ret["returncode"]:
                print("Package installation failed! Read the above output for more information.")
                raise TaskFailure()
            return
        print("This is a Windows environment, not installing packages.")

    def _test_for_venv(self, venv_working_directory):
        """Test if a venv is present at the provided working directory (root dir of venv).
        Checks for the existence of {venv_working_directory}/bin/activate or {venv_working_directory}/Scripts/activate.bat"""
        root_logger.debug(f"Checking for venv at {venv_working_directory}")
        #Presence of $DIR/bin/activate indicates a venv is installed here
        if os.path.isfile(f"{venv_working_directory}/bin/activate") or os.path.isfile(f"{venv_working_directory}\\Scripts\\activate.bat"):
            root_logger.debug(f"venv found")
            return True
        root_logger.debug("venv not found")
        return False

    def change_venv_dir(self):
        """Change virtual environment directory."""
        root_logger.debug("Changing venv directory")
        DEFAULT_VENV_DIR = constants.GlobalConstants.DEFAULT_VENV_DIR
        while True:
            print("Where do you want the virtual environment to be created?")
            print("Enter a path relative to Maximilian's root directory.")
            print(f"Press Enter to use the default path ({DEFAULT_VENV_DIR}).")
            creation_dir = input().strip()
            if not creation_dir:
                creation_dir = DEFAULT_VENV_DIR
            root_logger.debug(f"venv dir set to {creation_dir}")
            if os.path.exists(creation_dir):
                print("This location already exists and may have data stored in it.")
                print("Do you want to overwrite it?")
                print("You will lose that data if you continue!")
                root_logger.debug("Path already exists!")
                overwrite = SetupUtils.BooleanMenu("").handle_menu()['choice']
                if overwrite:
                    root_logger.debug("Overwriting venv path contents")
                    print("Alright, overwriting that location.")
                    os.unlink(creation_dir)
                    return creation_dir
                else:
                    print("Not overwriting that location.")
                    print("You'll need to choose a path again.\n--------")
                    continue
            return creation_dir

    def _force_venv_dir_change(self, target_dir):
        #Change the venv_dir field regardless of the config overwrite preference
        #Save chosen value for restoring later
        self.overwrite_config_copy = copy.deepcopy(self.overwrite_config)
        self.overwrite_config = True
        root_logger.debug(f"Changing config venv_dir from '{common.get_value(SetupGlobalState.config, 'venv_dir')}' to '{target_dir}'")
        self.set_config_value("venv_dir", target_dir)
        #Restore chosen config overwrite preference
        self.overwrite_config = self.overwrite_config_copy

    def _check_venv_exists(self):
        """Check if a virtual environment already exists at either the path specified in 'config' or the default path. Returns the path of the existing venv, None if none exists."""
        DEFAULT_VENV_DIR = constants.GlobalConstants.DEFAULT_VENV_DIR
        current_venv_dir = common.get_value(SetupGlobalState.config, 'venv_dir')
        #Do we have something in either config or our default directory?
        if os.path.exists(DEFAULT_VENV_DIR) or current_venv_dir:
            #Does config contain a valid path?
            if not os.path.exists(current_venv_dir):
                print("The virtual environment location specified in config does not exist.")
                print(f"Currently, it's set to '{current_venv_dir}'.")
                print("Would you like to change this? You'll be prompted to create a virtual environment if you decide not to change it. \nYou'll be brought back to this prompt if you enter a location that doesn't contain a virtual environment.")
                choice = SetupUtils.BooleanMenu("").handle_menu()["choice"]
                if choice:
                    new_dir = self.change_venv_dir()
                    self._force_venv_dir_change(new_dir)
                    return self._check_venv_exists()
                else:
                    print("Ok. You now can choose whether to use a virtual environment.")
                    return None
            #venv dir field in config will override default if it exists
            venv_working_directory = SetupUtils.get_venv_working_directory()
            if self._test_for_venv(venv_working_directory):
                return venv_working_directory
        return None

    def _acquire_target_venv_dir(self):
        """Get the directory the virtual environment should be installed to and ensure we can install to it. Returns None if a virtual environment should not be installed."""
        ret = self._check_venv_exists()
        if ret:
            print(f"You already have a virtual environment set up at '{ret}'.", style=TEXT_STYLES["bold"])
            print("Would you like to recreate it? This may take some time.")
            venv_recreate_choice = SetupUtils.BooleanMenu("").handle_menu()["choice"]
            if not venv_recreate_choice:
                print("Alright, not recreating the virtual environment.")
                return None
            print(f"Recreating the virtual environment at '{ret}'. Please be patient, this may take some time.", style=TEXT_STYLES["bold"])
            return ret
        else:
            print("From Maximilian version 2.0 onwards, Python dependencies for Maximilian are recommended to be installed in a 'virtual environment'.")
            print("This separates dependencies from your global Python packages and is required on many Linux systems.")
            print("The only downside is that the environment must be activated every time you open a new command prompt.")
            print("With this in mind, would you like to create a virtual environment for Maximilian? ('Yes' recommended)")
            venv_choice = SetupUtils.BooleanMenu("").handle_menu()["choice"]
            if not venv_choice:
                print("Alright, not installing to a virtual environment.")
                print("Choose 'Create virtual environment' in the Install menu if you want to do this later.")
                return None
            print("Alright, installing to a virtual environment.")
            current_venv_dir = common.get_value(SetupGlobalState.config, 'venv_dir')
            if current_venv_dir:
                print("A virtual environment location is already specified in config.")
                print(f"The location is '{current_venv_dir}'.")
                print("Creating the virtual environment at that location.")
                return current_venv_dir
            creation_dir = self.change_venv_dir()
            print(f"Creating the virtual environment at '{creation_dir}'. Please be patient, this may take some time.", style=TEXT_STYLES["bold"])
            return creation_dir

    def create_venv(self):
        """Prompt for venv creation, create if requested. Returns whether the venv was created and sets config['venv_dir'] if so. """
        import venv
        #Get the directory to install to.
        target_dir = self._acquire_target_venv_dir()
        #Did we choose not to install?
        if not target_dir:
            root_logger.debug("Not installing to a virtual environment.")
            return False
        root_logger.debug(f"Creating venv in directory '{target_dir}'")
        venv.create(target_dir, with_pip=True)
        self._force_venv_dir_change(target_dir)
        return True
    
    def actually_install_python_dependencies(self):
        pass

    def install_python_dependencies_venv_phase_2(self):
        self.actually_install_python_dependencies()
        pass

    def install_python_dependencies_venv_phase_1(self, continue_install_with=None):
        """Activate the virtual environment if not already activated, then quit Setup. Once Setup is restarted, run the SetupTaskHandler classmethod named {continue_install_with} to continue the installation"""
        root_logger.debug("Installing Python dependencies")
        venv_working_directory = SetupUtils.get_venv_working_directory()
        root_logger.debug(f"venv working dir is {venv_working_directory}")
        if self._test_for_venv(venv_working_directory):
            if not constants.GlobalConstants.WITHIN_VENV:
                root_logger.debug("Activating venv")
                SetupTaskHandler.RUN_ACTIVATE_VENV_TASK()
                print("You'll need to restart setup.py to continue.")
                print("The installation process will automatically resume from this point.")
                if continue_install_with:
                    continue_install_with = "," + continue_install_with
                SetupGlobalState.save_state(reason=f"activated_venv{continue_install_with}")
                quit()
            else:
                root_logger.debug("venv already activated")
                continue_install_with = getattr(SetupTaskHandler, continue_install_with, None)
                if not continue_install_with:
                    root_logger.debug("Not sure how to continue, we'll just jump to phase 2")
                    self.install_python_dependencies_venv_phase_2()
                return continue_install_with()

    def initial_database_setup():
        pass

class SetupTasks:
    """Container for various tasks performed by Setup."""

    @staticmethod
    def full_install():
        root_logger.debug("Starting full install task.")
        root_logger.debug("Initializing InstallHandler")
        installer = InstallHandler()
        root_logger.debug("Preparing for install")
        installer.prepare()
        root_logger.debug("Gathering installation info")
        installer.gather_information()
        root_logger.debug("Installing required packages")
        installer.install_packages()
    
    @staticmethod
    def full_install_phase_2():
        root_logger.debug("Starting second phase of full install")

    @staticmethod
    def install_no_database():
        pass

    @staticmethod
    def install_database():
        pass

    @staticmethod
    def update():
        import updater
        #Force update check
        sys.argv.append("--force-update")
        updater.update()
        sys.argv.remove("--force-update")

    @staticmethod
    def backup():
        pass

    @staticmethod
    def setup_database():
        pass

    @staticmethod
    def change_database_password():
        pass

    @staticmethod
    def clear_caches():
        pass

    @staticmethod
    def restore():
        pass

    @staticmethod
    @potentially_destructive
    def launch_database_client():
        return SetupDatabaseClient.main()

    @staticmethod
    def update_submodules():
        SetupUtils.check_for_git()
        ret = common.run_command("git submodule update")
        if ret["returncode"]:
            raise GitCommandFailed(ret)

    @staticmethod
    def start_database():
        DATABASE_START_COMMANDS = {"nt":[], "posix":[]}
        DATABASE_START_COMMANDS["posix"] = ["sudo service mysql start", "sudo mysqld_safe &", "sudo mysql &", "sudo /etc/init.d/mysqld start &", "sudo systemctl start mysql"]
        #TODO: Don't hardcode the MySQL Server path. 
        DATABASE_START_COMMANDS["nt"] = ["C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysqld", "net start mysql", "net start MariaDB"]
        for command in DATABASE_START_COMMANDS[OS_TYPE]:
            ret = common.run_command(command)
            if not ret['returncode']:
                print("Started the database.")
                print("Waiting 5 seconds for database to initialize...")
                sleep(5)
                return True
        print("All options for starting the database were exhausted.")
        print("The database software may not be fully installed, or the command isn't included in the set used here.")
        print("Consult your database software's documentation for information on the correct procedure.")
        raise TaskFailure()
    
    @staticmethod
    def initialize_submodules():
        SetupUtils.check_for_git()
        print("Initializing submodules...")
        ret = common.run_command("git submodule init")
        ret = common.run_command("git submodule update")

    @staticmethod
    def migrate():
        pass

    @staticmethod
    def activate_venv():
        venv_working_directory = SetupUtils.get_venv_working_directory()
        #this is slightly better looking garbage than a reimpl of _test_for_venv, will keep for now?
        if not InstallHandler._test_for_venv(InstallHandler, venv_working_directory):
            print("A virtual environment hasn't been set up or couldn't be found.", style=TEXT_STYLES["bold"])
            print("You may have chosen not to set up a virtual environment during initial setup or you're running this script from somewhere other than Maximilian's root directory.")
            print("You'll need to choose 'Install dependencies only' in the 'Install' menu to set one up.")
            return
        if constants.GlobalConstants.WITHIN_VENV:
            print("A virtual environment is already activated.")
            return
        root_logger.debug(f"Attempting to activate virtual environment at {venv_working_directory}")
        ret = SetupUtils.run_os_dependent_command(f"source {venv_working_directory}/bin/activate", f"{venv_working_directory}\\Scripts\\activate.bat")
        if ret["returncode"]:
            print("Couldn't activate the virtual environment. More details:")
            print(ret["output"])
            print("-----")
            raise TaskFailure()
        print("Activated the virtual environment.")

    @staticmethod
    def create_venv():
        venv_creation_handler = InstallHandler(single_use=True)
        ret = venv_creation_handler.create_venv()
        if ret:
            print("Virtual environment created.")
        else:
            print("Not creating a virtual environment.")
        
    @staticmethod
    def install_dependencies():
        pass

    @staticmethod
    def test_task():
        print("Test task ran")

class SetupTaskHandler:
    """Wraps and handles individual tasks. Returns task output as a TaskResults instance."""

    @staticmethod
    def run_task(task):
        try:
            root_logger.debug(f"Running task '{task.__name__}'")
            ret = task()
        except TaskFailure as exc:
            root_logger.debug(f"Task '{task.__name__}' exited with TaskExitStatus.FAILURE, returned '{exc.ret}'")
            return TaskResults(status=TaskExitStatus.FAILURE, ret=exc.ret, context=exc)
        except Exception as exc:
            if type(exc) == GitCommandFailed:
                print(SetupStrings.GIT_COMMAND_FAILED_WITHIN_TASK)
                print(exc.context["output"])
            root_logger.debug(f"Task '{task.__name__}' exited with TaskExitStatus.EXCEPTION:")
            root_logger.debug(traceback.format_exc())
            return TaskResults(status=TaskExitStatus.EXCEPTION, ret=None, context=exc)
        root_logger.debug(f"Task '{task.__name__}' exited successfully ")
        return TaskResults(status=TaskExitStatus.SUCCESS, ret=ret)

    #TODO: Generate run_task callbacks at runtime instead of this? This may not be the *best* way to do this but it'll stay for now.
    #Using functools.partial every time I wish to run a task as a callback will get annoying. 
    #Generating these callbacks from a list of tasks (prob involving setattr) may be hard to follow.
    RUN_INITIALIZE_SUBMODULES_TASK = functools.partial(run_task, SetupTasks.initialize_submodules)
    RUN_START_DATABASE_TASK = functools.partial(run_task, SetupTasks.start_database)
    RUN_UPDATE_SUBMODULES_TASK = functools.partial(run_task, SetupTasks.update_submodules)
    RUN_BACKUP_TASK = functools.partial(run_task, SetupTasks.backup)
    RUN_RESTORE_TASK = functools.partial(run_task, SetupTasks.restore)
    RUN_UPDATE_TASK = functools.partial(run_task, SetupTasks.update)
    RUN_FULL_INSTALL_TASK = functools.partial(run_task, SetupTasks.full_install)
    RUN_INSTALL_NO_DATABASE_TASK = functools.partial(run_task, SetupTasks.install_no_database)
    RUN_INSTALL_DATABASE_TASK = functools.partial(run_task, SetupTasks.install_database)
    RUN_CLEAR_CACHES_TASK = functools.partial(run_task, SetupTasks.clear_caches)
    RUN_LAUNCH_DATABASE_CLIENT_TASK = functools.partial(run_task, SetupTasks.launch_database_client)
    RUN_CHANGE_DATABASE_PASSWORD_TASK = functools.partial(run_task, SetupTasks.change_database_password)
    RUN_MIGRATE_TASK = functools.partial(run_task, SetupTasks.migrate)
    RUN_ACTIVATE_VENV_TASK = functools.partial(run_task, SetupTasks.activate_venv)
    RUN_INSTALL_DEPENDENCIES_TASK = functools.partial(run_task, SetupTasks.install_dependencies)
    RUN_CREATE_VENV_TASK = functools.partial(run_task, SetupTasks.create_venv)
    RUN_TEST_TASK = functools.partial(run_task, SetupTasks.test_task)

class SetupConstants:
    """Various non-string constants used by Setup."""   
    
    REQUIRED_PACKAGES = ["mariadb-server", "python3-pip", "ffmpeg", "python3-venv"]
    MAIN_MENU_OPTIONS = ["Install", "Database options", "Repair", {"Migrate to 2.0":SetupTaskHandler.RUN_MIGRATE_TASK}, {"Run updater":SetupTaskHandler.RUN_UPDATE_TASK}, "Help", "More", "Exit"]
    MORE_OPTIONS = [{"Clear caches":SetupTaskHandler.RUN_CLEAR_CACHES_TASK}, {"Activate virtual environment":SetupTaskHandler.RUN_ACTIVATE_VENV_TASK}, "Help", "Main Menu"]
    INSTALL_OPTIONS = [{"Full install (recommended)":SetupTaskHandler.RUN_FULL_INSTALL_TASK}, {"Install without database":SetupTaskHandler.RUN_INSTALL_NO_DATABASE_TASK}, {"Install database only":SetupTaskHandler.RUN_INSTALL_DATABASE_TASK}, "Help", "Main Menu"]
    DATABASE_OPTIONS = [{"Reinstall database":SetupTaskHandler.RUN_INSTALL_DATABASE_TASK}, {"Change database password":SetupTaskHandler.RUN_CHANGE_DATABASE_PASSWORD_TASK}, {"Start database":SetupTaskHandler.RUN_START_DATABASE_TASK}, {"Back up database":SetupTaskHandler.RUN_BACKUP_TASK}, {"Restore database":SetupTaskHandler.RUN_RESTORE_TASK}, {"Launch database client":SetupTaskHandler.RUN_LAUNCH_DATABASE_CLIENT_TASK}, "Help", "Main Menu"]
    REPAIR_OPTIONS = [{"Install dependencies":SetupTaskHandler.RUN_INSTALL_DEPENDENCIES_TASK}, {"Create virtual environment":SetupTaskHandler.RUN_CREATE_VENV_TASK}, "Main Menu"]
    MAIN_MENU = SetupUtils.IntMenu(options=MAIN_MENU_OPTIONS, prompt=SetupStrings.MAIN_MENU_PROMPT)
    MORE_MENU = SetupUtils.IntMenu(options=MORE_OPTIONS, prompt=SetupStrings.MORE_PROMPT)
    DATABASE_MENU = SetupUtils.IntMenu(options=DATABASE_OPTIONS, prompt=SetupStrings.DATABASE_MENU_PROMPT)
    INSTALL_MENU = SetupUtils.IntMenu(options=INSTALL_OPTIONS, prompt=SetupStrings.INSTALL_MENU_PROMPT)
    REPAIR_MENU = SetupUtils.IntMenu(options=REPAIR_OPTIONS, prompt=SetupStrings.REPAIR_MENU_PROMPT)

class SetupDatabaseClient:
    """A simple database client born from the ashes of a test written for db_utils
        Very limited and only allows operations permitted under the maximilianbot user."""
    db = None
    conn = None
    ip : str = None
    pw : str = None
    name : str = None
    OPTIONS_IN_MEMORY_MENU = SetupUtils.BooleanMenu(prompt="It looks like you've already used the database client in this session. \nDo you want to re-use the credentials provided earlier?")
    RUN_INITIALIZE_SUBMODULES_TASK_MENU = SetupUtils.BooleanMenu(prompt="Would you like to run that now?", YES_CALLBACK=SetupTaskHandler.RUN_INITIALIZE_SUBMODULES_TASK)
    RECONNECT_MENU = SetupUtils.BooleanMenu(prompt="Would you like to re-initialize the database client?", YES_CALLBACK=SetupTaskHandler.RUN_LAUNCH_DATABASE_CLIENT_TASK)

    @staticmethod
    def _initialize():
        """Do most of the initialization work. Load API, obtain credentials and IP address, other things."""
        if not SetupDatabaseClient.conn:
            root_logger.debug("Not connected, loading db api")
            ret = SetupUtils.load_database_api()
            if not ret:
                print("The database API couldn't be loaded.")
                print("If Maximilian is already installed, try running the 'Initialize submodules' task.")
                ret = SetupDatabaseClient.RUN_INITIALIZE_SUBMODULES_TASK_MENU.handle_menu()
                #Did we run the task?
                if type(ret["return"]) == TaskResults:
                    if ret["return"].status == TaskExitStatus.SUCCESS:
                        print("Submodule initialization succeeded. Launch the database client again.")
                    else:
                        if ret["return"].status == TaskExitStatus.EXCEPTION:
                            print(traceback.format_exception(ret["return"].context))
                        print("Submodule initialization failed. See the output above.")
                else:
                    print("Alright. Maximilian's submodules and dependencies must be installed for the database client to work.")
                    print("You may want to run the 'Install without database' task.")
                raise CleanExit
            if SetupDatabaseClient.pw is not None and SetupDatabaseClient.ip is not None and SetupDatabaseClient.name is not None:
                ret = SetupDatabaseClient.OPTIONS_IN_MEMORY_MENU.handle_menu()
                if ret["choice"]: #The user chose to re-use their previous credentials.
                    return
                print("Ok.")
            print("Enter the name of the database to connect to. This is not the IP address. Press 'Enter' to use the default ('maximilian'):")
            SetupDatabaseClient.name = input().strip()
            if not SetupDatabaseClient.name:
                SetupDatabaseClient.name = "maximilian"
            print("Please enter the database password:")
            SetupDatabaseClient.pw = getpass.getpass().strip()
            SetupDatabaseClient.ip = SetupGlobalState.ip

    @staticmethod
    def _create_connection():
        SetupDatabaseClient.conn = SetupDatabaseClient.db.db(user="maximilianbot", password=SetupDatabaseClient.pw, ip=SetupDatabaseClient.ip, database=SetupDatabaseClient.name)

    @staticmethod
    def initialize():
        """Initialize the database client. Handle initialization failure and establish connection."""
        print("Initializing database client.")
        try:
            SetupDatabaseClient._initialize()
            SetupDatabaseClient._create_connection()
        except CleanExit:
            raise CleanExit
        except Exception as exc:
            if not SetupGlobalState.db_available:
                root_logger.debug("db not available, starting it.")
                ret = SetupTaskHandler.RUN_START_DATABASE_TASK()
                if ret.status == TaskExitStatus.FAILURE:
                    return False
                SetupGlobalState.db_available = True
                try:
                    SetupDatabaseClient._create_connection()
                    return
                except Exception as ex:
                    traceback.print_exc()
                    raise ex
            print("The database client wasn't able to initialize. Here's some more details about the error.")
            traceback.print_exc()
            raise exc

    @staticmethod
    def main_loop():
        print("")
        while True:
            try:
                root_logger.debug("Entering DatabaseClient prompt")
                cmd = input("> ").strip()
                if cmd == "help":
                    pass
                elif cmd == "quit":
                    raise CleanExit
                else:
                    root_logger.debug(f"Running command '{cmd}'")
                    out = SetupDatabaseClient.conn.exec(cmd, ())
                    if out:
                        print(out)
            except KeyboardInterrupt:
                print("\nCtrl-C pressed - exiting!")
                raise CleanExit
            except CleanExit:
                raise CleanExit
            except:
                print("Command raised an exception:")
                traceback.print_exc()

    def end():
        """Exit the database client."""
        root_logger.debug("Closing database connection")
        SetupDatabaseClient.conn.conn.close()
        SetupDatabaseClient.conn = None

    def main():
        """Initialize the database client and start its main loop."""
        try:
            SetupDatabaseClient.initialize()
        except CleanExit:
            if SetupDatabaseClient.conn:
                SetupDatabaseClient.end()
            #Return without exception? Task technically succeeded.
            return
        #Unhandled exceptions are handled one level up by SetupTaskHandler
            
        try:
            SetupDatabaseClient.main_loop()
        except CleanExit:
            print("Cleaning up.")
            SetupDatabaseClient.end()

#TODO: Write preferences to config and keep them between sessions
def pre_setup():
    """Ask a couple questions before starting Setup."""
    root_logger.info("A couple questions before starting setup:")
    #Ask about text formatting.
    FORMATTING_MENU = SetupUtils.BooleanMenu(prompt="Do you want to enable text formatting? This makes output prettier but may not work on some systems.\nChoose 'No' if the above text isn't displaying correctly.")
    print("\nThis is a test of text formatting.", fg=TEXT_STYLES["cyan"], style=TEXT_STYLES["bold"])
    response = FORMATTING_MENU.handle_menu()
    if response["choice"]:
        print("Text formatting enabled.", style=TEXT_STYLES["bold"])
    else:
        #This should not be limited to this scope. Linter is stupid
        FORMATTING_ENABLED = False
        print("Text formatting disabled.")
    
    dbip = common.get_value(SetupGlobalState.config, "dbip")
    if dbip:
        print("\nLooks like your database is set up on a different computer.", style=TEXT_STYLES["bold"])
        print(f"The IP address is '{dbip}'.")
        print("If this isn't correct, remove the 'dbip' field from 'config' and restart Setup.\n")
        SetupGlobalState.remote = True
        SetupGlobalState.ip = dbip
        return
    #Then ask about whether the database server is not local.
    REMOTE_MENU = SetupUtils.BooleanMenu(prompt="Is the database set up on a different computer?\nCareful, your answer will affect some options during this session. For example, database setup will be skipped during a full install.\nUnsure? Choose 'No'.")
    response = REMOTE_MENU.handle_menu()
    if response["choice"]:
        SetupGlobalState.remote = True
        SetupGlobalState.ip = input("Enter the IP address of the remote database:\n").strip()
        print(f"\nRemote database IP address set to '{SetupGlobalState.ip}'.\n", style=TEXT_STYLES["bold"])
    else:
        SetupGlobalState.remote = False
        SetupGlobalState.ip = "localhost"

def _forward_menu(menu):
    SetupGlobalState.menu_stack.append(menu)
    SetupGlobalState.current_menu = menu

def _back_menu():
    SetupGlobalState.menu_stack.pop()
    SetupGlobalState.current_menu = SetupGlobalState.menu_stack[-1]

def setup_main():
    """Main method for Setup."""
    #Ask a few questions before entering the main loop.
    pre_setup()
    #Then show the introduction message
    print(SetupStrings.INTRO_HEADER, style=TEXT_STYLES["bold"])
    print(SetupStrings.INTRO_DESC)
    sleep(1)

    while True:
        #Show the menu and handle input.
        root_logger.debug("Showing current menu.")
        ret = SetupGlobalState.current_menu.handle_menu()
        chosen_option = SetupGlobalState.current_menu.options[ret["choice"]]

        if chosen_option == "Exit":
            raise KeyboardInterrupt

        #Check if the user requested help.
        #This check is intended to be index-agnostic in case options change in the future.
        if chosen_option == "Help":
            if SetupGlobalState.current_menu == SetupConstants.MAIN_MENU:
                print(SetupStrings.MAIN_MENU_HELP)
            elif SetupGlobalState.current_menu == SetupConstants.MORE_MENU:
                print(SetupStrings.MORE_MENU_HELP)
            elif SetupGlobalState.current_menu == SetupConstants.DATABASE_MENU:
                print(SetupStrings.DATABASE_MENU_HELP)
            elif SetupGlobalState.current_menu == SetupConstants.INSTALL_MENU:
                print(SetupStrings.INSTALL_MENU_HELP)

        #Check for menu changes.
        if chosen_option == "More":
            root_logger.debug("Showing additional options.")
            _forward_menu(SetupConstants.MORE_MENU)
        elif chosen_option == "Install":
            root_logger.debug("Showing installation options.")
            _forward_menu(SetupConstants.INSTALL_MENU)
        elif chosen_option == "Database options":
            root_logger.debug("Showing database options.")
            _forward_menu(SetupConstants.DATABASE_MENU)
        elif chosen_option == "Repair":
            root_logger.debug("Showing repair options.")
            _forward_menu(SetupConstants.REPAIR_MENU)
        elif chosen_option == "Main Menu" or chosen_option == "Back":
            print("Returning to the previous menu.")
            _back_menu()

        #Why are we returning to the menu?
        menu_callback_return = ret["return"]
        if type(menu_callback_return) == TaskResults:
            if menu_callback_return.status == TaskExitStatus.FAILURE:
                print("\nSorry, looks like a task failed.", style=TEXT_STYLES["bold"])
            elif menu_callback_return.status == TaskExitStatus.EXCEPTION:
                root_logger.debug("Uncaught exception in menu callback!")
                root_logger.debug(traceback.format_exc())
                print("\nSorry, a task exited with an error.", style=TEXT_STYLES["bold"])
            elif menu_callback_return.status == TaskExitStatus.SUCCESS:
                pass
            print("\nReturning to the menu.")
        print("")

def cleanup():
    #Clean up dangling file handlers and delete temporary files
    root_logger.debug("Cleaning up.")
    if SetupGlobalState.LOCK_FILE_HANDLER:
        SetupGlobalState.LOCK_FILE_HANDLER.close()
        os.unlink("setup.lock")
    if SetupGlobalState.config_found and SetupGlobalState.config:
        SetupUtils.write_config("config")

def _handle_restart(reason):
    if reason.startswith("activated_venv"):
        root_logger.debug("Determining how to continue install")
        pts = reason.split(",")
        if len(pts) < 2:
            root_logger.debug("No continue_install_with specified.")
            return ""
        continue_install_with = getattr(SetupTaskHandler, pts[1], None)
        if not continue_install_with:
            root_logger.debug(f"continue_install_with was set to '{pts[1]}' but was not defined. It must be a SetupTaskHandler classmethod!")
            return None
        if not callable(continue_install_with):
            root_logger.debug(f"continue_install_with must be callable!")
            return None
        print("Now that your virtual environment is activated, installation can continue.", style=TEXT_STYLES["bold"])
        return continue_install_with()
    else:
        root_logger.debug("This restart reason is not handled!")
        return ""

#Definitions finished, let's initialize :)

#Determine the initial logging level
if IS_DEBUG:
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

#Initialize our global state.
SetupGlobalState = SetupState()

restart_reason = common.get_value(SetupGlobalState.config, "restart_reason", 0)
if restart_reason:
    ret = _handle_restart(restart_reason)
    if ret is None:
        print("Sorry, Setup wasn't able to continue where you left off.", style=TEXT_STYLES["bold"])
        print("If this happens again, run setup.py with -v and report the error.")
    elif ret == "":
        print("Sorry, Setup wasn't able to figure out where you left off.", style=TEXT_STYLES["bold"])
        print("If this happens again, run setup.py with -v and report the error.")
    elif type(ret) == TaskResults:
        if not "-u" in sys.argv:
            sys.argv = sys.argv.append("-u")
        FORMATTING_ENABLED = True


if __name__ == "__main__":
    if not "-u" in sys.argv:
        print("Hi!\nThis setup script is a re-implementation of the current setup script.\nIt's not at all ready for use yet.")
        print("It offers a refreshed user experience and a few more features, but it could break your installation.\n")
        print("For setup, repairs, and other tasks, please continue to use setup.sh for the time being.")
        print("If you wish to test this out, run it with -u.")
        cleanup()
        quit()
    try:
        setup_main()
    except (KeyboardInterrupt, CleanExit):
        print("\nExiting setup.")
        cleanup()
    except SystemExit:
        pass
    except Exception as exc:
        print("Setup exited unexpectedly! Please report this error.")
        traceback.print_exc()
        cleanup()

