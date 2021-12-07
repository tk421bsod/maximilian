# hosting this yourself
a quick note: some of these lines are quite long.
if you're reading this in your IDE / text editor of choice, i recommend you turn on word wrap. in visual studio code, it's in File > Preferences > Settings > Text Editor > Word Wrap.

another thing: this only works on Linux for now

this may or may not display correctly on github.

Start by downloading the source code in this repository.  I recommend cloning the repository using `git clone https://github.com/tk421bsod/maximilian`.
Then, run setup.sh.
Run it with `remote` if you plan on running Maximilian on a different computer, e.g `bash setup.sh remote`, or `nodb` if you already have the database set up, e.g `bash setup.sh nodb`.
Follow the prompts setup.sh gives you.
It'll install almost everything Maximilian needs (python, mariadb, pip, python packages, etc) and set them up.

Now you're ready to run Maximilian. Just run `python3 main.py`.
If you see an "Invalid syntax" error when starting Maximilian, make sure you're running it on Python3.7 or above. 
On some older versions of Linux you might need to compile a newer version of Python yourself.

If you get some weird output and can't see it anymore, check the log file. It's located in `./logs/maximilian-<date>.log`.

# additional command line arguments 

To enable eval commands through an extension called `jishaku` (https://github.com/Gorialis/jishaku), run `main.py` with `--enablejsk`.

If you're hosting the database on another computer, you'll need to run `main.py` with `--ip <database_ip>`, replacing `<database_ip>` with the IP address of your database.

To skip loading a specific extension, use the `--noload` argument. Follow it up with the names of the extensions you don't want loaded. for example, `python3 main.py --noload cogs.userinfo` will make Maximilian not load the userinfo extension.

You can specify a logging level (which filters the information Maximilian outputs) through command line arguments after `main.py`; the logging levels are -q (disables logging), -e (errors only), -w (warnings + errors), -i (warnings + errors + info, recommended), -v (all log messages are outputted, this is not recommended because of the console spam).
It defaults to -w if nothing's specified.
For example, `python3 main.py -i` will start Maximilian with the INFO logging level.
I recommend using `-i` as it outputs some information you wouldn't see at other logging levels.

# known issues
- Maximilian requires multiple custom emoji.
I'm going to introduce the ability to change or disable these soontm.

- None of Maximilian's `utils` commands work.
This is because the owner id is set as mine. I'll make this an option soon.
