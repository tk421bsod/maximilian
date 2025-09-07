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
    def potentially_destructive_inner(*args, **kwargs):
        """Warn about a potentially destructive operation"""
        print(f"\nAre you sure that you want to do this?", style=constants.TEXT_STYLES["bold"])
        print("If you don't know what you are doing, this option may cause a loss of data or break your installation.")
        potentially_destructive_menu = ui.BooleanMenu(prompt="")
        ret = potentially_destructive_menu.handle_menu()
        if ret["choice"]:
            func(*args, **kwargs)
    return potentially_destructive_inner

def full_install():
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
    if venv_created:
        import task_handler
        installer.install_python_dependencies_venv_phase_1(task_handler.RUN_INSTALL_PHASE_2_TASK)
    else:
        installer.install_python_dependencies()
        task_handler.RUN_INSTALL_PHASE_2_TASK()

def full_install_phase_2():
    root_logger = get_root_logger()
    root_logger.debug("Starting second phase of full install")

def install_no_database():
    pass

def install_database():
    pass

def update():
    from .. import updater
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
    from setup.db_client import SetupDatabaseClient
    return SetupDatabaseClient.main()

def update_submodules():
    shared_utils.check_for_git()
    ret = common.run_command("git submodule update")
    if ret["returncode"]:
        raise GitCommandFailed(ret)

def start_database():
    DATABASE_START_COMMANDS = {"nt":[], "posix":[]}
    DATABASE_START_COMMANDS["posix"] = ["sudo service mysql start", "sudo mysqld_safe &", "sudo mysql &", "sudo /etc/init.d/mysqld start &", "sudo systemctl start mysql"]
    #TODO: Don't hardcode the MySQL Server path. 
    DATABASE_START_COMMANDS["nt"] = ["C:\\Program Files\\MySQL\\MySQL Server 8.0\\bin\\mysqld", "net start mysql", "net start MariaDB"]
    for command in DATABASE_START_COMMANDS[constants.OS_TYPE]:
        ret = common.run_command(command)
        if not ret['returncode']:
            print("Started the database.")
            print("Waiting 5 seconds for database to initialize...")
            time.sleep(5)
            return True
    print("All options for starting the database were exhausted.")
    print("The database software may not be fully installed, or the command isn't included in the set used here.")
    print("Consult your database software's documentation for information on the correct procedure.")
    raise TaskFailure()

def initialize_submodules():
    shared_utils.check_for_git()
    print("Initializing submodules...")
    ret = common.run_command("git submodule init")
    ret = common.run_command("git submodule update")

def migrate():
    pass

def show_venv_activation_help():
    venv_utils.show_venv_activation_help()

def create_venv():
    venv_creation_handler = InstallHandler(single_use=True)
    ret = venv_creation_handler.create_venv()
    if ret:
        print("Virtual environment created.")
    else:
        print("Not creating a virtual environment.")
    
def install_dependencies():
    pass

def test_task():
    print("Test task ran")
