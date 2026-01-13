import functools
import logging
import importlib
import traceback
import os

import common

from setup.task_models import GitCommandFailed

def get_root_logger():
    return logging.getLogger('setup')

def partial_with_doc(func, *args):
    """Apply the docstring of the callable args[0] to functools.partial created using func."""
    partial = functools.partial(func, *args)
    if not callable(args[0]):
        print("partial_with_doc args must have a callable as the first element!")
        return partial
    get_root_logger().debug(f"Setting docstring '{args[0].__doc__}' for callable '{args[0].__name__}'")
    partial.__doc__ = args[0].__doc__
    return partial

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
    run_git_command("git status")
