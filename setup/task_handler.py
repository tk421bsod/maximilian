import functools
import traceback
import logging

from setup.task_models import TaskResults, TaskExitStatus, TaskFailure, GitCommandFailed
from setup import task_logic
from setup import strings
from setup import shared_utils

def run_task(task):
    root_logger = shared_utils.get_root_logger()
    try:
        root_logger.debug(f"Running task '{task.__name__}'")
        ret = task()
    except TaskFailure as exc:
        root_logger.debug(f"Task '{task.__name__}' exited with TaskExitStatus.FAILURE, returned '{exc.ret}'")
        return TaskResults(status=TaskExitStatus.FAILURE, ret=exc.ret, context=exc)
    except Exception as exc:
        if type(exc) == GitCommandFailed:
            print(strings.GIT_COMMAND_FAILED_WITHIN_TASK)
            print(exc.context["output"])
        root_logger.debug(f"Task '{task.__name__}' exited with TaskExitStatus.EXCEPTION:")
        root_logger.debug(traceback.format_exc())
        return TaskResults(status=TaskExitStatus.EXCEPTION, ret=None, context=exc)
    root_logger.debug(f"Task '{task.__name__}' exited successfully ")
    return TaskResults(status=TaskExitStatus.SUCCESS, ret=ret)

#TODO: Generate menu callbacks dynamically instead of this? This may not be the *best* way to do this but it'll stay for now.
#Using shared_utils.task_partial_with_doc every time I wish to run a task as a callback will get annoying. 
#Generating these callbacks from a list of tasks (prob involving setattr) may be hard to follow.
RUN_INITIALIZE_SUBMODULES_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.initialize_submodules)
RUN_START_DATABASE_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.start_database)
RUN_UPDATE_SUBMODULES_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.update_submodules)
RUN_BACKUP_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.backup)
RUN_RESTORE_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.restore)
RUN_UPDATE_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.update)
RUN_FULL_INSTALL_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.full_install)
RUN_INSTALL_NO_DATABASE_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.install_no_database)
RUN_INSTALL_DATABASE_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.install_database)
RUN_INSTALL_PHASE_2_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.full_install_phase_2)
RUN_CLEAR_CACHES_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.clear_caches)
RUN_LAUNCH_DATABASE_CLIENT_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.launch_database_client)
RUN_CHANGE_DATABASE_PASSWORD_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.change_database_password)
RUN_MIGRATE_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.migrate)
RUN_SHOW_VENV_ACTIVATION_HELP_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.show_venv_activation_help)
RUN_CHECK_VENV_ACTIVATED_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.check_venv_activated)
RUN_INSTALL_DEPENDENCIES_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.install_dependencies)
RUN_CREATE_VENV_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.create_venv)
RUN_TEST_TASK = shared_utils.task_partial_with_doc(run_task, task_logic.test_task)

