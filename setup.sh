#!/bin/bash

#fancy text
#these might not display correctly on some terminals 
bold=$(tput bold)
normal=$(tput sgr0)

if [ "$1" == "remote" ];
then
    ip="%"
else
    ip="localhost"
fi

if [ "$1" == "nodb" ];
then
    nodb='true'
else
    nodb='false'
fi

echo "${bold}----------------Maximilian Setup----------------${normal}"
echo "This script automates most parts of setting up Maximilian. You'll still need to do a few things, like getting the token and choosing a password for the database."
if [ "$1" == "remote" ];
then
    echo "${bold}You've chosen to configure the database for remote access.${normal} This will not set up Maximilian on this computer."
elif [ "$1" == "nodb" ];
then
    echo "${bold}You've chosen to not set up the database on this computer.${normal} If you've set up the database on a different computer, run main.py with '--ip <ip>', <ip> being the ip address of that other computer."
    echo "This will still set up Maximilian on this computer."
else 
    echo "${bold}You didn't pass any arguments, so the database will only be configured for local access.${normal} Maximilian will still be set up."
fi
echo "This script installs several packages (and also downloads some code) so ${bold}you'll need a stable Internet connection${normal} and around 1 gigabyte of free space."
echo "You can press ${bold}Ctrl-C${normal} or ${bold}Ctrl-Z${normal} to quit at any time."
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
echo ""
if [ ! -f "token.txt" -a ! $ip == '%' ];
then
    echo "It doesn't look like you've put a token in token.txt." 
    echo "Enter the token you want Maximiian to use. If you don't know what this is, create an application in Discord's Developer Portal, create a bot account for that application, and copy the account's token. Then paste it here."
    echo "Your input will be hidden to keep the token secret."
    read -s token
    if [ "$token" == "" -o "$token" == " " ];
    then 
        echo "You have to actually enter a token."
        exit 13
    fi
    echo "$token" >> token.txt
    echo "Alright, saved the token to 'token.txt'. If the token isn't valid, either edit the file and add the correct token or delete the file and run this again."
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
    echo "It'll be saved to 'dbp.txt' after setting up the database."
fi
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
    sudo mysql -Be "CREATE DATABASE maximilian; CREATE DATABASE maximilian_test; CREATE USER 'maximilianbot'@'$ip' IDENTIFIED BY '$password'; GRANT INSERT, SELECT, UPDATE, CREATE, DELETE on maximilian_test.* TO 'maximilianbot'@'$ip' IDENTIFIED BY '$password'; GRANT INSERT, SELECT, UPDATE, CREATE, DELETE ON maximilian.* TO 'maximilianbot'@'$ip' IDENTIFIED BY '$password'; FLUSH PRIVILEGES;"
else
    echo "Not setting up the database."
fi
if [ -f "dbp.txt" ];
then
    rm -f dbp.txt
fi
if [ ! $ip == '%' ];
then
    echo "$password" >> dbp.txt
    echo "Saved the password to dbp.txt"
    echo ""
    echo "Installing dependencies..."
    pip3 install -r requirements.txt
    echo ""
    echo "Alrighty, Maximilian should be (almost) fully installed now. Try running it using 'python3 main.py --enablejsk -i'. If you want cogs.images and cogs.misc's bottomify command to work, use 'pip install -r requirements-extra.txt'."
else
    echo "Finished setting up the database."
fi
