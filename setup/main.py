from constants import SetupConstants
from state import SetupState
from strings import SetupStrings
from task_models import TaskExitStatus, TaskResults
from task_handler import SetupTaskHandler
from task_logic import SetupTasks
from utils import markdown, shared
from install import InstallUtils

import ui
import text


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
