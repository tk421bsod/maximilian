import getpass
import os

from setup.state import SetupState

def enter_install(handler):
    """Set SetupState.install_in_progress to 'handler'"""
    SetupState().install_in_progress = handler

def exit_install():
    """Clear SetupState.install_in_progress"""
    SetupState().install_in_progress = None

def _token_sanity_check(token):
    if len(token.split('.')) == 3: #Token should be in 3 segments delimited by '.'.
        return True
    return False

def get_token():
    from_env = os.getenv("MAXIMILIAN_TOKEN")
    if from_env:
        print("Thanks for providing the token via an environment variable.")
        if _token_sanity_check(from_env):
            return from_env
        print("The token you provided is not valid!\n")
    print("Enter a token. This allows Maximilian to log in to Discord.")
    print("Your input will be hidden to keep it secret.")
    print("(Unsure? Enter ? for help.)")
    while True:
        token = getpass.getpass("").strip()
        if token == "?":
            print("\nA token allows a bot to log in under a special account.")
            print("Need one? Open the Discord Developer Portal, create an application, go to the Bot tab, create a bot account, and copy the token.")
            print("Then paste it here.")
            print("When you're ready, enter your token below.")
            continue
        elif token == "":
            print("\nYou must enter a token to continue.")
            continue
        if _token_sanity_check(token):
            print("\nToken set.")
            break
        print("You entered an invalid token. Please try again.")
    return token

def get_database_password():
    from_env = os.getenv("MAXIMILIAN_DBP")
    if from_env:
        print("Thanks for providing the database password via an environment variable.")
        return from_env
    print("\nNext, enter a database password. This will be what Maximilian uses to access the database.")
    if SetupState().remote:
        print("Since the database is set up on a different computer, enter the password for that database.")
    print("Your input will be hidden to keep it secret.")
    while True:
        dbp = getpass.getpass("").strip()
        if dbp == "":
            print("\nYou must enter a password to continue.")
            continue
        print("\nGreat. Enter the same password again to confirm it.")
        dbp_confirmation = getpass.getpass("").strip()
        if dbp_confirmation != dbp:
            print("\nThe two passwords didn't match. You'll need to enter the password again.")
            continue
        print("Database password set.")
        break
    return dbp

@staticmethod
def get_owner_id():
    print("Enter the ID for your Discord account. This enables error reporting and gives you more control over Maximilian.")
    print("You *can* leave this blank, but your experience will be better if you include it.")
    print("(Unsure of how to get your ID or just want some more info? Enter ?.)")
    while True:
        owner_id = input().strip()
        if owner_id == "?":
            print("\nA user ID is a unique number that identifies a specific Discord account.")
            print("Maximilian uses this ID to determine where to send error messages.")
            print("This ID is also used to enable some more advanced commands.")
            print("These commands allow you to perform maintenance and debugging without access to the command line.")
            print("This also allows you to use the Jishaku module. See HOSTING.md for more details on that.")
            print("You can get your ID by right-clicking on yourself in the member list, then clicking 'Copy User ID' in the context menu.")
            print("If you don't see this option, enable 'Developer Mode' in Settings -> Advanced, and try again.")
            print("When you're ready, enter your ID below.")
            continue
        elif owner_id == "":
            print("\nOwner ID not set.\nError reporting, 'utils' commands, and Jishaku have been disabled.") 
            print("")
            break
        if not owner_id.isnumeric():
            print("The ID must be a number.")
            continue
        print("\nOwner ID set.")
        break
    return owner_id
