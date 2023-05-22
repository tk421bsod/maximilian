#!/bin/bash

#fancy text
#these might not display correctly on some terminals 
bold=$(tput bold)
normal=$(tput sgr0)

function ctrl-c () {
    echo ""
    echo "Exiting."
    exit 39
}

ip="%"
sleep 0.5

#we might have been invoked by main.py to start the database.
#to avoid unnecessary waiting, just check for this arg  before updating
if [ "$1" == "start" ];
then
    echo "Trying to start the database..."
    sudo service mysql start
    if [ $? != 0 ];
    then
        sudo mysqld_safe &
        if [ $? != 0 ];
        then
            sudo mysql &
            if [ $? != 0 ];
            then
                sudo /etc/init.d/mysqld start &
                if [ $? != 0 ];
                then
                    sudo systemctl start mysql
                    if [ $? != 0 ];
                    then
                        echo "Sorry, couldn't start the database."
                        exit
                    fi
                fi
            fi
        fi
    fi
    echo "Started the database."
    exit
fi

if [ "$1" == "help" ];
then
    echo "Usage: bash setup.sh [OPTION]"
    echo ""
    echo "setup.sh handles setting up and repairing different Maximilian components."
    echo "You can perform specific tasks through the use of the following options."
    echo ""
    echo "Options:"
    echo "${bold}start${normal} - Attempts to start the database with 5 different commands."
    echo "${bold}backup${normal} - Starts the database and backs up its data to './backup.sql'."
    echo "${bold}restore${normal} - Restores the database from a previously created backup. The backup must be named 'backup.sql'."
    echo "${bold}fix${normal} - Attempts to fix the database by backing up the data, reinstalling the database, and restoring from the backup."
    echo "${bold}reset${normal} - Resets the database. This deletes all data."
    echo "${bold}delete-old${normal} - Deletes any old configuration files."
    echo "${bold}nodb${normal} - Sets up Maximilian without the database. Only use this if you've already set up the database on a different computer."
    echo "${bold}onlydb${normal} - Only sets up the database."
    echo "${bold}help${normal} - Shows this message."
    echo "None - Sets up Maximilian."
    exit
fi

if [ "$1" == "nodb" ];
then
    nodb='true'
else
    nodb='false'
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

if [ "$1" == "backup" ];
then
    echo "Backing up the database..."
    bash setup.sh start
    if [ "$2" != "" ];
    then
        db="$2"
    else
        db="maximilian"
    fi
    sudo mysqldump --databases $db > backup.sql
    echo ""
    echo "Saved the backup to 'backup.sql'. Run 'bash setup.sh restore' to restore it."
    exit
fi

if [ "$1" == "restore" ];
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
        bash setup.sh start
        if [ "$2" != "" ];
        then
            db="$2"
        else
            db="maximilian"
        fi
        sudo mysql -Be "drop database ${db};"
        sudo mysql -Be "create database ${db};"
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
        bash setup.sh start
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
        bash setup.sh start
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
        bash setup.sh start
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
    echo "It looks like you've been using an older version of Maximilian."
    echo "Your data will need to be migrated as the configuration data format has changed."
    echo "Press Enter to continue."
    read -s
    echo ""
    sleep 1
    echo "token:$(cat token.txt)" >> config
    echo "dbp:$(cat dbp.txt)" >> config
    rm token.txt
    rm dbp.txt
    echo "Migrated old data."
    echo "Press Enter to continue with setup, or press Ctrl-C to quit."
    read -s
    echo "Continuing with setup."
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
echo "#This file contains sensitive information that can compromise your account. Do not share it with anyone." >> config
echo "theme_color:0x3498db" >> config
echo ""
echo "Configuration file created."
sleep 0.5
echo "A reminder:"
echo "Maximilian's configuration file contains sensitive information that can compromise your account."
echo "${bold}Do not share it with anyone.${normal}"
echo ""
sleep 2

echo "${bold}----------------Maximilian Setup----------------${normal}"
echo "This script automates most parts of setting up Maximilian. You'll still need to do a few things, like getting the token and choosing a password for the database."
if [ "$1" == "onlydb" ];
then
    echo "${bold}You've chosen to only set up the database.${normal} This will not set up Maximilian on this computer. To set up Maximilian on this computer, run this with 'nodb'."
elif [ "$1" == "nodb" ];
then
    echo "${bold}You've chosen to not set up the database on this computer.${normal} If you've set up the database on a different computer, run main.py with '--ip <ip>', <ip> being the ip address of that other computer."
    echo "This will still set up Maximilian on this computer."
else 
    echo "${bold}You didn't pass any arguments, so the database will only be configured for local access.${normal} Maximilian will still be set up."
fi
echo "This script installs several packages so ${bold}you'll need a stable Internet connection${normal} and around 1 gigabyte of free space."
echo "You can press ${bold}Ctrl-C${normal} to quit at any time."
echo ""
sleep 1
echo ""
echo "${bold}Take a moment to read through the above information. Setup will start in a few seconds.${normal}"
sleep 5
echo ""
grep -qs token ./config
if [ $? != 0 -a "$1" != "onlydb" ];
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
if [ "$1" != "onlydb" ];
then
    echo "One more thing before setup starts..."
    echo "Enter your Discord account's ID. This lets you use certain features like the 'utils' commands and Jishaku. It also makes Maximilian DM you with any errors it experiences."
    read owner_id
    echo "owner_id:$owner_id" >> config
    echo ""
fi
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
    echo "Performing initial database setup..."
    bash setup.sh start
    sudo mysql -Be "CREATE DATABASE maximilian;"
    sudo mysql -Be "CREATE USER 'maximilianbot'@'$ip' IDENTIFIED BY '$password';"
    sudo mysql -Be "GRANT INSERT, SELECT, UPDATE, CREATE, DELETE ON maximilian.* TO 'maximilianbot'@'$ip' IDENTIFIED BY '$password'; FLUSH PRIVILEGES;"
    echo "dbp:$password" >> config
    echo "Saved the password to 'config'"
    echo "Finished initial database setup."
else
    echo "Not setting up the database."
fi

if [ "$1" != 'onlydb' ];
then
    echo ""
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
    echo "last_update:" >> config
    echo "Setup is almost finished. There's just one more thing..."
    echo "Would you like to enable ${bold}automatic updates${normal}? Y/N"
    echo "If enabled, Maximilian will attempt to update itself on startup once every 14 days."
    read autoupdate
    echo ""
    if [ "${autoupdate^^}" == 'Y' -o "${autoupdate^^}" == 'YES' ];
    then
        echo "Automatic updates enabled!"
        echo "automatic_updates:True" >> config
    else
        echo "Automatic updates disabled."
        echo "You'll be asked about updating on every startup unless you use '--no-update' or '--force-update'."
        echo "To change this later, change 'automatic_updates:False' to 'automatic_updates:True' in 'config'."
        echo "automatic_updates:False" >> config
    fi
    sleep 1
    echo "Alrighty, Maximilian is fully installed now. Try running it using 'python3 main.py --enablejsk'. If you want the images module or pretty console output, use 'pip3 install -r requirements-extra.txt'."
else
    echo "Finished setting up the database."
fi
exit 0
