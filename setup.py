"""A Python implementation of setup.sh.
Will replace setup.sh for easier maintenance and platform independence in the future.
"""

if __name__ == "__main__":
    print("Setup is starting.\n")

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
import updater  

OS_TYPE = os.name

original_print = print
TEXT_END = "\x1b[0m"
TEXT_STYLES = {"none":0, "bold":1, "underline":2, "negative1":3, "negative2":5, "black":30, "red":31, "green":32, "yellow":33, "blue":34, "purple":35, "cyan":36, "white":37}
FORMATTING_ENABLED = True
IS_DEBUG = "-v" in sys.argv
LOG_FORMAT = "%(levelname)s:%(name)s:%(funcName)s:%(message)s"

if IS_DEBUG:
    log_level = logging.DEBUG
else:
    log_level = logging.WARN

logging.basicConfig(level=log_level, format=LOG_FORMAT)
root_logger = logging.getLogger("setup")

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
        while text:
            #Check for separators in our text. Replace separators with their style, then print the resulting string.
            for separator, style in [("**", TEXT_STYLES["bold"]), ("~~", TEXT_STYLES["underline"]), ("[red]", TEXT_STYLES["red"]), ("[green]", TEXT_STYLES["green"])]:
                pairs = MarkdownUtils._find_separator_pairs(text, separator)
                processed = ""
                for pair in pairs:
                    #Replace the first part of the pair with a separator.
                    processed += text[:pair[0]] + style
                    #Add the text in between the pairs.
                    processed += text[pair[0]+len(separator):pair[1]]
                    #End the styled portion.
                    processed += TEXT_END
                    #TODO really not sure how to implement this! If we add the rest of the text we might end up with duplicate strings!!!!
                    #Come back to this later thank you future me
                    processed += text[pair[1]]
            return

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
    MORE_PROMPT = "These aren't used very often but may be able to help.\nChoose one from the list below, 'Help' for assistance, or 'Main Menu' to go back:"

    MAIN_MENU_HELP = """\n---- Setup Help ----
Looking to install Maximilian? Choose the **Full install** option.
Already have a database server set up on another computer? Choose **Install without database**.
Want to set up the database server by itself? Choose **Install database only**.
Have an issue? Try **Repair**.
Want to check for updates now? Choose **Run updater**.
Need to back up the database? Choose **Back up database**.
Something else? Choose **More**.
"""
    MORE_HELP = """\n---- More Help ----
Need to re-initialize the database? Choose **Re-run database setup**.
Have a different database password in mind? Choose **Change database password**.
Want to free up some space? Choose **Clear caches**. Some things may take longer to load afterwards.
Database not started? Choose **Start database**. This usually isn't necessary.
Have a backup you want to restore? Choose **Restore database**. Ensure your backup is in the .sql format.
Need to manually modify the database? Choose **Launch database client**. Only use this option if you know what you're doing.
Want to return to the main menu? Choose **Main Menu**.
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
        for k, v in SetupGlobalState.config.items():
            config += f"{k}:{v}\n"
        return config

    @staticmethod
    def write_config(path):
        "Write configuration data from convert_config to a file at 'path'. Overwrites config file contents."
        config = SetupUtils.convert_config()
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
    def run_os_dependent_command(linux_command, windows_command):
        if OS_TYPE == "nt":
            return common.run_command(windows_command)
        elif OS_TYPE == "posix":
            return common.run_command(linux_command)
        
    @staticmethod
    def run_git_command(cmd):
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
                    print(f"Enter a number between 1 and {len(self.options)}.\n")
                    return -2
                return ret-1
            except ValueError:
                print("Enter a number.\n")
            return -2
        
        def handle_menu(self):
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
                print("When you're ready, enter your ID below.")
                continue
            elif owner_id == "":
                print("\nError reporting, 'utils' commands, and Jishaku have been disabled.") 
                print("")
                break
            print("\nOwner ID set.")
            break
        return owner_id

class InstallHandler:

    """Container for methods used by the installation process.
    
    Set single_use upon initialization if only using the instance once.
    This prevents methods from outputting contextual information used during a full install
    """

    def __init__(self, single_use=False):
        self.overwrite_config = False
        self.overwrite_config_menu = SetupUtils.BooleanMenu("It looks like you already have configuration data saved.\nDo you want to overwrite it?")
        self.dbp = None
        self.owner_id = None
        self.token = None
        self.automatic_updates_enabled = None
        self.single_use = single_use
        if SetupGlobalState.remote is None:
            SetupGlobalState.remote = SetupUtils.BooleanMenu("Is the database already set up on a different computer?").handle_menu()["choice"]

    def set_config_value(self, k, v):
        if self.overwrite_config:
            SetupGlobalState.config[k] = v
        else:
            root_logger.debug(f"Not overwriting config key '{k}' with '{v}'")

    def prepare(self):
        """Prepare for the install."""
        if SetupGlobalState.config:
            self.overwrite_config = self.overwrite_config_menu.handle_menu()["choice"]
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
        self.dbp = InstallUtils.get_database_password()
        self.owner_id = InstallUtils.get_owner_id()
        
        print("Would you like to enable automatic updates?")
        self.automatic_updates_enabled = SetupUtils.BooleanMenu("Would you like to enable automatic updates?\nIf enabled, Maximilian will attempt to update itself on startup once every 14 days.").handle_menu()["choice"]
        
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
            ret = common.run_command(f"sudo apt-get install {SetupConstants.REQUIRED_PACKAGES}")
            if ret["returncode"]:
                print("")
            return
        print("This is a Windows environment, not installing packages.")

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

    @staticmethod
    def install_no_database():
        pass

    @staticmethod
    def install_database():
        pass

    @staticmethod
    def repair():
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
    def set_database_password():
        pass

    @staticmethod
    def clear_caches():
        pass

    @staticmethod
    def restore():
        pass

    @staticmethod
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
    RUN_REPAIR_TASK = functools.partial(run_task, SetupTasks.repair)
    RUN_UPDATE_TASK = functools.partial(run_task, SetupTasks.update)
    RUN_FULL_INSTALL_TASK = functools.partial(run_task, SetupTasks.full_install)
    RUN_INSTALL_NO_DATABASE_TASK = functools.partial(run_task, SetupTasks.install_no_database)
    RUN_INSTALL_DATABASE_TASK = functools.partial(run_task, SetupTasks.install_database)
    RUN_CLEAR_CACHES_TASK = functools.partial(run_task, SetupTasks.clear_caches)
    RUN_LAUNCH_DATABASE_CLIENT_TASK = functools.partial(run_task, SetupTasks.launch_database_client)
    RUN_SET_DATABASE_PASSWORD_TASK = functools.partial(run_task, SetupTasks.set_database_password)
    RUN_MIGRATE_TASK = functools.partial(run_task, SetupTasks.migrate)

class SetupConstants:
    """Various non-string constants used by Setup."""   
    
    REQUIRED_PACKAGES = ["mariadb-server", "python3-pip", "ffmpeg", "g++"]
    MAIN_MENU_OPTIONS = [{"Full install (recommended)":SetupTaskHandler.RUN_FULL_INSTALL_TASK}, {"Install without database":SetupTaskHandler.RUN_INSTALL_NO_DATABASE_TASK}, {"Install database only":SetupTaskHandler.RUN_INSTALL_DATABASE_TASK}, {"Repair":SetupTaskHandler.RUN_REPAIR_TASK}, {"Migrate to 2.0":SetupTaskHandler.RUN_MIGRATE_TASK}, {"Run updater":SetupTaskHandler.RUN_UPDATE_TASK}, {"Back up database":SetupTaskHandler.RUN_BACKUP_TASK}, "Help", "More"]
    MORE_OPTIONS = [{"Re-run database setup":SetupTaskHandler.RUN_INSTALL_DATABASE_TASK}, {"Change database password":SetupTaskHandler.RUN_SET_DATABASE_PASSWORD_TASK}, {"Clear caches":SetupTaskHandler.RUN_CLEAR_CACHES_TASK}, {"Start database":SetupTaskHandler.RUN_START_DATABASE_TASK}, {"Restore database":SetupTaskHandler.RUN_RESTORE_TASK}, {"Launch database client":SetupTaskHandler.RUN_LAUNCH_DATABASE_CLIENT_TASK}, "Help", "Main Menu"]
    MAIN_MENU = SetupUtils.IntMenu(options=MAIN_MENU_OPTIONS, prompt=SetupStrings.MAIN_MENU_PROMPT)
    MORE_MENU = SetupUtils.IntMenu(options=MORE_OPTIONS, prompt=SetupStrings.MORE_PROMPT)    

class SetupDatabaseClient:
    """A simple database client born from the ashes of a test written for db_utils
        Very limited and only allows operations permitted under the maximilianbot user."""
    db = None
    conn = None
    ip : str = None
    pw : str = None
    name : str = None
    IS_REMOTE_MENU = SetupUtils.BooleanMenu(prompt="Is the database set up on a different computer?")
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
            print("Enter the name of the database to connect to (defaults to 'maximilian'):")
            SetupDatabaseClient.name = input().strip()
            if not SetupDatabaseClient.name:
                SetupDatabaseClient.name = "maximilian"
            SetupDatabaseClient.pw = input("Please enter the database password:\n").strip()
            print("\r ")
            is_remote = SetupDatabaseClient.IS_REMOTE_MENU.handle_menu()
            if is_remote["choice"]:
                SetupDatabaseClient.ip = input("Enter the IP address of the remote database:\n").strip()
            else:
                SetupDatabaseClient.ip = "localhost"

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

class SetupGlobalState:
    pw = ""
    ip = "%"        
    current_menu = SetupConstants.MAIN_MENU
    LOCK_FILE_HANDLER = None
    install_in_progress = None
    db_available = False
    remote = None
    try:
        if os.path.exists("setup.lock"):
            print("Setup exited unexpectedly.", style=TEXT_STYLES["bold"])
            if os.path.exists("config.tmp"):
                print("Your configuration data from that session was lost.", style=TEXT_STYLES["bold"])
                print("You must finish the setup process to save your configuration data.")
                os.unlink("config.tmp")
            else:
                print("No configuration data was lost.")
        elif os.path.exists("config.tmp"):
            print("You exited Setup before a task was finished.\nYour configuration data from that session was lost.", style=TEXT_STYLES["bold"])
            print("You must finish the setup process to save your configuration data.")
            os.unlink("config.tmp")
        if __name__ == "__main__":
            root_logger.debug("Loading config.")
            config = common.load_config()
            root_logger.debug("Creating lock file.")
            LOCK_FILE_HANDLER = open("setup.lock", "w")
        else:
            config = None
    except FileNotFoundError:
        root_logger.debug("Config not found.")
        config = None
    except:
        root_logger.debug("Could not load/parse config. See exc info below")
        root_logger.debug(traceback.format_exc())

#TODO: Write preferences to config and keep them between sessions
def pre_setup():
    """Ask a couple questions before starting Setup."""
    print("A couple questions before starting setup:")
    #Ask about text formatting.
    FORMATTING_MENU = SetupUtils.BooleanMenu(prompt="Do you want to enable text formatting? This makes output prettier but may not work on some systems.\nChoose 'No' if the above text isn't displaying correctly.")
    print("\nThis is a test of text formatting.", fg=TEXT_STYLES["cyan"], style=TEXT_STYLES["bold"])
    response = FORMATTING_MENU.handle_menu()
    if response["choice"]:
        print("Text formatting enabled.", style=TEXT_STYLES["bold"])
    else:
        #Linter is dumb AF, this should not be limited to this scope 
        FORMATTING_ENABLED = False
        print("Text formatting disabled.")
    #Then ask about debug logging.
    DEBUG_MENU = SetupUtils.BooleanMenu(prompt="Would you like to show debugging information? This may make output a little harder to read.")
    response = DEBUG_MENU.handle_menu()
    if response["choice"]:
        logging.basicConfig(level=logging.DEBUG, format=LOG_FORMAT)

def setup_main():
    """Main method for Setup."""
    #Ask a few questions before entering the main loop.
    pre_setup()
    os.system("cls" if OS_TYPE == "nt" else "clear")
    #Then show the introduction message
    print(SetupStrings.INTRO_HEADER, style=TEXT_STYLES["bold"])
    print(SetupStrings.INTRO_DESC)
    sleep(1)

    while True:
        #Show the menu and handle input.
        root_logger.debug("Showing current main menu.")
        ret = SetupGlobalState.current_menu.handle_menu()
        chosen_option = SetupGlobalState.current_menu.options[ret["choice"]]

        #Check if the user requested help.
        #This check is intended to be index-agnostic in case options change in the future.
        if SetupGlobalState.current_menu == SetupConstants.MAIN_MENU and chosen_option == "Help":
            print(SetupStrings.MAIN_MENU_HELP)
        elif SetupGlobalState.current_menu == SetupConstants.MORE_MENU and chosen_option == "Help":
            print(SetupStrings.MORE_HELP)
        
        #Check for menu changes.
        if SetupGlobalState.current_menu == SetupConstants.MAIN_MENU and chosen_option == "More":
            SetupGlobalState.current_menu = SetupConstants.MORE_MENU
        elif SetupGlobalState.current_menu == SetupConstants.MORE_MENU and chosen_option == "Main Menu":
            SetupGlobalState.current_menu = SetupConstants.MAIN_MENU

        #TODO: What do we do after a task exits? This might be too high up for exception handling.
        if type(ret["return"]) == TaskResults:
            if ret["return"].status == TaskExitStatus.FAILURE:
                print("\nSorry, looks like a task failed. Returning to the menu.", style=TEXT_STYLES["bold"])
            elif ret["return"].status == TaskExitStatus.EXCEPTION:
                root_logger.debug("Uncaught exception in menu callback!")
                root_logger.debug(traceback.format_exc())
                print("\nSorry, a task exited with an error. Returning to the menu.", style=TEXT_STYLES["bold"])
            else:
                print("\nReturning to the menu.")
        print("")

def cleanup():
    #Clean up dangling file handlers and delete temporary files
    root_logger.debug("Cleaning up.")
    if SetupGlobalState.LOCK_FILE_HANDLER:
        SetupGlobalState.LOCK_FILE_HANDLER.close()
        os.unlink("setup.lock")

if __name__ == "__main__":
    if not "-u" in sys.argv:
        print("Hi!\nThis setup script is a re-implementation of the current setup script.\nIt's not at all ready for use yet.")
        print("Many things will not exist, the things that do are most likely broken and could break your installation.\n")
        print("For setup, repairs, and other tasks, please continue to use setup.sh for the time being.")
        print("If you wish to test this out, run it with -u.")
        quit()
    try:
        setup_main()
    except (KeyboardInterrupt, CleanExit):
        print("\nExiting setup.")
        cleanup()
    except Exception as exc:
        print("Setup exited unexpectedly! Please report this error.")
        traceback.print_exc()
        cleanup()

