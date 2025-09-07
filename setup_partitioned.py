from setup import main
from setup.state import SetupState
from setup.task_models import CleanExit
from setup import logging_utils

import traceback

if __name__ == "__main__":
    try:
        logging_utils.initialize_logging()
        SetupState() #Initialize shared setup state
        main.setup_main()
    except (KeyboardInterrupt, CleanExit):
        print("\nExiting setup.")
    except SystemExit:
        pass
    except Exception as exc:
        print("Setup exited unexpectedly! Please report this error.")
        traceback.print_exc()
    main.cleanup()
else:
    print("This file is intended to be run directly.")