import logging
import os
import subprocess
import time

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
    Python implementation of the setup.sh updater with some slight changes.
    '''
    #loggers aren't used here as we want all this to show regardless of logging level
    print("initializing updater\n")
    initial = common.get_latest_commit()
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
    print("Checking for updates...")
    try:
        subprocess.run(['git', 'fetch', remote], check=True)
    except subprocess.CalledProcessError:
        print("Something went wrong while checking for updates.")
        return
    after = common.run_command(['git', 'rev-parse', '--short', f'{remote}/{branch}'])['output']
    if initial != after:
        resp = input("Update available. Would you like to apply it? Y/N\n").lower().strip()
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
