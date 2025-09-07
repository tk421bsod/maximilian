from setup import shared_utils
from setup.state import SetupState
from setup import ui
from setup import install_utils
from setup import strings
from setup import constants
from setup import task_handler
from setup.task_models import TaskFailure, TaskResults
from setup import venv_utils

import common
import sys

class InstallHandler:

    """Container for methods used by the installation process.
    
    Set single_use upon initialization if only using the instance once.
    This prevents methods from outputting contextual information used during a full install.
    """

    def __init__(self, single_use=False):
        self.overwrite_config = False
        self.overwrite_config_menu = ui.BooleanMenu("It looks like you already have configuration data saved.\nDo you want to overwrite it?")
        self.dbp = None
        self.owner_id = None
        self.token = None
        self.automatic_updates_enabled = None
        self.single_use = single_use
        SetupState().install_in_progress = self
        if SetupState().remote is None:
            SetupState().remote = ui.BooleanMenu("Is the database already set up on a different computer?").handle_menu()["choice"]

    def set_config_value(self, k, v):
        if self.overwrite_config:
            SetupState().config[k] = v
        else:
            shared_utils.get_root_logger().debug(f"Not overwriting config key '{k}' with '{v}'")

    def prepare(self):
        """Prepare for the install."""
        if SetupState().config_found:
            self.overwrite_config = self.overwrite_config_menu.handle_menu()["choice"]
        else:
            self.overwrite_config = True
        if constants.OS_TYPE == "nt":
            print("Since you're on Windows, you'll need to install some software on your own.", style=constants.TEXT_STYLES["bold"])
            print("Please install:\n*Python 3.9 or above, ensure it's on your PATH and that 'Install pip' is checked during installation\n*MySQL / MariaDB server\n*FFmpeg (must be on PATH, only for music features)")
            if not SetupState().remote:
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
        print("Initial configuration data created.", style=constants.TEXT_STYLES["bold"])
        print("This will be saved after the setup process finishes.")

    def gather_information(self):
        """Gather information used later on."""
        if not self.overwrite_config:
            print("\nYou chose to not overwrite configuration data.")
            print("Skipping the information gathering step.")
            return
        self.prep_initial_config()
        print("")
        print("There's a few things Setup needs from you.\n", style=constants.TEXT_STYLES["bold"])
        self.token = self.get_token()
        self.set_config_value("token", self.token)
        self.dbp = self.get_database_password()
        self.set_config_value("dbp", self.dbp)
        self.owner_id = self.get_owner_id()
        self.set_config_value("owner_id", self.owner_id)

        print("Would you like to enable automatic updates?")
        self.automatic_updates_enabled = ui.BooleanMenu("Would you like to enable automatic updates?\nIf enabled, Maximilian will attempt to update itself on startup once every 14 days.").handle_menu()["choice"]
        if self.automatic_updates_enabled:
            self.set_config_value("automatic_updates", "1")
            print("Automatic updates enabled.")
        else:
            self.set_config_value("automatic_updates", "0")
            print("Automatic updates disabled.")

    def install_packages(self):
        if constants.OS_TYPE == "posix":
            print("Updating package index...")
            print("You may be prompted to enter your password.")
            ret = common.run_command("sudo apt-get update")
            if ret["returncode"] == 127:
                print("Your Linux distribution doesn't use the 'apt' package manager.")
                print("You'll need to install the required packages manually to get started.")
                print(f"Install {','.join(constants.REQUIRED_PACKAGES[:-1])}, and {constants.REQUIRED_PACKAGES[-1]}.") 
                if not self.single_use:
                    print("Then press Enter to continue.")
                    input()
                    print("Great. Continuing with the installation.")
                return
            print("Installing required packages...")
            ret = common.run_command(f"sudo apt-get install -y {' '.join(constants.REQUIRED_PACKAGES)}")
            if ret["returncode"]:
                print("Package installation failed! Read the above output for more information.")
                raise TaskFailure()
            return
        print("This is a Windows environment, not installing packages.")

    def _acquire_target_venv_dir(self):
        """Get the directory the virtual environment should be installed to and ensure we can install to it. Returns None if a virtual environment should not be installed."""
        ret = venv_utils.check_venv_exists(self)
        if ret:
            print(f"You already have a virtual environment set up at '{ret}'.", style=constants.TEXT_STYLES["bold"])
            print("Would you like to recreate it? This may take some time.")
            venv_recreate_choice = ui.BooleanMenu("").handle_menu()["choice"]
            if not venv_recreate_choice:
                print("Alright, not recreating the virtual environment.")
                return None
            print(f"Recreating the virtual environment at '{ret}'. Please be patient, this may take some time.", style=constants.TEXT_STYLES["bold"])
            return ret
        else:
            print("From Maximilian version 2.0 onwards, Python dependencies for Maximilian are recommended to be installed in a 'virtual environment'.")
            print("This separates dependencies from your global Python packages and is required on many Linux systems.")
            print("The only downside is that the environment must be activated every time you open a new command prompt.")
            print("With this in mind, would you like to create a virtual environment for Maximilian? ('Yes' recommended)")
            venv_choice = ui.BooleanMenu("").handle_menu()["choice"]
            if not venv_choice:
                print("Alright, not installing to a virtual environment.")
                print("Choose 'Create virtual environment' in the Install menu if you want to do this later.")
                return None
            print("Alright, installing to a virtual environment.")
            current_venv_dir = common.get_value(SetupState().config, 'venv_dir')
            if current_venv_dir:
                print("A virtual environment location is already specified through config.")
                print(f"The location is '{current_venv_dir}'.")
                print("Creating the virtual environment at that location.")
                return current_venv_dir
            creation_dir = venv_utils.change_venv_dir()
            print(f"Creating the virtual environment at '{creation_dir}'. Please be patient, this may take some time.", style=constants.TEXT_STYLES["bold"])
            return creation_dir

    def create_venv(self):
        """Prompt for venv creation, create if requested. Return whether the venv was created and set config['venv_dir'] if so. """
        root_logger = shared_utils.get_root_logger()
        import venv
        #Get the directory to install to.
        target_dir = self._acquire_target_venv_dir()
        #Did we choose not to install?
        if not target_dir:
            root_logger.debug("Not installing to a virtual environment.")
            return False
        root_logger.debug(f"Creating venv in directory '{target_dir}'")
        venv.create(target_dir, with_pip=True)
        venv_utils.force_venv_dir_change(self, target_dir)
        return True
    
    def install_python_dependencies(self):
        print("Installing dependencies...")
        ret = common.run_command(f"{sys.executable} -m pip install -r requirements.txt")
        if ret['returncode']:
            print("Looks like dependency installation failed. Here's output from the command that may help:")
            print(ret['output'])
            print("The installation process will continue, but Maximilian will not run until you run 'Install dependencies' from the main setup menu.")
        else:
            print("Finished installing dependencies.")

    def install_python_dependencies_venv_phase_2(self):
        self.install_python_dependencies()
        pass

    def install_python_dependencies_venv_phase_1(self, continue_install_with=None):
        """Display virtual environment activation help if not already activated, then quit Setup. Once Setup is restarted, run the task_handler classmethod named {continue_install_with} to continue the installation"""
        root_logger = shared_utils.get_root_logger()
        root_logger.debug("Installing Python dependencies")
        venv_working_directory = venv_utils.get_venv_working_directory()
        root_logger.debug(f"venv working dir is {venv_working_directory}")
        if self._test_for_venv(venv_working_directory):
            if not constants.GlobalConstants.WITHIN_VENV:
                if not self.single_use:
                    print("Your virtual environment needs to be activated to continue the installation process.")
                else:
                    print("Your virtual environment needs to be activated to install dependencies.")
                task_handler.RUN_SHOW_VENV_ACTIVATION_HELP_TASK()
                print("After activating the virtual environment, restart Setup.")
                if not self.single_use:
                    print("The installation process will automatically resume from this point.")
                if continue_install_with:
                    continue_install_with = "," + continue_install_with
                SetupState().save_state(reason=f"activated_venv{continue_install_with}")
                quit()
            else:
                print("Your virtual environment is already activated.")
                continue_install_with = getattr(task_handler, continue_install_with, None)
                if not continue_install_with:
                    root_logger.debug("Not sure how to continue, we'll just jump to phase 2")
                    return self.install_python_dependencies_venv_phase_2()
                return continue_install_with()

    def initial_database_setup():
        pass