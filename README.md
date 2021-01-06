# maximilian

An easy to use Discord bot with a web interface. 

With this bot, you can create reaction roles (used for assigning permissions to users if they agree to a server's rules, for example), custom commands (text that Maximilian sends when you type its prefix + the text that triggers the command, useful for commonly used bits of text that would take a while to type), generate zalgo text (in the future you'll be allowed to disable commands like this), etc.

#Self Hosting

I discourage hosting this bot yourself, but you can if you want to.
##Step 1: Download required files and install dependencies 
First, clone or download the source. I recommend cloning the source, as you can recieve regular updates by running `git pull`. The only files required are main.py (runs bot, handles errors), common.py (methods for interacting with the database), reactionroles.py (handles reaction roles), responses.py (handles custom commands), userinfo.py (handles user info), misc.py (miscellaneous commands), and prefixes.py (handles server specific prefixes).
Next, make sure you have Python 3.5 - 3.8 installed, then install Maximilian's dependencies through pip, using `pip install discord.py pymysql gitpython zalgo_text`.

##Step 2: Set up a bot and test it.
Then, set up a bot in the Discord Developer Portal, enable the members and presences intents, and put the token (not the client secret) into a file called `token.txt` in the same directory as the other files.
To start the bot, run main.py. You'll see an error message saying that it couldn't connect to the database, and that most features won't work. By 'most features', I mean server-specific prefixes, custom commands, and reaction roles. (also the deleteall command won't work as there's no data to delete)

##Step 3 (optional, but most features won't work until you do this): Setting up the database
To fix the issue, you'll need to set up an instance of MariaDB with a user called 'maximilianbot'. Install the database as described [here](https://mariadb.com/kb/en/getting-installing-and-upgrading-mariadb/), then go to the mariadb shell by typing `mariadb`, then create a user named 'maximilianbot' with the statement `CREATE USER 'maximilianbot'@'localhost' IDENTIFIED BY 'password';`, replacing `localhost` with the IP of the computer you want to connect from if you're not running the database on the computer you're hosting the bot on (keep it as `localhost` otherwise), and replacing `password` with the password you want Maximilian to connect to the database with. 
Next, create a file called `dbp.txt` in the same directory as main.py and common.py, then put the database password (the password you set up for maximilianbot in the previous step) in the file.
You'll need to create a few tables and a database for the bot to function. 
I've included a script you can run to create those tables for you. If you go to the directory that main.py is in, you should see a file called `maximilian-db-setup.sql`. Go back to your mariadb shell, and type `CREATE DATABASE maximilian;`. This will create a database named maximilian. 
To create all of the necessary tables, exit the shell by typing `exit`, then change the directory you're in to the directory that you put the source code in using `cd <directory>` (you can use `cd ..` to go up a directory if you go into the wrong one, and `cd ~` should bring you to your user directory).
Then, run `mariadb -u maximilianbot -p maximilian < maximilian-db-setup.sql`, and enter your password. This will create a few tables that Maximilian uses. 
Now, try running main.py again, with `python3 main.py --ip <ip>`, replacing `<ip>` with the ip you chose for maximilianbot when you created it. If you chose localhost, omit the --ip argument (in that case, the command should look like `python3 main.py`). If the command fails, try using `python` instead of `python3`.
