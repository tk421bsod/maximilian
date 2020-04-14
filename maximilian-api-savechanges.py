#flask.Flask, flask.escape, flask.request, flask.redirect, datetime, pymysql.cursors, and cryptography.fernet.Fernet are needed for this, so import them
from flask import Flask, escape, request, redirect
import datetime
import pymysql.cursors
from cryptography.fernet import Fernet
import os
from common import db
#once imported, open the log file in append mode, as we don't want to overwrite the file every time this is ran
log = open("maximilian-api-savechanges-log.txt", "a")
#write the time the log file was opened and flush the buffer so changes appear immediately
log.write("Log opened at " + str(datetime.datetime.now()) + ". \n")
log.flush()

app = Flask('maximilian-api-savechanges')

@app.route('/other-projects/maximilian/api/', methods=['GET', 'POST'])
def save():
    try:
        db.connect()
        log.write("Request recieved at " + str(datetime.datetime.now()) + ". Processing request... \n")
        log.flush()
        log.write("Getting parameters from URL... \n")
        log.flush()
        for key, value in request.args.items:
            print(key)
        os._exit()
        path = request.args.get('path', '')
        #TODO: make this work for every form on the website by iterating over every item in requests.args and getting their values
        #'path' is what form the request originated from
        guild_id = request.args.get('guild_id', '')
        print(guild_id)
        response_trigger = request.args.get('response_trigger', '')
        print(response_trigger)
        response_text = request.args.get('response_text', '')
        print(response_text)
        log.write("Finished getting parameters. Checking for duplicate entries... \n")
        log.flush()
        db.execute("select * from responses where guild_id=%s and response_trigger=%s;", (guild_id, response_trigger))
        row = db.fetchone()
        print(row)
        if row == None:
            log.write("No duplicates found. Validating guild ID... \n")
            log.flush()
            try:
                test=int(guild_id)
                print(test)
            except Exception as e:
                log.write("The guild ID isn't valid. Redirecting... \n")
                log.flush()
                db.close()
                print("The guild ID isn't valid. Redirecting...")
                return redirect('http://animationdoctorstudio.net/other-projects/maximilian?redirectsource=saveresponse&responsesaved=error-guildid-invalid')
                pass
            log.write("The guild ID is valid. Inserting data into table... \n")
            log.flush()
            db.execute("INSERT INTO responses(guild_id, response_trigger, response_text) VALUES (%s, %s, %s);", (guild_id, response_trigger, response_text))
            log.write("Data inserted. Committing changes... \n")
            log.flush()
            dbfile.commit()
            log.write("Changes committed. Redirecting... \n")
            log.flush()
            db.close()
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian?redirectsource=saveresponse&responsesaved=successful')
        else:
            log.write("Duplicate found. Redirecting... \n")
            log.flush()
            db.close()
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian?redirectsource=saveresponse&responsesaved=error-duplicate')
    except Exception as e:
        print("Error: " + str(e) + ". Check the log file for more details.")
        log.write("Error: " + str(e) + ". \n")
        log.flush()
        db.close()
        redirect('http://animationdoctorstudio.net/other-projects/maximilian/responses?redirectsource=saveresponse&responsesaved=error-unknown')
        os._exit()


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)