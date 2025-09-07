import copy
import os

from setup.state import SetupState
from setup import constants
from setup import shared_utils
from setup import ui

import common
import constants as maximilian_constants

def test_for_venv(venv_working_directory):
    """Test if a venv is present at the provided working directory (root dir of venv).
    Checks for the existence of {venv_working_directory}/bin/activate or {venv_working_directory}/Scripts/activate.bat"""
    root_logger = shared_utils.get_root_logger()
    root_logger.debug(f"Checking for venv at {venv_working_directory}")
    #Presence of $DIR/bin/activate indicates a venv is installed here
    if os.path.isfile(f"{venv_working_directory}/bin/activate") or os.path.isfile(f"{venv_working_directory}\\Scripts\\activate.bat"):
        root_logger.debug(f"venv found")
        return True
    root_logger.debug("venv not found")
    return False

def change_venv_dir():
    """Change virtual environment directory."""
    root_logger = shared_utils.get_root_logger()
    root_logger.debug("Changing venv directory")
    DEFAULT_VENV_DIR = maximilian_constants.GlobalConstants.DEFAULT_VENV_DIR
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
            overwrite = ui.BooleanMenu("").handle_menu()['choice']
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

def force_venv_dir_change(parent, target_dir):
    #Change the venv_dir field regardless of the config overwrite preference
    #Save chosen value for restoring later
    parent.overwrite_config_copy = copy.deepcopy(parent.overwrite_config)
    parent.overwrite_config = True
    shared_utils.get_root_logger().debug(f"Changing config venv_dir from '{common.get_value(SetupState().config, 'venv_dir')}' to '{target_dir}'")
    parent.set_config_value("venv_dir", target_dir)
    #Restore chosen config overwrite preference
    parent.overwrite_config = parent.overwrite_config_copy

def check_venv_exists(parent):
    """Check if a virtual environment already exists at either the path specified in 'config' or the default path. Return the path of the existing venv, None if none exists."""
    DEFAULT_VENV_DIR = maximilian_constants.GlobalConstants.DEFAULT_VENV_DIR
    current_venv_dir = common.get_value(SetupState().config, 'venv_dir')
    #Do we have something in either config or our default directory?
    if os.path.exists(DEFAULT_VENV_DIR) or current_venv_dir:
        #Does config contain a valid path?
        if not current_venv_dir or not os.path.exists(current_venv_dir):
            print("The virtual environment location specified in config does not exist.")
            print(f"Currently, it's set to '{current_venv_dir}'.")
            print("Would you like to change this? If not, you'll be asked if you want to create a virtual environment. \nYou'll be brought back to this prompt if you enter a location that doesn't contain a virtual environment.")
            choice = ui.BooleanMenu("").handle_menu()["choice"]
            if choice:
                new_dir = change_venv_dir()
                force_venv_dir_change(parent, new_dir)
                return check_venv_exists(parent)
            else:
                print("Ok. You can now choose whether to use a virtual environment.")
                return None
        #venv dir field in config will override default if it exists
        venv_working_directory = get_venv_working_directory()
        if test_for_venv(venv_working_directory):
            return venv_working_directory
    return None

def get_venv_working_directory():
    venv_dir = common.get_value(SetupState().config, "venv_dir", maximilian_constants.GlobalConstants.DEFAULT_VENV_DIR)
    return venv_dir if os.path.exists(venv_dir) else maximilian_constants.GlobalConstants.DEFAULT_VENV_DIR

def show_venv_activation_help():
    venv_dir = get_venv_working_directory()
    if not test_for_venv(venv_dir):
        print("A virtual environment hasn't been set up or couldn't be found.", style=constants.TEXT_STYLES["bold"])
        print("You may have chosen not to set up a virtual environment during initial setup or you're running this script from somewhere other than Maximilian's root directory.")
        print("You'll need to choose 'Install dependencies only' in the 'Install' menu to set one up.")
        return
    if maximilian_constants.GlobalConstants.WITHIN_VENV:
        print("A virtual environment is already activated.")
        return
    print("To activate your virtual environment, you'll need to run the following command:")
    if os.name == "nt":
        print(f"{venv_dir}\\Scripts\\activate.bat", style=constants.TEXT_STYLES["bold"])
    elif os.name == "posix":
        print(f"source {venv_dir}/bin/activate", style=constants.TEXT_STYLES["bold"])