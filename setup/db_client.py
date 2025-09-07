import traceback
import getpass

from setup.state import SetupState
from setup import shared_utils 
from setup.task_models import CleanExit, TaskResults, TaskExitStatus
from setup import task_handler
from setup import ui

class SetupDatabaseClient:
    """A simple database client born from the ashes of a test written for db_utils
        Very limited and only allows operations permitted under the maximilianbot user."""
    db = None
    conn = None
    ip : str = None
    pw : str = None
    name : str = None
    OPTIONS_IN_MEMORY_MENU = ui.BooleanMenu(prompt="It looks like you've already used the database client in this session. \nDo you want to re-use the credentials provided earlier?")
    RUN_INITIALIZE_SUBMODULES_TASK_MENU = ui.BooleanMenu(prompt="Would you like to run that now?", YES_CALLBACK=task_handler.RUN_INITIALIZE_SUBMODULES_TASK)
    RECONNECT_MENU = ui.BooleanMenu(prompt="Would you like to re-initialize the database client?", YES_CALLBACK=task_handler.RUN_LAUNCH_DATABASE_CLIENT_TASK)

    @staticmethod
    def _initialize():
        """Do most of the initialization work. Load API, obtain credentials and IP address, other things."""
        if not SetupDatabaseClient.conn:
            shared_utils.get_root_logger().debug("Not connected, loading db api")
            ret = shared_utils.load_database_api()
            if not ret:
                print("The database API couldn't be loaded.")
                print("If Maximilian is already installed, try running the 'Initialize submodules' task.")
                ret = SetupDatabaseClient.RUN_INITIALIZE_SUBMODULES_TASK_MENU.handle_menu()
                #Did we run the task?
                if type(ret["return"]) == TaskResults:
                    if ret["return"].status == TaskExitStatus.SUCCESS:
                        print("Submodule initialization succeeded. Launch the database client again.")
                    else:
                        if ret["return"].status == TaskExitStatus.EXCEPTION:
                            print(traceback.format_exception(ret["return"].context))
                        print("Submodule initialization failed. See the output above.")
                else:
                    print("Alright. Maximilian's submodules and dependencies must be installed for the database client to work.")
                    print("You may want to run the 'Install without database' task.")
                raise CleanExit
            if SetupDatabaseClient.pw is not None and SetupDatabaseClient.ip is not None and SetupDatabaseClient.name is not None:
                ret = SetupDatabaseClient.OPTIONS_IN_MEMORY_MENU.handle_menu()
                if ret["choice"]: #The user chose to re-use their previous credentials.
                    return
                print("Ok.")
            print("Enter the name of the database to connect to. This is not the IP address. Press 'Enter' to use the default ('maximilian'):")
            SetupDatabaseClient.name = input().strip()
            if not SetupDatabaseClient.name:
                SetupDatabaseClient.name = "maximilian"
            print("Please enter the database password:")
            SetupDatabaseClient.pw = getpass.getpass().strip()
            SetupDatabaseClient.ip = SetupState().ip

    @staticmethod
    def _create_connection():
        SetupDatabaseClient.conn = SetupDatabaseClient.db.db(user="maximilianbot", password=SetupDatabaseClient.pw, ip=SetupDatabaseClient.ip, database=SetupDatabaseClient.name)

    @staticmethod
    def initialize():
        """Initialize the database client. Handle initialization failure and establish connection."""
        print("Initializing database client.")
        try:
            SetupDatabaseClient._initialize()
            SetupDatabaseClient._create_connection()
        except CleanExit:
            raise CleanExit
        except Exception as exc:
            if not SetupState().db_available:
                shared_utils.get_root_logger().debug("db not available, starting it.")
                ret = task_handler.RUN_START_DATABASE_TASK()
                if ret.status == TaskExitStatus.FAILURE:
                    return False
                SetupState().db_available = True
                try:
                    SetupDatabaseClient._create_connection()
                    return
                except Exception as ex:
                    traceback.print_exc()
                    raise ex
            print("The database client wasn't able to initialize. Here's some more details about the error.")
            traceback.print_exc()
            raise exc

    @staticmethod
    def main_loop():
        print("")
        root_logger = shared_utils.get_root_logger()
        while True:
            try:
                root_logger.debug("Entering DatabaseClient prompt")
                cmd = input("> ").strip()
                if cmd == "help":
                    pass
                elif cmd == "quit":
                    raise CleanExit
                else:
                    root_logger.debug(f"Running command '{cmd}'")
                    out = SetupDatabaseClient.conn.exec(cmd, ())
                    if out:
                        print(out)
            except KeyboardInterrupt:
                print("\nCtrl-C pressed - exiting!")
                raise CleanExit
            except CleanExit:
                raise CleanExit
            except:
                print("Command raised an exception:")
                traceback.print_exc()

    def end():
        """Exit the database client."""
        shared_utils.get_root_logger().debug("Closing database connection")
        SetupDatabaseClient.conn.conn.close()
        SetupDatabaseClient.conn = None

    def main():
        """Initialize the database client and start its main loop."""
        try:
            SetupDatabaseClient.initialize()
        except CleanExit:
            if SetupDatabaseClient.conn:
                SetupDatabaseClient.end()
            #Return without exception? Task technically succeeded.
            return
        #Unhandled exceptions are handled one level up by SetupTaskHandler
            
        try:
            SetupDatabaseClient.main_loop()
        except CleanExit:
            print("Cleaning up.")
            SetupDatabaseClient.end()