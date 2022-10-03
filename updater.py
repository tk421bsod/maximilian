import logging
import os
import subprocess
import time
import datetime
import sys

import common

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

def update():
    '''
    Checks for updates if needed. Applies update if one is found.
    '''
    #loggers aren't used here as we want all this to show regardless of logging level
    print("initializing updater\n")
    #step 1: get info & display current branch
    initial = common.get_latest_commit()[0]
    #get current remote
    remote = common.run_command(['git', 'remote'])['output'][0]
    #get current branch
    branch = common.run_command(['git', 'branch', '--show-current'])['output'][0]
    time.sleep(0.5)
    print(f"You're currently on the '{branch}' branch.")
    if branch != 'release':
        print("Updates on this branch may be unstable.")
        print("You can switch back to the 'release' branch at any time using 'git checkout release'.")
        print("If an update breaks something, reset to the previous commit using 'git reset HEAD~1'.")
    else:
        print("You can switch to other branches at any time using 'git checkout <branch>'.")
        print("Use 'git branch' to view a list of branches.")
    time.sleep(0.5)
    try:
        config = common.load_config()
        last_update = common.load_config()['last_update']
        if not last_update:
            print("Updater was interrupted or last update failed, checking for updates now")
        elif "--force-update" in sys.argv:
            print("main.py was invoked with --force-update. Checking for updates now.")
        else:
            last = datetime.datetime.fromtimestamp(int(last_update))
            print(f"\nLast check for updates was {last.strftime('at %-I:%M %p on %B %d, %Y.')}")
            elapsed = (datetime.datetime.now()-last).days
            if not bool(config['automatic_updates']):
                print("Automatic updates aren't enabled. Would you like to attempt an update? Y/N\n")
                if input().strip().lower() == "y":
                    print("Ok, attempting an update...")
            elif elapsed > 14:
                print("It's been more than 14 days since the last update. Updating now.")
            else:
                print(f"It's been {elapsed} days since the last update. To force an update, run main.py with --force-update.")
                return
    except KeyError:
        pass #updater hasn't checked for updates yet
    time.sleep(1)
    common.run_command(["sed", "-i", "\"s/last_update:.*/last_update:0/\"", "config"])
    #step 3: if one of the three conditions above was met, fetch changes
    try:
        subprocess.run(['git', 'fetch', remote], check=True)
    except subprocess.CalledProcessError:
        print("Update check failed. See the above output for details.")
        return
    after = common.run_command(['git', 'rev-parse', '--short', f'{remote}/{branch}'])['output'][0]
    print(initial)
    print(after)
    subprocess.run(f"sed -i \"s/last_update:.*/last_update:{round(time.time())}/\" config", shell=True)
    if initial != after:
        #HEAD commit changed during the fetch?
        #then an update was applied!
        #step 4: ask for confirmation, then apply changes if yes
        resp = input(f"Update available. \nTake a moment to review the changes at 'https://github.com/TK421bsod/maximilian/compare/{initial}...{branch}'.\nWould you like to apply the update? Y/N\n").lower().strip()
        if resp == "y":
            print("\nApplying update...")
            pull = common.run_command(['git', 'pull'])
            output = "\n".join(pull['output'])
            print("\nGit output:")
            print(output)
            if pull['returncode']:
                print("Something went wrong while applying the update. Take a look at the above output for details.")
                os._exit(124)
            print(f"Update applied. \nView the changes at 'https://github.com/TK421bsod/maximilian/compare/{initial}...{branch}'.")
            if list_in_str(['main.py', 'common.py', 'db.py', 'settings.py'], output):
                print("This update changed some important files. Run main.py again.")
                os._exit(111)
        else:
            print("\nNot applying the update.")
    else:
        print("No updates available.")
    time.sleep(1)

if __name__ == "__main__":
    print("It looks like you're trying to run the updater directly.")
    print("Use 'python3 main.py --update'.")

