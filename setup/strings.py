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
