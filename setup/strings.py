INTRO_HEADER = "---- Maximilian Setup ----"
INTRO_DESC = "This utility helps automate Maximilian's initial setup process. \nIt can also assist with a few common maintenance tasks."
MAIN_MENU_PROMPT = "Choose an option from the list below, or 'Help' for explanations:"
MORE_PROMPT = "These options aren't used very often but may be able to help.\nChoose one from the list below, 'Help' for assistance, or 'Main Menu' to go back:"
INSTALL_MENU_PROMPT = "Choose an installation type, 'Help' for assistance, or 'Main Menu' to go back:"
DATABASE_MENU_PROMPT = "Choose a database action to perform, 'Help' for assistance, or 'Main Menu' to go back:"
REPAIR_MENU_PROMPT = "Choose an option, 'Help' for assistance, or 'Main Menu' to go back:"
VENV_MENU_PROMPT = "Choose a virtual environment management option, 'Help' for assistance, or 'Main Menu' to go back:"

DEFAULT_HELP = "No help text provided."
SUBMENU_HELP_PREFIX = "    Submenu providing "
SUBMENU_HELP = {"install":"options for installing Maximilian", "database":"options for database maintenance", "virtual":"virtual environment creation, deletion, and activation options",  "repair":"options for repairing issues with your installation"}
MAIN_MENU_RETURN_HELP = "    Return to the main menu."
PREVIOUS_MENU_HELP = "    Return to the previous menu."
EXIT_HELP = "    Exit the setup utility."
HELP_HELP = "    Display help for this menu."

MAIN_MENU_HELP = "\n---- Setup Help ----"
MORE_HELP = "\n---- More Help ----"
DATABASE_MENU_HELP = "\n---- Database Options Help ----"
INSTALL_MENU_HELP = "\n---- Install Help ----"
UNINSTALL_MENU_HELP = "\n---- Uninstall Help ----"

POSIX_HELP_STRINGS = {
    "DATABASE_NOT_STARTED":"Did you enter the correct password when prompted?"


}
NT_HELP_STRINGS = {
    "DATABASE_NOT_STARTED":"\n*You might not have permission to start the database.\nTry running 'net start mysql' or 'net start MariaDB' from an Administrator Command Prompt.\\n\n*FOR MARIADB INSTALLS: You might not have installed MariaDB as a service.\nRun the installer again and ensure that 'Install as service' is checked. The service name must be either 'mysql' or 'MariaDB'."
                    

}
GIT_COMMAND_FAILED_WITHIN_TASK = "A Git command failed. This task cannot continue."
GIT_COMMAND_FAILED_FATAL = "A Git command failed. Setup cannot continue."
GIT_COMMAND_FAILED_MORE = "Read the above output carefully, then check HOSTING.md for more information."

VENV_DIR_NOT_WRITABLE = "Your virtual environment location is not writable! Write permissions are required to create a virtual environment."

