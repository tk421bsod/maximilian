import logging
import os
import subprocess
import time
import datetime
import sys

import common
from common import Text

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

def print_git_output(output):
    print("\n-----")
    print("Git output:")
    print("\n".join(output))
    print("-----\n")

def update():
    '''
    Checks for updates if needed. Applies update if one is found.
    '''
    #loggers aren't used here as we want all this to show regardless of logging level
    print("initializing updater\n")
    #step 1: get info & display current branch
    initial = common.get_latest_commit()
    #get current remote
    remote = common.run_command("git remote")['output'][0]
    ret = common.run_command("git branch --show-current")
    #get current branch
    branch = ret['output'][0]
    time.sleep(0.5)
    if ret['returncode'] == 128:    
        print(f"{Text.BOLD}Maximilian is running under a different user than the one that owns its root directory!{Text.NORMAL}")
        print("Git really doesn't like this.")
        print("You may have run this as root or cloned the repository as root.")
        print("Using Maximilian through a process manager? Run with --no-update.")
        print("Something like `git config --system --add safe.directory \"/path/to/maximilian\"` should fix this.")
        raise KeyboardInterrupt
    if branch == "":
        print("It doesn't look like you're on a branch.")
        print("You may be in a 'detached HEAD' state.")
        print("Consider checking out either the 'release' or 'development' branch.")
        print("See https://stackoverflow.com/questions/10228760 for more information.")
        raise KeyboardInterrupt
    print(f"{Text.BOLD}You're currently on the '{branch}' branch.")
    if branch == 'development':
        print(f"Updates on this branch may break things.{Text.NORMAL}")
        print("You can switch back to the 'release' branch at any time using 'git checkout release'.")
        print("If an update breaks something, reset to the previous commit using 'git reset HEAD~1'.")
        print("If you decide to revert, you may need to go back to the latest commit with `git reset --hard HEAD` before you can receive further updates.")
    elif branch == 'release':
        print(f"Updates on this branch are infrequent but stable.{Text.NORMAL}")
        print("You can switch to other branches at any time using 'git checkout <branch>'.")
        print("Use 'git branch' to view a list of branches.")
    else:
        print(f"I can't tell what kind of branch this is.{Text.NORMAL}")
        print("You're either on a release snapshot branch for version 2.0 onward or your own custom branch.")
        print("Old releases don't receive support and may stop working without notice.")
        print("For the latest changes, consider switching to the `release` branch using `git checkout release`.")
    time.sleep(1)
    try:
        config = common.load_config()
        last_update = config['last_update']
        if not last_update:
            print("Updater was interrupted or last update failed, checking for updates now")
        elif "--force-update" in sys.argv or "--update" in sys.argv:
            print("main.py was invoked with --force-update. Checking for updates now.")
        else:
            #Convert our last update timestamp from a Unix timestamp to datetime 
            last = datetime.datetime.fromtimestamp(int(last_update))
            #                                      "was at HOUR:MINUTE <AM/PM> on MONTH DAY, YEAR."
            print(f"\n{Text.BOLD}Last check for updates was at {last.strftime('%-I:%M %p on %B %d, %Y.')}{Text.NORMAL}")
            elapsed = (datetime.datetime.now()-last).days
            try:
                automatic_updates = bool(config['automatic_updates'])
            except KeyError:
                automatic_updates = True
            if not automatic_updates:
                print("Automatic updates aren't enabled. Would you like to attempt an update? Y/N\n")
                if input().strip().lower() == "y":
                    print("Ok, attempting an update...")
                else:
                    print("Not attempting an update.")
                    return
            elif elapsed > 14:
                print("It's been more than 14 days since the last update. Updating now.")
            else:
                print(f"It's been {elapsed} days since the last update. To force an update, run main.py with --force-update.")
                time.sleep(1)
                return
    except KeyError:
        #append timestamp to config if it doesn't exist
        subprocess.run("echo \"last_update:0\" >> config", shell=True)
        print("Couldn't determine the time since last update. Updating now.")
    time.sleep(1)
    #step 2.5: if a condition above was met, reset last update timestamp
    subprocess.run("sed -i \"s/last_update:.*/last_update:/\" config", shell=True)
    #step 3: fetch changes from remote, don't merge until user confirms though
    print("\n")
    try:
        subprocess.run(['git', 'fetch', remote], check=True)
    except subprocess.CalledProcessError:
        print("Update check failed. See the above output for details.")
        return
    after = common.run_command(f"git rev-parse --short {remote}/{branch}")['output'][0]
    #now that we can check if an update exists, set last update timestamp
    subprocess.run(f"sed -i \"s/last_update:.*/last_update:{round(time.time())}/\" config", shell=True)
    if initial != after:
        #HEAD commit different after the fetch?
        #then an update was applied!
        #step 4: ask for confirmation, then apply changes if yes
        resp = input(f"\nUpdate available. \nTake a moment to review the changes at 'https://github.com/TK421bsod/maximilian/compare/{initial}...{branch}'.\nWould you like to apply the update? Y/N\n").lower().strip()
        if resp == "y":
            print("\nApplying update...")
            time.sleep(0.3)
            pull = common.run_command("git pull")
            print_git_output(pull['output'])
            if pull['returncode']:
                print("Something went wrong while applying the update. Take a look at the above output for details.")
                sys.exit(124)
            print("Updating submodules...")
            submodule_update = common.run_command("git submodule update --remote")
            print_git_output(submodule_update['output'])
            if submodule_update['returncode']:
                print("Something went wrong while updating submodules. The above output may contain more details.")
                print("You may want to go into the directory for each submodule and pull changes from the remote.")
            print(f"Update applied. \nView the changes at 'https://github.com/TK421bsod/maximilian/compare/{initial}...{branch}'.")
            time.sleep(1)
            if list_in_str(['main.py', 'common.py', 'db.py', 'settings.py', 'base.py', 'startup.py', 'core.py'], "\n".join(pull['output'])):
                print("\nThis update changed some important files that can't be reloaded while Maximilian is running.\nPlease restart Maximilian to finish the update process.")
                sys.exit(111)
        else:
            print("\nNot applying the update.")
    else:
        print("No updates available.")
    time.sleep(1)

if __name__ == "__main__":
    print("It looks like you're trying to run the updater directly.")
    print("Use 'python3 main.py --update'.")

