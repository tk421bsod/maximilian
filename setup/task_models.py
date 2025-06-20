class GitCommandFailed(BaseException):
    """Raised to indicate a Git command failed within a task. Includes the output of the run_command call that failed."""

    def __init__(self, context):
        self.context = context

class TaskFailure(BaseException):
    """Raised to indicate that a task failed. Includes a slot for the return value of the task."""
    
    __slots__ = ("ret")
    
    def __init__(self, ret=None):
        self.ret = ret

class TaskExitStatus:
    SUCCESS = 0
    FAILURE = 1
    EXCEPTION = 2

class TaskResults:
    """Returned from SetupTaskHandler."""
    
    def __init__(self, status, ret, context=None):
        self.status : TaskExitStatus = status
        self.ret = ret
        self.context : typing.Optional[Exception] = context
