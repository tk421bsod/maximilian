def _empty_callback():
    return None

class MenuWithCallbacks:
    """
    Base class for a menu that maps callbacks to options.
    Menus subclassing this must initialize this, then call handle_callback for callbacks to run.
    """

    def _has_callback(self, option):
        """Check if a menu option has a callback attached to it."""
        if type(option) != dict:
            return False
        return True

    def _handle_callback(self, option):
        """Handle a callback mapped to a menu option.

        Returns the return value of the callback if available, otherwise returns None.
        """
        #Return None if there isn't an attached callback.
        if not self._has_callback(option):
            return None
        #Get the attached callback.
        callback = list(option.values())[0]
        if not callable(callback):
            print("Menu callbacks must be callable! Returning None.", fg=TEXT_STYLES["red"])
            return None
        #Run the callback and return its return value.
        ret = callback()
        return ret

class IntMenu(MenuWithCallbacks):
    """
    A menu for choosing from a list of options.
    Provide a list of options and a prompt for input at initialization then call handle_menu.
    handle_menu will return a dict with the format {"choice":<index of chosen option>, "return":<callback return, None if no callback>}
    Can be reused if you desire.

    Options must be provided as a list. They can also be a list of dicts if you wish to execute a callback when a menu option is chosen.
    Callbacks need to be callable.
    You can also mix the two types within the list if some options don't need callbacks.
    For example, ["Option 1", {"Option 2":some_callback}]
    """

    __slots__ = ("options", "prompt", "allow_all")

    def __init__(self, options, prompt, allow_all=False):
        """Initialize an IntMenu.
        You must call handle_menu for the menu to be shown.
        `allow_all` controls whether to allow an `all` option separate from the normal options.
        When this is enabled, a response of `all` returns `-1` from `handle_menu`.

        See class documentation for the required format for `options`.
        """
        self.options = options
        self.prompt = prompt
        self.allow_all = allow_all
        super().__init__()

    def _handle_input(self):
        ret = input().strip().lower()
        print("")
        if self.allow_all and ret == "all":
            return -1
        try:
            ret = int(ret)
            if ret < 1 or ret > len(self.options):
                print(f"Enter a number between 1 and {len(self.options)}.\n ")
                return -2
            return ret-1
        except ValueError:
            print("Enter a number.\n")
        return -2
    
    def handle_menu(self):
        if self.prompt:
            self.prompt = "\n" + self.prompt
        print(self.prompt)
        print("---------------")
        for index, option in enumerate(self.options):
            if self._has_callback(option):
                print(f"{index+1}) {list(option.keys())[0]}")
            else:
                print(f"{index+1}) {option}")
        print("---------------")
        if len(self.options) == 1:
            print("Automatically selecting the only option available.")
            ret = self._handle_callback(self.options[0])
            return {"choice":0, "return":ret}
        while True:
            index = self._handle_input()
            if index != -2:
                ret = self._handle_callback(self.options[index])
                return {"choice":index, "return":ret}

class BooleanMenu(IntMenu):
    """A menu for choosing between 'Yes' and 'No'."""

    #Construct an IntMenu with only two options
    def __init__(self, prompt, YES_CALLBACK=_empty_callback, NO_CALLBACK=_empty_callback):
        options = [{"Yes":YES_CALLBACK}, {"No":NO_CALLBACK}]
        super().__init__(options, prompt, False)

    def handle_menu(self):
        """Display and handles input for the BooleanMenu. Returns the answer provided."""
        ret = super().handle_menu()
        #handle_menu returns the index of the chosen item.
        #Yes returns 0, No returns 1.
        #Converting to a boolean, then getting its inverse, converts the answer to its boolean counterpart.
        ret["choice"] = not ret["choice"]
        return ret
