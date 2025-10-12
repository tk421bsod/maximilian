from setup import logging_utils
logging_utils.initialize_logging()

from setup import main
from setup.state import SetupState
from setup.task_models import CleanExit

import traceback

if __name__ == "__main__":
    try:
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
