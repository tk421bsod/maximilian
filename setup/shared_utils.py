#common is a Maximilian module and is located one dir up.
from .. import common

from state import SetupState

def convert_config():
    "Convert configuration data from a dict to a string to write."
    config = ""
    root_logger.debug("Converting config to string")
    for k, v in SetupState.config.items():
        config += f"{k}:{v}\n"
    root_logger.debug(f"Resulting config string: {config}")
    return config

def write_config(path):
    "Write configuration data from convert_config to a file at 'path'. Overwrites config file contents."
    config = convert_config()
    root_logger.debug(f"Writing config to file {path}")
    with open(path, "w") as configfile:
        configfile.write(config)

def load_database_api():
    """Attempt to import the database API. If the import fails, returns False. Upon success, returns True."""
    try:
        SetupDatabaseClient.db = importlib.import_module("db_utils.db")
    except:
        traceback.print_exc()
        return False
    return True

def get_venv_working_directory():
    venv_dir = common.get_value(SetupState.config, "venv_dir")
    return venv_dir if os.path.exists(venv_dir) else constants.GlobalConstants.DEFAULT_VENV_DIR

def run_os_dependent_command(linux_command, windows_command):
    root_logger.debug(f"Running OS dependent command, linux: {linux_command} windows: {windows_command}")
    if OS_TYPE == "nt":
        return common.run_command(windows_command)
    elif OS_TYPE == "posix":
        return common.run_command(linux_command)
    
def run_git_command(cmd):
    """Run a Git command and raise GitCommandFailed if it fails."""
    root_logger.debug("Running Git command")
    ret = common.run_command(cmd)
    if ret["returncode"]:
        raise GitCommandFailed(ret)
    return ret

def check_for_git():
    """Check for an active Git repository in the current working directory. Use before tasks that perform Git operations."""
    ret = SetupUtils.run_git_command("git status")
