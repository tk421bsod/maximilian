import logging
import functools

from task_models import TaskResults, TaskExitStatus, GitCommandFailed
from task_logic import SetupTasks
from shared_utils import root_logger

class SetupTaskHandler:
    """Wraps and handles individual tasks. Returns task output as a TaskResults instance."""

    @staticmethod
    def run_task(task):
        try:
            root_logger.debug(f"Running task '{task.__name__}'")
            ret = task()
        except TaskFailure as exc:
            root_logger.debug(f"Task '{task.__name__}' exited with TaskExitStatus.FAILURE, returned '{exc.ret}'")
            return TaskResults(status=TaskExitStatus.FAILURE, ret=exc.ret, context=exc)
        except Exception as exc:
            if type(exc) == GitCommandFailed:
                print(SetupStrings.GIT_COMMAND_FAILED_WITHIN_TASK)
                print(exc.context["output"])
            root_logger.debug(f"Task '{task.__name__}' exited with TaskExitStatus.EXCEPTION:")
            root_logger.debug(traceback.format_exc())
            return TaskResults(status=TaskExitStatus.EXCEPTION, ret=None, context=exc)
        root_logger.debug(f"Task '{task.__name__}' exited successfully ")
        return TaskResults(status=TaskExitStatus.SUCCESS, ret=ret)

    #TODO: Generate run_task callbacks at runtime instead of this? This may not be the *best* way to do this but it'll stay for now.
    #Using functools.partial every time I wish to run a task as a callback will get annoying. 
    #Generating these callbacks from a list of tasks (prob involving setattr) may be hard to follow.
    RUN_INITIALIZE_SUBMODULES_TASK = functools.partial(run_task, SetupTasks.initialize_submodules)
    RUN_START_DATABASE_TASK = functools.partial(run_task, SetupTasks.start_database)
    RUN_UPDATE_SUBMODULES_TASK = functools.partial(run_task, SetupTasks.update_submodules)
    RUN_BACKUP_TASK = functools.partial(run_task, SetupTasks.backup)
    RUN_RESTORE_TASK = functools.partial(run_task, SetupTasks.restore)
    RUN_UPDATE_TASK = functools.partial(run_task, SetupTasks.update)
    RUN_FULL_INSTALL_TASK = functools.partial(run_task, SetupTasks.full_install)
    RUN_INSTALL_NO_DATABASE_TASK = functools.partial(run_task, SetupTasks.install_no_database)
    RUN_INSTALL_DATABASE_TASK = functools.partial(run_task, SetupTasks.install_database)
    RUN_CLEAR_CACHES_TASK = functools.partial(run_task, SetupTasks.clear_caches)
    RUN_LAUNCH_DATABASE_CLIENT_TASK = functools.partial(run_task, SetupTasks.launch_database_client)
    RUN_CHANGE_DATABASE_PASSWORD_TASK = functools.partial(run_task, SetupTasks.change_database_password)
    RUN_MIGRATE_TASK = functools.partial(run_task, SetupTasks.migrate)
    RUN_ACTIVATE_VENV_TASK = functools.partial(run_task, SetupTasks.activate_venv)
    RUN_INSTALL_DEPENDENCIES_TASK = functools.partial(run_task, SetupTasks.install_dependencies)
    RUN_CREATE_VENV_TASK = functools.partial(run_task, SetupTasks.create_venv)
    RUN_TEST_TASK = functools.partial(run_task, SetupTasks.test_task)
