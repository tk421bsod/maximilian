print("Setup is starting...")

from setup import task_logic

from setup import constants
from setup.state import SetupState
from setup import strings
from setup.task_models import TaskExitStatus, TaskResults, GitCommandFailed, TaskFailure, CleanExit
from setup import task_handler
from setup import shared_utils
from setup import ui

import common

from time import sleep
import traceback
import sys
import os

from setup import deferred_constants

def get_submenu_help(menu_type):
    submenu_help_string = common.get_value(strings.SUBMENU_HELP, menu_type, "additional options")
    print(f"{strings.SUBMENU_HELP_PREFIX}{submenu_help_string}.")

def get_menu_help():
    menu = SetupState().current_menu
    print("---- Help for the current menu ----")
    for num, option in enumerate(menu.options):
        if not type(option) == dict:
            print(f"{num+1}) {option}", style=constants.TEXT_STYLES["bold"])
            submenu_type = option.split(" ")[0].lower()
        if type(option) == dict:
            print(f"{num+1}) {list(option.keys())[0]}", style=constants.TEXT_STYLES["bold"])
            task = list(option.values())[0]
            #Grab the docstring from the partial function. (shared_utils.partial_with_doc sets this)
            doc = getattr(task, "__doc__", strings.DEFAULT_HELP)
            if not doc:
                doc = strings.DEFAULT_HELP
            print(f"    {doc}")
        elif option == "Main Menu":
            print(strings.MAIN_MENU_RETURN_HELP)
        elif option == "Exit":
            print(strings.EXIT_HELP)
        elif option == "Back":
            print(strings.PREVIOUS_MENU_HELP)
        elif option == "Help":
            print(strings.HELP_HELP)
        elif submenu_type in constants.MENU_LIST:
            get_submenu_help(submenu_type)
        else:
            print("Help text not implemented for this option, sorry")
    print("----")

def _setup_main_loop():
    root_logger = shared_utils.get_root_logger()
    while True:
        #Show the menu and handle input.
        root_logger.debug("Showing current menu.")
        ret = SetupState().current_menu.handle_menu()
        chosen_option = SetupState().current_menu.options[ret["choice"]]

        if chosen_option == "Exit":
            return

        #Check if the user requested help.
        #This check is intended to be index-agnostic in case options change in the future.
        if chosen_option == "Help":
            get_menu_help()

        #Check for menu changes.
        if chosen_option == "More":
            root_logger.debug("Showing additional options.")
            ui.forward_menu(deferred_constants.MORE_MENU)
        elif chosen_option == "Install":
            root_logger.debug("Showing installation options.")
            ui.forward_menu(deferred_constants.INSTALL_MENU)
        elif chosen_option == "Virtual environment options":
            root_logger.debug("Showing virtual environment options.")
            ui.forward_menu(deferred_constants.VENV_MENU)
        elif chosen_option == "Database options":
            root_logger.debug("Showing database options.")
            ui.forward_menu(deferred_constants.DATABASE_MENU)
        elif chosen_option == "Repair":
            root_logger.debug("Showing repair options.")
            ui.forward_menu(deferred_constants.REPAIR_MENU)
        elif chosen_option == "Main Menu" or chosen_option == "Back":
            print("Returning to the previous menu.")
            ui.back_menu()

        #Why are we returning to the menu?
        menu_callback_return = ret["return"]
        if type(menu_callback_return) == TaskResults:
            if menu_callback_return.status == TaskExitStatus.FAILURE:
                print("\nSorry, looks like a task failed.", style=constants.TEXT_STYLES["bold"])
            elif menu_callback_return.status == TaskExitStatus.EXCEPTION:
                root_logger.debug("Uncaught exception in menu callback!")
                root_logger.debug(traceback.format_exc())
                print("\nSorry, a task exited with an error. Run setup with -v, or enable debugging information, to show details.", style=constants.TEXT_STYLES["bold"])
            elif menu_callback_return.status == TaskExitStatus.SUCCESS:
                pass
            input("Press Enter to return to the menu.")
            print("\nReturning to the menu.")

def _pre_setup():
    """Ask a couple questions before starting Setup."""
    root_logger = shared_utils.get_root_logger()
    root_logger.info("A couple questions before starting setup:")
    #Ask about text formatting.
    FORMATTING_MENU = ui.BooleanMenu(prompt="Do you want to enable text formatting? This makes output prettier but may not work on some systems.\nChoose 'No' if the above text isn't displaying correctly.")
    print("\nThis is a test of text formatting.", fg=constants.TEXT_STYLES["cyan"], style=constants.TEXT_STYLES["bold"])
    response = FORMATTING_MENU.handle_menu()
    if response["choice"]:
        print("Text formatting enabled.", style=constants.TEXT_STYLES["bold"])
    else:
        SetupState().FORMATTING_ENABLED = False
        print("Text formatting disabled.")
    
    dbip = common.get_value(SetupState().config, "dbip")
    if dbip:
        print("\nIt looks like your database is set up on a different computer.", style=constants.TEXT_STYLES["bold"])
        print(f"The IP address is '{dbip}'.")
        print("If this isn't correct, remove the 'dbip' field from 'config' and restart Setup.\n")
        SetupState().remote = True
        SetupState().ip = dbip
        return
    #Then ask about whether the database server is not local.
    REMOTE_MENU = ui.BooleanMenu(prompt="Is the database set up on a different computer?\nCareful, your answer will affect some options during this session. For example, database setup will be skipped during a full install.\nUnsure? Choose 'No'.")
    response = REMOTE_MENU.handle_menu()
    if response["choice"]:
        SetupState().remote = True
        SetupState().ip = input("Enter the IP address of the remote database:\n").strip()
        print(f"\nRemote database IP address set to '{SetupState().ip}'.\n", style=constants.TEXT_STYLES["bold"])
    else:
        SetupState().remote = False
        SetupState().ip = "localhost"

def cleanup():
    #Clean up dangling file handlers and delete temporary files
    root_logger = shared_utils.get_root_logger()
    root_logger.debug("Cleaning up.")
    if SetupState().LOCK_FILE_HANDLER:
        SetupState().LOCK_FILE_HANDLER.close()
        os.unlink("setup.lock")
        root_logger.debug("Removed lock file.")
    if SetupState().config_found and SetupState().config:
        if SetupState().install_in_progress: #Discard config if we were in the middle of an install.
            root_logger.debug("Installation exited unexpectedly! Not writing config.")
            return
        if SetupState().was_config_changed():
            SetupState().write_config("config")
        else:
            root_logger.debug("Config has not changed, skipping write")
    else:
        root_logger.debug("No config to write.")

def _handle_restart(reason):
    root_logger = shared_utils.get_root_logger()
    if reason.startswith("activated_venv"):
        root_logger.debug("Determining how to continue install")
        pts = reason.split(",")
        if len(pts) < 2:
            root_logger.debug("No continue_install_with specified.")
            return ""
        continue_install_with = getattr(task_handler, pts[1], None)
        if not continue_install_with:
            root_logger.debug(f"continue_install_with was set to '{pts[1]}' but is not an attribute of task_handler. It must be a task_handler method!")
            return None
        if not callable(continue_install_with):
            root_logger.debug(f"continue_install_with must be callable!")
            return None
        if sys.exec_prefix == sys.base_exec_prefix:
            print("Your virtual environment is not activated! You must activate it to continue.")
            task_handler.RUN_SHOW_VENV_ACTIVATION_HELP_TASK()
            SetupState().save_state(reason)
            raise CleanExit
        print("Now that your virtual environment is activated, installation can continue.", style=constants.TEXT_STYLES["bold"])
        ret = continue_install_with()
        print("Installation finished. Returning to the menu.")
    else:
        root_logger.debug("This restart reason is not handled!")
        return ""

def _check_for_restart():
    restart_reason = common.get_value(SetupState().config, "restart_reason", 0)
    if restart_reason:
        ret = _handle_restart(restart_reason)
        if ret is None:
            print("Sorry, Setup wasn't able to continue where you left off.", style=constants.TEXT_STYLES["bold"])
            print("If this happens again, run setup.py with -v and report the error.")
        elif ret == "":
            print("Sorry, Setup wasn't able to figure out where you left off.", style=constants.TEXT_STYLES["bold"])
            print("If this happens again, run setup.py with -v and report the error.")
        elif type(ret) == TaskResults: #_handle_restart ran a task!
            if not "-u" in sys.argv: #This flag keeps this setup script from being unintentionally used. Appending it to sys.argv forces Setup to run
                sys.argv = sys.argv.append("-u")
            SetupState().FORMATTING_ENABLED = True #There isn't a good way to save these flags across restarts yet. TODO: Add these to config?
            return True


def setup_main():
    """Main method for Setup."""
    #Before starting the main loop, check if we've restarted.
    ret = _check_for_restart()
    #Were we ran with the intention of testing this script?
    if not "-u" in sys.argv:
        print("Hi!\nThis is a re-implementation of the current setup script.\nIt's not at all ready for use yet.")
        print("It offers a refreshed user experience and a few more features, but it could break your installation!\n")
        print("For setup, repairs, and other tasks, please run setup.sh.")
        print("If you wish to test this out, run it with -u.")
        cleanup()
        quit()
    if not ret: #Skip introductions if we've just finished an install.    
        #Ask a few questions before entering the main loop.
        _pre_setup()
        #Then show the introduction message
        print(strings.INTRO_HEADER, style=constants.TEXT_STYLES["bold"])
        print(strings.INTRO_DESC)
    sleep(1)
    root_logger = shared_utils.get_root_logger()
    root_logger.debug("Entering main loop")
    _setup_main_loop()
    root_logger.debug("Exiting main loop")

if __name__ == "__main__":
    print("Sorry, this script cannot be executed directly. Please run setup.py from the repository root directory.")
