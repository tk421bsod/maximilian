import logging
import importlib
import traceback
import os

import common

from setup.task_models import GitCommandFailed

def get_root_logger():
    return logging.getLogger('setup')

def load_database_api():
    """Attempt to import the database API. If the import fails, returns False. Upon success, returns True."""
    from setup.db_client import SetupDatabaseClient
    try:
        SetupDatabaseClient.db = importlib.import_module("db_utils.db")
    except:
        traceback.print_exc()
        return False
    return True

def run_os_dependent_command(linux_command, windows_command):
    get_root_logger().debug(f"Running OS dependent command, linux: {linux_command} windows: {windows_command}")
    os_type = os.name
    if os_type == "nt":
        ret = common.run_command(windows_command)
    elif os_type == "posix":
        ret = common.run_command(linux_command)
    get_root_logger().debug(ret)
    return ret

def run_git_command(cmd):
    """Run a Git command and raise GitCommandFailed if it fails."""
    get_root_logger().debug("Running Git command")
    ret = common.run_command(cmd)
    if ret["returncode"]:
        raise GitCommandFailed(ret)
    return ret

def check_for_git():
    """Check for an active Git repository in the current working directory. Use before tasks that perform Git operations."""
    ret = run_git_command("git status")
