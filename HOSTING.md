# hosting this yourself
Want to host your own instance of Maximilian?
You can set one up in just a few minutes.

First, ensure your system meets these requirements:
- at least 2gb of RAM
- 2gb free hard drive space (10gb for music)
- Working Internet connection (around 10mbps download for music)
- Any version of Linux that supports Python 3.8+ (recommended: latest Ubuntu LTS version)
- WSL (if on Windows)

Start by downloading the source code in this repository.  I recommend cloning the repository using `git clone https://github.com/tk421bsod/maximilian`.
Then, run setup.sh and follow the prompts it gives you.
It'll install almost everything Maximilian needs (python, mariadb, pip, python packages, etc) and set them up.

Now you're ready to run Maximilian. Just run `python3 main.py`.
If you see an "Invalid syntax" error when starting Maximilian, make sure you're running it on Python 3.8 or above. 
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

Run main.py with `--help` to view more information on valid arguments.

# can I run Maximilian on Windows?
At the moment, no.
I'm considering it and may make it an option in 1.1.
