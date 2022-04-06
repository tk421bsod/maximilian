#!/bin/bash

#fancy text
#these might not display correctly on some terminals 
bold=$(tput bold)
normal=$(tput sgr0)

function ctrl-c () {
    echo ""
    echo "Exiting."
    rm config > /dev/null 2>&1
    exit 39
    
}

ip="%"

echo "Checking for updates..."
initial="$(git rev-parse --short HEAD)"
git pull > /dev/null 2>&1
ret=$?
#try https if the initial pull failed (e.g ssh blocked)
if [ $ret != 0 ]
then
    git pull https://github.com/tk421bsod/maximilian development > /dev/null 2>&1
    ret=$?
fi
after="$(git rev-parse --short HEAD)"
if [ $ret != 0 ]
then
    echo ""
    echo "Something went wrong while checking for updates. If you've made local changes, use 'git status' to view what files need to be committed. If you haven't done anything, check your Internet connection."
    sleep 1
fi

#initial commit different than commit after pulling?
#then an update was applied!
#restart setup as it may have been affected
if [ "$initial" != "$after" ];
then
    echo ""
    echo "Update applied. Restarting setup..."
    sleep 1
    bash setup.sh "$1"
    exit
elif [ "$1" == "update" ];
then
    echo ""
    echo "No updates available. Exiting."
    exit
else
    echo ""
    echo "No updates available. Starting setup."
    sleep 1
    echo ""
fi

if [ "$1" == "update" ];
then
    exit
fi

if [ "$1" == "nodb" ];
then
    nodb='true'
else
    nodb='false'
fi

sleep 0.5

if [ "$1" == "help" ];
then
    echo "Usage: bash setup.sh [OPTION]"
    echo ""
    echo "setup.sh handles setting up and repairing different Maximilian components."
    echo "You can perform specific tasks through the use of the following options."
    echo ""
    echo "Options:"
    echo "${bold}start${normal} - Attempts to start the database through 'sudo service mysql start'."
    echo "${bold}backup${normal} - Starts the database and backs up its data to './backup.sql'."
    echo "${bold}restore${normal} - Restores the database from a previously created backup. The backup must be named 'backup.sql'."
    echo "${bold}fix${normal} - Attempts to fix the database by backing up the data, reinstalling the database, and restoring from the backup."
    echo "${bold}reset${normal} - Resets the database. This deletes all data."
    echo "${bold}delete-old${normal} - Deletes any old configuration files."
    echo "${bold}nodb${normal} - Sets up Maximilian without the database. Only use this if you've already set up the database on a different computer."
    echo "None - Sets up Maximilian."
    exit
fi

if [ "$1" == "delete-old" ];
then
    if [ ! -f token.txt -a ! -f dbp.txt ];
    then
        echo "It doesn't look like you have any old configuration data."
        exit
    fi
    echo "Deleting old configuration files..."
    rm token.txt > /dev/null 2>&1
    rm dbp.txt > /dev/null 2>&1
    echo "Done."
    exit
fi

if [ "$1" == "start" ];
then
    echo "Trying to start the database..."
    sudo service mysql start
    if [ $? != 0 ];
    then
        echo "Couldn't start the database."
        exit
    fi
    echo "Started the database."
    exit
fi

if [ "$1" == "backup" -o "$2" == "backup" ];
then
    echo "Backing up the database..."
    sudo service mysql start
    sudo mysqldump --databases maximilian > backup.sql
    echo ""
    echo "Saved the backup to 'backup.sql'. Run 'bash setup.sh restore' to restore it."
    exit
fi

if [ "$1" == "restore" -o "$2" == "restore" ];
then
    if [ ! -f backup.sql ]
    then
        echo "Couldn't find a backup. Make sure it's named 'backup.sql'."
        exit
    fi
    echo "You've chosen to restore data from a backup. Before continuing, please read the following."
    echo "Continuing will overwrite all data in the database. Depending on when you made the backup, you might lose some data."
    echo "Do you want to continue? Y/N"
    read continue
    if [ ${continue^^} == "Y" ]
    then
        echo ""
        echo "Ok. Restoring from the backup..."
        sudo service mysql start
        sudo mysql -Be "drop database maximilian"
        sudo mysql -Be "create database maximilian;"
        sudo mysql maximilian < backup.sql
        if [ $? != 0 ]
        then
            echo "Something went wrong while restoring the backup. Tell tk421 about this."
            exit
        fi
        echo "Done restoring data."
        exit
    else
        echo "Exiting."
        exit
    fi
fi

if [ "$1" == "fix" -o "$2" == "fix" ];
then
    echo ""
    echo "You've chosen to automatically fix the database. Before continuing, read through the following."
    echo "This will attempt to fix problems with the database by backing up data, reinstalling the database, and restoring from the backup."
    echo "This may take a while. Make sure you have a stable Internet connection and at least 1gb of free space before continuing."
    echo "Do you want to continue? Y/N"
    read continue
    if [ ${continue^^} == "Y" ]
    then
        echo "Ok."
        echo "Backing up data..."
        sudo service mysql start
        sudo mysqldump --databases maximilian > backup.sql
        echo "Reinstalling the database... Step 1 of 3"
        sudo mysql -Be "drop user 'maximilianbot'@'$ip';" 
        sudo mysql -Be "drop database maximilian;"
        sudo apt -y remove mariadb-server > /dev/null 2>&1
        echo "Reinstalling the database... Step 2 of 3"
        sudo apt -y autoremove > /dev/null 2>&1
        echo "Reinstalling the database... Step 3 of 3"
        sudo apt -y install mariadb-server > /dev/null 2>&1
        echo "Restoring the backup..."
        sudo service mysql start
        sudo mysql -Be "create database maximilian;"
        sudo mysql maximilian < backup.sql
        if [ $? != 0 ]
        then
            echo "Something went wrong while restoring the backup. Tell tk421 about this."
            exit
        fi
        echo "Done. Run setup.sh again to set a password."
        exit
    else
        echo "Ok. Exiting."
        exit
    fi
fi

if [ "$1" == "reset" ];
then
    echo ""
    echo "You've chosen to ${bold}reset${normal} the database. Before continuing, please read through this thoroughly."
    echo "This will ${bold}irreversibly remove all data Maximilian has stored${normal} (reaction roles, song metadata, reminders, configuration data, custom commands, etc.) and ${bold}RENDER MAXIMILIAN INOPERABLE${normal} until you run setup.sh again."
    echo "Only continue if either you've already tried 'bash setup.sh fix' or you've been instructed to by tk421."
    echo "${bold}To continue, enter 'RESET!' exactly as shown. To exit, press Ctrl-C or Ctrl-Z now. Once you continue, THIS CANNOT BE REVERSED.${normal}"
    read reset
    if [ "$reset" == "RESET!" ]
    then
        echo ""
        echo "Ok. Resetting the database."
        sudo service mysql start
        sudo mysql -Be "drop database maximilian;"
        sudo mysql -Be "drop database maximilian_test;"
        sudo mysql -Be "drop user 'maximilianbot'@'$ip';"
        rm config
        echo ""
        echo "Reset the database. Run this again and follow the prompts to set it up."
        exit
    else
        echo "You need to enter 'RESET!' exactly as it's shown."
        exit
    fi
fi

if [ -f token.txt ];
then
    echo "It looks like you've been using an older version of setup.sh. The configuration data format has changed, so you'll need to re-enter the token and database password."
    echo "Quit setup now (using either Ctrl-C or Ctrl-Z) if you want to keep (or copy) the old data."
    echo "Maximilian will not work until this finishes."
    echo "Press Enter if you want to continue. THIS WILL DELETE THE OLD DATA."
    read -s
    nodb='true'
    echo ""
    echo "Ok, starting setup."
    sleep 1
    rm token.txt
    rm dbp.txt
    echo "Deleted old data."
    echo ""
fi

if [ -f config ];
then
    echo "It looks like you've already run setup.sh."
    echo "Do you want to run it again? yes/no"
    echo "Warning: This will delete Maximilian's configuration data, so you'll need to reenter the database password, token, and your user id. Don't do it unless you have all of those ready."
    echo "Quit setup now (using either Ctrl-C or Ctrl-Z) if you want to keep the old data."
    read run
    if [ ${run^^} == 'NO' ];
    then
        echo "Alright. Exiting."
        exit 1
    elif [ ${run^^} == 'YES' ];
    then
        echo "Ok, starting setup."
        sleep 1
        rm config
        echo "Deleted old data."
        echo ""
        nodb='true'
    else
        echo "You need to enter either 'yes' or 'no'."
        exit 1
    fi
fi

trap ctrl-c SIGINT

echo ""
echo "Creating configuration file."
echo "#Configuration data for Maximilian." > config
echo "#This file was automatically generated by setup.sh. Editing it may break stuff." >> config
echo "custom_emoji:0" >> config
echo ""

echo "${bold}----------------Maximilian Setup----------------${normal}"
echo "This script automates most parts of setting up Maximilian. You'll still need to do a few things, like getting the token and choosing a password for the database."
if [ "$1" == "remote" ];
then
    echo "${bold}You've chosen to configure the database for remote access.${normal} This will not set up Maximilian on this computer. To set up Maximilian on this computer, run this with `nodb`."
elif [ "$1" == "nodb" ];
then
    echo "${bold}You've chosen to not set up the database on this computer.${normal} If you've set up the database on a different computer, run main.py with '--ip <ip>', <ip> being the ip address of that other computer."
    echo "This will still set up Maximilian on this computer."
else 
    echo "${bold}You didn't pass any arguments, so the database will only be configured for local access.${normal} Maximilian will still be set up."
fi
echo "This script installs several packages so ${bold}you'll need a stable Internet connection${normal} and around 1 gigabyte of free space."
echo "You can press ${bold}Ctrl-C${normal} to quit at any time. ${bold}However, exiting before setup finishes will delete any saved configuration data.${normal}"
echo ""

sleep 1

if [ "$1" == "jmmith" ];
then
    echo ""
    echo "${bold}Take a moment to read through the above information. Setup will start in a few seconds.${normal}"
    sleep 5
else
    echo "${bold}Read the README.md (and HOSTING.md) for Maximilian if you haven't already, because a README isn't any good if you don't read it.${normal}"
    echo ""
    read -p "Have you read the README? Y/N  " readme
    if [ ${readme^^} == 'N' ];
    then
        echo "Go read the README!"
        exit 1
    elif [ ${readme^^} == 'Y' ];
    then
        echo "Great. Continuing with setup in a few seconds..."
        sleep 5
    else
        echo "what?"
        exit 1
    fi
fi
echo ""
grep -qs token ./config
if [ $? != 0 ];
then
    echo "Enter the token you want Maximiian to use. If you don't know what this is, create an application in Discord's Developer Portal, create a bot account for that application, and copy the account's token. Then paste it here."
    echo "Your input will be hidden to keep the token secret."
    read -s token
    if [ "$token" == "" -o "$token" == " " ];
    then
        echo "You have to actually enter a token."
        exit 13
    fi
    echo "token:$token" >> config
    echo "Alright, saved the token to 'config'. If the token isn't valid, either edit the file and add the correct token or delete the file and run this again."
    echo ""
fi
echo "Enter the password you want to use for the database."
if [ $nodb == 'false' ];
then
    echo "The database and maximilian will be configured to use this password."
else
    echo "Make sure it's the password 'maximilianbot' logs in with."
fi
echo "Your input will be hidden to keep the password secret."
read -s password
if [ "$password" == "" -o "$password" == " " ];
then
    echo "The password can't be blank!"
    echo "Run this again and enter an actual password."
    exit 12
fi
echo ""
echo "Type the same password again."
read -s passwordconf
if [ "$password" != "$passwordconf" ];
then
    echo "The passwords don't match! Run this again."
    echo "Remember that passwords are case-sensitive."
    exit 11
fi  
echo ""
echo "Ok, the password has been set. "
if [ ! $ip == '%' ];
then
    echo "It'll be saved to 'config' after setting up the database."
fi
echo "One more thing before setup starts..."
echo "Enter your Discord account's ID. This lets you use certain features like the 'utils' commands and Jishaku. It also makes Maximilian DM you with any errors it experiences."
read owner_id
echo "owner_id:$owner_id" >> config
echo ""
echo "Getting latest packages..."
sudo apt update
echo ""
echo "Installing required packages..."
packages="python3 python3-pip ffmpeg g++"
if [ $nodb == 'false' ];
then
    packages+=" mariadb-server"
fi
sudo apt -y install $packages
pip3 install -U pip
echo ""
if [ $nodb == 'false' ];
then
    echo "Setting up the database..."
    sudo service mysql start
    sudo mysql -Be "CREATE DATABASE maximilian;"
    sudo mysql -Be "CREATE USER 'maximilianbot'@'$ip' IDENTIFIED BY '$password';"
    sudo mysql -Be "GRANT INSERT, SELECT, UPDATE, CREATE, DELETE ON maximilian.* TO 'maximilianbot'@'$ip' IDENTIFIED BY '$password'; FLUSH PRIVILEGES;"
else
    echo "Not setting up the database."
fi
echo "$1"
if [ ! $1 == 'remote' ];
then
    echo "dbp:$password" >> config
    echo "Saved the password to 'config'"
    echo ""
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
    echo "Alrighty, Maximilian should be (almost) fully installed now. Try running it using 'python3 main.py --enablejsk -i'. If you want cogs.images and cogs.misc's bottomify command to work, use 'pip install -r requirements-extra.txt'."
else
    echo "Finished setting up the database."
fi
exit 0
