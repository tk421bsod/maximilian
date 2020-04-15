#flask.Flask, flask.escape, flask.request, flask.redirect, datetime, pymysql.cursors, and cryptography.fernet.Fernet are needed for this, so import them
from flask import Flask, escape, request, redirect
import datetime
import pymysql.cursors
from cryptography.fernet import Fernet
import os
from common import db

dbinst = db()
dbinst.connect("maximilian")
#once imported, open the log file in append mode, as we don't want to overwrite the file every time this is ran
log = open("maximilian-api-savechanges-log.txt", "a")
#write the time the log file was opened and flush the buffer so changes appear immediately
log.write("Log opened at " + str(datetime.datetime.now()) + ". \n")
log.flush()

app = Flask('maximilian-api-savechanges')

@app.route('/other-projects/maximilian/api/', methods=['GET', 'POST'])
def save():
    try:
        values = {}
        log.write("Request recieved at " + str(datetime.datetime.now()) + ". Processing request... \n")
        log.flush()
        log.write("Getting parameters from URL and concatenating dict from them... \n")
        log.flush()
        print("getting parameters...")
        valuenodupe = request.args.get('valuenodupe', '')
        table = request.args.get('table', '')
        path = request.args.get('path', '')
        for key, value in request.args.items():
            if value != valuenodupe:
                if value != table:
                    if value != path:
                        values[key] = value
        log.write("Finished getting parameters. Inserting data, using common.py's insert function... \n")
        log.flush()
        result = dbinst.insert("maximilian", table, values, valuenodupe, False)
        print("called function")
        if result == "success":
            log.write("Successfully inserted data. Redirecting...")
            log.flush()
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian/' + path + '?redirectsource=savechanges&changessaved=success' )
        elif result == "debuginfoprinted":
            print("Debug info was printed successfully.")
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian/' + path)
        elif result == "error-duplicate":
            log.write("Duplicate found. Redirecting...")
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian/' + path + '?redirectsource=savechanges&changessaved=error-duplicate')
        elif result == "error-unhandled":
            log.write("An unhandled error occured while inserting data. Redirecting...")
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian/' + path + '?redirectsource=savechanges&changesaved=error-unknown')
    except Exception as e:
        print("Error: " + str(e) + ". Check the log file for more details.")
        log.write("Error: " + str(e) + ". \n")
        log.flush()
        return redirect('http://animationdoctorstudio.net/other-projects/maximilian/' + path + '?redirectsource=savechanges&changesaved=error-unknown')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)