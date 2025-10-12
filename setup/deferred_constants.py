from setup import strings
from setup import task_handler
from setup import ui

REQUIRED_PACKAGES = ["mariadb-server", "python3-pip", "ffmpeg", "python3-venv"]
MAIN_MENU_OPTIONS = ["Install", "Database options", "Virtual environment options", "Repair", {"Migrate to 2.0":task_handler.RUN_MIGRATE_TASK}, {"Run updater":task_handler.RUN_UPDATE_TASK}, "Help", "More", "Exit"]
MORE_OPTIONS = [{"Clear caches":task_handler.RUN_CLEAR_CACHES_TASK}, "Help", "Main Menu"]
INSTALL_OPTIONS = [{"Full install (recommended)":task_handler.RUN_FULL_INSTALL_TASK}, {"Install without database":task_handler.RUN_INSTALL_NO_DATABASE_TASK}, {"Install database only":task_handler.RUN_INSTALL_DATABASE_TASK}, "Help", "Main Menu"]
DATABASE_OPTIONS = [{"Reinstall database":task_handler.RUN_INSTALL_DATABASE_TASK}, {"Change database password":task_handler.RUN_CHANGE_DATABASE_PASSWORD_TASK}, {"Start database":task_handler.RUN_START_DATABASE_TASK}, {"Back up database":task_handler.RUN_BACKUP_TASK}, {"Launch database client":task_handler.RUN_LAUNCH_DATABASE_CLIENT_TASK}, "Help", "Main Menu"]
REPAIR_OPTIONS = [{"Install dependencies":task_handler.RUN_INSTALL_DEPENDENCIES_TASK}, "Main Menu"]
VENV_OPTIONS = [{"Create virtual environment":task_handler.RUN_CREATE_VENV_TASK}, {"Show virtual environment activation help":task_handler.RUN_SHOW_VENV_ACTIVATION_HELP_TASK}, {"Check virtual environment activation status":task_handler.RUN_CHECK_VENV_ACTIVATED_TASK}, "Help", "Main Menu"]

MAIN_MENU = ui.IntMenu(options=MAIN_MENU_OPTIONS, prompt=strings.MAIN_MENU_PROMPT)
MORE_MENU = ui.IntMenu(options=MORE_OPTIONS, prompt=strings.MORE_PROMPT)
DATABASE_MENU = ui.IntMenu(options=DATABASE_OPTIONS, prompt=strings.DATABASE_MENU_PROMPT)
INSTALL_MENU = ui.IntMenu(options=INSTALL_OPTIONS, prompt=strings.INSTALL_MENU_PROMPT)
REPAIR_MENU = ui.IntMenu(options=REPAIR_OPTIONS, prompt=strings.REPAIR_MENU_PROMPT)
VENV_MENU = ui.IntMenu(options=VENV_OPTIONS, prompt=strings.VENV_MENU_PROMPT)
