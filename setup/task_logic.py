import sys
import time

import common
import constants as maximilian_constants

from setup import constants
from setup.shared_utils import get_root_logger
from setup import shared_utils
from setup.task_models import CleanExit, TaskExitStatus, TaskResults, TaskFailure, GitCommandFailed
from setup.install_handler import InstallHandler
from setup import venv_utils
from setup import ui

def potentially_destructive(func):
    @property
    def __doc__():
        shared_utils.get_root_logger().debug(f"Returning docstring for potentially_destructive wrapped func: '{func.__doc__}'")
        return func.__doc__

    def potentially_destructive_inner(*args, **kwargs):
        print(f"\nAre you sure that you want to do this?", style=constants.TEXT_STYLES["bold"])
        print("If you don't know what you are doing, this option may cause a loss of data or break your installation.")
        potentially_destructive_menu = ui.BooleanMenu(prompt="")
        ret = potentially_destructive_menu.handle_menu()
        if ret["choice"]:
            func(*args, **kwargs)
    return potentially_destructive_inner

    potentially_destructive_inner.__doc__ = __doc__

def full_install():
    """Install everything. Recommended in most cases."""
    root_logger = get_root_logger()
    root_logger.debug("Starting first phase of full install")
    root_logger.debug("Initializing InstallHandler")
    installer = InstallHandler()
    root_logger.debug("Preparing for install")
    installer.prepare()
    root_logger.debug("Gathering installation info")
    installer.gather_information()
    root_logger.debug("Installing required packages")
    installer.install_packages()
    root_logger.debug("Creating virtual environment")
    venv_created = installer.create_venv()
    import task_handler
    if venv_created:
        installer.install_python_dependencies_venv_phase_1(task_handler.RUN_INSTALL_PHASE_2_TASK)
    else:
        installer.install_python_dependencies()
        task_handler.RUN_INSTALL_PHASE_2_TASK()

def full_install_phase_2():
    root_logger = get_root_logger()
    root_logger.debug("Starting second phase of full install")

def install_no_database():
    """Install Maximilian and its dependencies, but skip database setup. Use this option if you already have the database set up on another computer."""
    pass

def install_database():
    """Install Maximilian's database and skip everything else. Use this option if you want to host your database separately."""
    pass

def update():
    """Check for updates."""
    import updater
    #Force update check
    sys.argv.append("--force-update")
    updater.update()
    sys.argv.remove("--force-update")

def backup():
    pass

def setup_database():
    pass

def change_database_password():
    pass

def clear_caches():
    pass

def restore():
    pass

@potentially_destructive
def launch_database_client():
    """Start a simple database client."""
    from setup.db_client import SetupDatabaseClient
    return SetupDatabaseClient.main()

def update_submodules():
    shared_utils.check_for_git()
    ret = common.run_command("git submodule update")
    if ret["returncode"]:
        raise GitCommandFailed(ret)

def start_database():
    """Start the database server."""
    DATABASE_START_COMMANDS = {"nt":[], "posix":[]}
    DATABASE_START_COMMANDS["posix"] = ["sudo service mysql start", "sudo mysqld_safe &", "sudo mysql &", "sudo /etc/init.d/mysqld start &", "sudo systemctl start mysql"]
    #TODO: Don't hardcode the MySQL Server path. 
    DATABASE_START_COMMANDS["nt"] = ["C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysqld", "net start mysql", "net start MariaDB"]
    print("Trying to start the database server. You may be prompted for your password.")
    for command in DATABASE_START_COMMANDS[constants.OS_TYPE]:
        ret = common.run_command(command)
        if not ret['returncode']:
            print("Started the database server.")
            print("Waiting 5 seconds for database server to initialize...")
            time.sleep(5)
            return True
    print("All options for starting the database were exhausted.")
    print("The database software may not be fully installed, or the command isn't included in the set used here.")
    print("Consult your database software's documentation for information on the correct procedure.")
    raise TaskFailure()

def initialize_submodules():
    """Set up dependencies that live in Git submodules."""
    shared_utils.check_for_git()
    print("Initializing submodules.")
    ret = common.run_command("git submodule init")
    ret = common.run_command("git submodule update")

def migrate():
    """Move from 1.x to 2.0."""
    pass

def show_venv_activation_help():
    """Show steps to activate the virtual environment."""
    venv_utils.show_venv_activation_help()

def check_venv_activated():
    """Check if the virtual environment is activated."""
    if maximilian_constants.GlobalConstants.WITHIN_VENV:
        print("Your virtual environment is active.")
    else:
        print("Your virtual environment is not active.")
        print("For help, choose 'Show virtual environment activation help' from the menu.")

def create_venv():
    """Create a virtual environment to install dependencies to."""
    venv_creation_handler = InstallHandler(single_use=True)
    ret = venv_creation_handler.create_venv()
    if ret:
        print("Virtual environment created.")
    else:
        print("Not creating a virtual environment.")
    
def install_dependencies():
    """Install software Maximilian depends on."""
    pass

def test_task():
    print("Test task ran")
