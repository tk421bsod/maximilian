import logging
import os
import traceback

import common

from setup import shared_utils
from setup import constants

class SetupState:
    _current_instance = None

    def __new__(cls):
        root_logger = logging.getLogger('setup')
        #root_logger.debug("Checking for existing SetupState.")
        if not SetupState._current_instance:
            root_logger.debug("Initializing new SetupState.")
            SetupState._current_instance = super().__new__(cls)
        else:
            pass #root_logger.debug("A SetupState already exists. Call SetupState().destroy to clear the current instance.")
        return SetupState._current_instance

    def __init__(self):
        if hasattr(self, "_initialized"): #Do not perform initialization if we've already initialized
            return

        from setup import deferred_constants
        
        root_logger = logging.getLogger('setup')
        root_logger.debug("Initializing global state")
        self._initialized = True
        self.pw = ""
        self.ip = "%"
        self.current_menu = deferred_constants.MAIN_MENU
        self.menu_stack = [deferred_constants.MAIN_MENU]
        self.LOCK_FILE_HANDLER = None
        self.install_in_progress = None
        self.db_available = False
        self.remote = None
        self.ip = "localhost"
        self.config_found = True
        temp_config_exists = os.path.exists("config.tmp")
        lock_file_exists = os.path.exists("setup.lock")
        setup_state_exists = os.path.exists("setup_state.tmp")
        root_logger.debug(f"Temp config: {temp_config_exists} | Lock file: {lock_file_exists} | Saved state: {setup_state_exists}")
        if setup_state_exists:
            self.config = common.load_config("setup_state.tmp")
            root_logger.debug(self.config)
            root_logger.debug(f"Saved state detected. Restart reason: {self.config['restart_reason']}")
            os.unlink("setup_state.tmp")
            return
        try:
            if lock_file_exists:
                print("Setup exited unexpectedly.", style=constants.TEXT_STYLES["bold"])
                if temp_config_exists and not setup_state_exists:
                    print("Your configuration data from that session was lost.", style=constants.TEXT_STYLES["bold"])
                    print("You must finish the setup process to save your configuration data.")
                    os.unlink("config.tmp")
                else:
                    print("No configuration data was lost.")
            elif temp_config_exists and not setup_state_exists:
                print("You exited Setup before a task was finished.\nYour configuration data from that session was lost.", style=constants.TEXT_STYLES["bold"])
                print("You must finish the setup process to save your configuration data.")
                os.unlink("config.tmp")
            root_logger.debug("Loading config.")
            self.config = common.load_config()
            root_logger.debug("Creating lock file.")
            self.LOCK_FILE_HANDLER = open("setup.lock", "w")
        except FileNotFoundError:
            root_logger.debug("Config not found.")
            self.config = {}
            self.config_found = False
        except:
            root_logger.debug("Could not load/parse config. See exc info below")
            root_logger.debug(traceback.format_exc())
            print("The configuration file couldn't be loaded. Run setup.py with -v to show more information.")
            print("This file will be overwritten if you use any options from the 'Install' menu.")
            self.config = {}
            self.config_found = False

    def destroy(self):
        logging.getLogger('setup').debug("Destroying SetupState!")
        SetupState._current_instance = None

    def was_config_changed(self):
        "Return whether config has changed during this session."
        on_disk = common.load_config()
        diff = not (self.config == on_disk)
        shared_utils.get_root_logger().debug(f"Config changed: {diff}")
        return diff

    def convert_config(self):
        "Convert configuration data from a dict to a string to write."
        root_logger = shared_utils.get_root_logger()
        config = ""
        root_logger.debug("Converting config to string")
        for k, v in self.config.items():
            config += f"{k}:{v}\n"
        root_logger.debug(f"Resulting config string: {config}")
        return config

    def write_config(self, path):
        "Write configuration data from convert_config to a file at 'path'. Overwrites config file contents."
        config = self.convert_config()
        shared_utils.get_root_logger().debug(f"Writing config to file {path}")
        with open(path, "w") as configfile:
            configfile.write(config)

    def save_state(self, reason="None"):
        """Save the current config to setup_state.tmp"""
        root_logger = logging.getLogger('setup')
        root_logger.debug(f"Temporarily saving current config with reason '{reason}'.")
        self.config["restart_reason"] = reason
        self.write_config("setup_state.tmp")
        root_logger.debug("Temporary config saved")

    def load_state(self):
        """Load saved temporary config from setup_state.tmp"""
        root_logger = logging.getLogger('setup')
        if not os.path.isfile("setup_state.tmp"):
            root_logger.debug("No saved temporary config found")
            return None
        config = common.load_config('setup_state.tmp')
        root_logger.debug("Loaded saved temporary config.")
        self.config.update(config)
