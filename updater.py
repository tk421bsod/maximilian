import logging
import os
import subprocess
import time
import datetime
import sys

import common
from common import Text

class CleanExit(BaseException):
    """Cleanly exit the updater."""

def list_in_str(list, string):
    '''
    Tests if any elements in 'list' are in 'string'.

    Returns:
        True - An element in 'list' is in 'string'.
        False - No elements in 'list' are in 'string'.
    '''
    for elem in list:
        if elem in string:
            return True
    return False

def _print_git_output(output):
    print("\n-----")
    print("Git output:")
    print("\n".join(output))
    print("-----\n")

def _show_branch_advice(branch):
    """Show some helpful advice pertaining to the current branch. Exits with a KeyboardInterrupt if `branch` is empty."""
    print()
    if not branch:
        print(f"{Text.BOLD}It doesn't look like you're on a branch.{Text.NORMAL}")
        print("You may be in a 'detached HEAD' state.")
        print("Consider checking out either the 'release' or 'development' branch.")
        print("See the `troubleshooting` section in HOSTING.md or https://stackoverflow.com/questions/10228760 for more information.")
        time.sleep(1)
        raise KeyboardInterrupt
    print(f"{Text.BOLD}You're currently on the '{branch}' branch.")
    if branch == 'development':
        print(f"Updates on this branch may break things.{Text.NORMAL}")
        print("You can switch back to the 'release' branch at any time using 'git checkout release'.")
        print("If an update breaks something, reset to the previous commit using 'git reset HEAD~1'.")
        print("If you decide to revert, you may need to go back to the latest commit with `git reset --hard HEAD` before you can receive further updates.")
    elif branch == 'release':
        print(f"This branch contains the latest stable version of Maximilian.{Text.NORMAL}")
        print("This branch is only updated with increments of the version number.")
        print("You can switch to other branches at any time using 'git checkout <branch>'.")
        print("Use 'git branch' to view a list of branches.")
    else:
        print(f"I can't tell what kind of branch this is.{Text.NORMAL}")
        print("You're either on a release snapshot branch for version 2.0 onward or your own custom branch.")
        print("Old releases don't receive support and may stop working without notice.")
        print("For the latest changes, consider switching to the `release` branch using `git checkout release`.")
    print()

def _die():
    """Do an unclean exit if a Git command failed."""
    print(f"{Text.BOLD}One or more Git commands failed. The updater cannot continue.{Text.NORMAL}")
    print("Git doesn't provide enough information to programatically determine an error, so you should read the above output carefully.")
    print("See the `troubleshooting` section of HOSTING.md for help.")
    time.sleep(1)
    raise KeyboardInterrupt

def _run_git_command(command, exit=True):
    """Run a Git command. Interrupts the updater if it fails and `exit` is True."""
    ret = common.run_command(command)
    if exit and ret['returncode'] in [1, 128]:
       _print_git_output(ret['output'])
       _die()
    return ret
    
def _clean_exit():
    """Exit the updater cleanly (i.e without showing 'Updater interrupted.' after the exit)"""
    raise CleanExit

def _process_last_update_timestamp(config):
    """Obtains and converts the last update timestamp, then exits if conditions for an update check are not met."""
    #Get our last update timestamp.
    last_update = common.get_value(config, 'last_update')
    #No timestamp? Either this is a new install or we were interrupted.
    if not last_update:
        print("Updater was interrupted or last update failed. Checking for updates now.")
    elif "--force-update" in sys.argv or "--update" in sys.argv:
        print("main.py was invoked with --force-update. Checking for updates now.")
    else:
        #Convert our last update timestamp from a Unix timestamp to a datetime.
        last = datetime.datetime.fromtimestamp(int(last_update))
        #Then format it nicely:
        # ...                                      "was at HOUR:MINUTE <AM/PM> on MONTH DAY, YEAR."
        print(f"{Text.BOLD}Last check for updates was at {last.strftime('%-I:%M %p on %B %d, %Y.')}{Text.NORMAL}")
        elapsed = (datetime.datetime.now()-last).days
        #Do we have automatic updates enabled? Default to True
        automatic_updates = common.get_value(config, 'automatic_updates', True)
        #If we don't, politely ask if the user wants to check for updates.
        if not automatic_updates:
            print("Automatic updates aren't enabled. Would you like to check for updates? Y/N\n")
            if input().strip().lower() == "y":
                print("Ok, checking for updates...")
            else:
                print("Ok, not checking for updates.")
                time.sleep(0.5)
                _clean_exit()
        elif elapsed > 14:
            print("It's been more than 14 days since the last update. Updating now.")
        #Exit if it's been less than 14 days.
        else:
            print(f"It's been {elapsed} days since the last update. To force an update, run main.py with --force-update.")
            time.sleep(1)
            _clean_exit()

def _fetch_changes_from_remote(remote):
    """Attempts to fetch changes from `remote`. Exits the updater if unsuccessful."""
    #Remove last update timestamp.
    #Interrupting the updater before we set it again will result in an immediate update check next time.
    common.run_command("sed -i \"s/last_update:.*/last_update:/\" config")
    #Fetch changes from the remote.
    #Cleanly exit and display a non-generic message if the fetch fails. 
    fetch = _run_git_command(f"git fetch {remote}", exit=False)
    _print_git_output(fetch['output'])
    if fetch['returncode']:
        print(f"{Text.BOLD}Update check failed. See the above output for details.{Text.NORMAL}")
        _clean_exit()
    #Set last update timestamp to the current time.
    common.run_command(f"sed -i \"s/last_update:.*/last_update:{round(time.time())}/\" config")

def _apply_update():
    time.sleep(0.3)
    #Run 'git pull' to merge changes into our local copy. 
    #Additional changes are fetched if necessary.
    #In the future, maybe we could use `git merge {remote}/{branch} {branch}`?
    pull = _run_git_command("git pull", exit=False)
    _print_git_output(pull['output'])
    if pull['returncode']:
        print(f"{Text.BOLD}Something went wrong while applying the update. Take a look at the above output for details.{Text.NORMAL}")
        sys.exit(124)
    print("Updating submodules...")
    #Attempt to update all submodules.
    submodule_update = common.run_command("git submodule update --remote")
    _print_git_output(submodule_update['output'])
    if submodule_update['returncode']:
        print(f"{Text.BOLD}Something went wrong while updating submodules. The above output may contain more details.{Text.NORMAL}")
        print("You may want to run `cd db_utils; git pull; cd ../web/deps/vif; git pull; cd ../../..;`.")
        print("This will attempt to update each submodule independently.")
        print(f"{Text.BOLD}Submodules contain important code. Maximilian may not start if you don't update submodules.{Text.NORMAL}\n")
        time.sleep(1)
    print(f"{Text.BOLD}Update applied.{Text.NORMAL} \nView the changes at 'https://github.com/TK421bsod/maximilian/compare/{initial}...{branch}'.")
    time.sleep(1)
    #Exit if we had changes to any files already loaded.
    if list_in_str(['main.py', 'common.py', 'db.py', 'settings.py', 'base.py', 'startup.py', 'core.py'], "\n".join(pull['output'])):
        print(f"\n{Text.BOLD}This update changed some important files that can't be reloaded while Maximilian is running.\nPlease restart Maximilian to finish the update.{Text.NORMAL}")
        sys.exit(111)

def _update():
    """
    Checks for updates if needed. Applies update if one is found.
    """
    #loggers aren't used here as we want all this to show regardless of logging level
    print("initializing updater\n")
    #Load configuration data. Used for last update timestamp and the automatic updates setting.
    config = common.load_config()
    #Get our current HEAD commit.
    initial = common.get_latest_commit()
    #Attempt to get our current remote.
    remote = _run_git_command("git remote")['output'][0]
    #Attempt to get our current branch.
    branch = _run_git_command("git branch --show-current")['output'][0]
    time.sleep(0.5)
    #Pause between each step to give the user some time to read.
    _show_branch_advice(branch)
    time.sleep(2)
    _process_last_update_timestamp(config)
    time.sleep(2)
    _fetch_changes_from_remote(remote)
    #Get our new HEAD commit.
    after = _run_git_command(f"git rev-parse --short {remote}/{branch}")['output'][0]
    #HEAD commit different after the fetch?
    #then there's an update waiting to be merged!
    if initial != after:
        #Ask for confirmation and provide a link to review changes.
        resp = input(f"\nUpdate available. \nTake a moment to review the changes at 'https://github.com/TK421bsod/maximilian/compare/{initial}...{branch}'.\nWould you like to apply the update? Y/N\n").lower().strip()
        if resp == "y":
            print("\nApplying update...")
            _apply_update()
        else:
            print("\nNot applying the update.")
    else:
        print("No updates available.")
    time.sleep(1)

def update():
    """Checks for updates if needed. Applies updates if found.
    
    Wraps `updater._update`
    """
    try:
        _update()
    except CleanExit:
        pass

if __name__ == "__main__":
    print("It looks like you're trying to run the updater directly.")
    print("Use 'python3 main.py --update'.")

