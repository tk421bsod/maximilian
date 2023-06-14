# hosting this yourself
Want to host your own instance of Maximilian?
You can set one up in just a few minutes.

First, ensure your system meets these requirements:
- at least 2gb of RAM
- 2gb free hard drive space (5gb for music support)
- Working Internet connection (around 10mbps download for music)
- Any version of Linux that supports Python 3.8+ (recommended: latest Ubuntu LTS version)
- WSL (if on Windows)

Start by downloading the source code in this repository.  I recommend cloning the repository using `git clone https://github.com/tk421bsod/maximilian`.

Then, run the setup script (`bash setup.sh`) and follow the prompts it gives you.
It'll install almost everything Maximilian needs (python, mariadb, pip, python packages, etc) and set them up.

Now you're ready to run Maximilian. Just run `python3 main.py`.
If you see an "Invalid syntax" error when starting Maximilian, make sure you're running it on Python 3.8 or above. 
On some older versions of Linux you might need to compile a newer version of Python yourself.

If you get some weird output and can't see it anymore, check the log file. It's located in `./logs/maximilian-<date>.log`.

# optional packages
Want to get prettier output in the console?
Run `pip3 install -r requirements-extra.txt`.

# additional command line arguments 

To enable special debugging commands through an extension called `jishaku` (https://github.com/Gorialis/jishaku), run `main.py` with `--enablejsk`.
While Jishaku is an invaluable tool for debugging and development, it can be very dangerous. If your Discord account is compromised, an attacker can have almost complete access to your computer through Jishaku.
The first time you run Maximilian with Jishaku enabled and a logging level at or below `-w`, startup will be temporarily paused and you'll see a warning with this same information.
Want to see the warning again later? Remove the `jsk_used` line from `config`.
I recommend enabling two factor authentication for your Discord account before using Jishaku.

If you're hosting the database on another computer, you'll need to run `main.py` with `--ip <database_ip>`, replacing `<database_ip>` with the IP address of your database.

To skip loading a specific extension, use the `--no-load` argument. Follow it up with the names of the extensions you don't want loaded. for example, `python3 main.py --no-load cogs.userinfo` will make Maximilian not load the userinfo extension.

You can specify a logging level (which filters the information Maximilian outputs) through command line arguments after `main.py`; the logging levels are -q (disables logging), -e (errors only), -w (warnings + errors, default), -i (warnings + errors + info, recommended), -v (warnings + errors + info + debugging info).
It defaults to -w if nothing's specified.
For example, `python3 main.py -i` will start Maximilian with the INFO logging level.
I recommend using `-i` as it outputs some information you wouldn't see at other logging levels.

Using `-v`, `--verbose`, or `--debug` will result in larger log file sizes and much more output to the console, especially on the first run.
You may also see a small decrease in performance.
If you choose to use it, you'll see a small warning on startup.

To bypass the updater on startup, run main.py with `--no-update`.
This can save some startup time if you're restarting Maximilian frequently.

Want to make Maximilian check for updates each time it starts, regardless of the time since the last update?
Run main.py with `--force-update`.

Want to attempt an update and exit? Use `--update`. This implicitly enables `--force-update`.

Run main.py with `--help` to view more information on valid arguments.
Anything not documented either here or in `--help` is not stable and can change at any time.

# can I run Maximilian on Windows?
At the moment, no.
I'm considering it and may make it an option in the future.

# i wanna contribute, wtf is up with all these files?
Maximilian is broken up into a number of different Python modules to make development and maintenance easier.
Each module handles some specific functionality.

Any modules in the root directory are what the bot calls 'required' modules. They provide a set of APIs for other modules to call into.

Here's what each one does:
* main.py - handles some early initialization, launches Maximilian
* settings.py - an extremely simple API for adding setting toggles to a module
* helpcommand.py - a custom help command
* errorhandling.py - command error handling utilities
* core.py - various utility commands, hooks for on_message, guild_join, and guild_remove, a couple helper methods used in async contexts
* db.py - database interface
* common.py - some helper methods that are used outside of async contexts
* updater.py - handles updating Maximilian
* startup.py - handles a couple tasks only performed during startup
* base.py - handles most tasks besides early initialization

Deleting or breaking one of the above modules will prevent Maximilian from functioning as all of them are interdependent to some degree.
Broke something and want to reset to a working version? Run `git restore <file>`.

There are also a couple different directories:
* cogs - stores 'optional' modules that contain commands
* logs - stores log files, labeled with date started
* languages - stores files used by the translation subsystem, required for Maximilian to start
* songcache - cache for files generated by the music module
* web - assorted website files

Anything in the 'cogs' directory is what the bot calls 'optional' modules.
As the name implies, you can delete or break these without much effect besides a loss of their functionality.
These modules make up the majority of Maximilian's features.

They are:
* config.py - calls into settings.py to allow for changing settings
* music.py - some music features
* reactionroles.py - gives users roles on reactions
* misc.py - a few fun commands that don't really fit into a category
* prefixes.py - provides per-server customizable prefixes
* reminders.py - reminders and todo lists
* responses.py - 'custom commands': say something, get a response
* userinfo.py - provides information about users

The rest of the files in the root directory are either utilities or data.
Some are automatically generated by various tools.

These files are not automatically generated:
* requirements.txt - a list of dependencies. `pip` uses this to know what packages to install.
* requirements-extra.txt - some extra dependencies (not required, but definitely nice to have!)
* HOSTING.md - some info on hosting / contributing and also the file you're currently reading ;)
* README.md - one line description of the bot, branch info, 1.0 patch notes
* setup.sh - handles setting up Maximilian and doing some common tasks

And now for the automatically generated files:

`config` is generated by setup.sh and it contains configuration data for Maximilian. 
This data includes:
* The token to use
* Database password
* The owner's account ID
* Main color (theme_color)
* etc.
Editing this file or quitting setup.sh before it is finished can break Maximilian. 
If Maximilian says something is missing, try running setup.sh again, filling in the necessary details when prompted.
Do not share this file with anyone. It could give people access to your bot's account.

`backup.sql` is a database backup created through the command `bash setup.sh backup`.
`setup.sh` does this through the `mysqldump` utility.
As with `config`, do not share this file with anyone. It contains all data stored by Maximilian at the time the backup was made.
This includes, but is not limited to, user IDs, prefixes, todo lists, custom commands, and reminders.
You can restore the backup by running `bash setup.sh restore`.

# troubleshooting
As much as I try to make Maximilian easy to install and use, you may run into some issues.
Below are some common errors and steps to resolve them.

`Maximilian cannot start because an external dependency failed to load.`
A dependency installed separate from Maximilian didn't load.
Running `pip3 install -U -r requirements.txt` should fix this.

`Maximilian cannot start because an internal module failed to load.`
One of Maximilian's core files didn't load correctly.
This usually is caused by invalid syntax or the file simply not existing.
Just updated after modifying some files? Git may have broken something in an attempt to merge the two versions. Merge conflicts also tend to break stuff.
Modified some files? You may have broken something.
If there are no merge conflicts, just run `git restore <file>`.
You can find the file name and some extra error info in the last line of output from Maximilian.
If you introduced merge conflicts, you probably know how to fix them already.
Updated to a newer version of Maximilian and haven't modified anything?
Let `tk___421` know. They probably messed something up.

`It looks like your Python installation is missing some features.`
Try updating your Python. If you built Python from source, you may need to install additional dependencies and recompile.
