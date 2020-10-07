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

@app.route('/other-projects/maximilian/api', methods=['GET', 'POST'])
def save():
    try:
        #this recieves requests originating from the save function in common.js
        #data gets passed to this as parameters in a url, and this concatenates a dict containing the values and value names and passes all of the data to the insert function of common.py
        print("Request recieved")
        values = {}
        #TODO: Use the 'logging' module for logging, as it simplifies this
        log.write("Request recieved at " + str(datetime.datetime.now()) + ". Processing request... \n")
        log.flush()
        log.write("Getting parameters from URL and concatenating dict from them... \n")
        log.flush()
        print("getting parameters...")
        valuenodupe = request.args.get('valuenodupe', '')
        table = request.args.get('table', '')
        path = request.args.get('path', '')
        database = request.args.get('database', '')
        debug = bool(request.args.get('debug', False))
        valueallnum = request.args.get('valueallnum', '')
        valueallnumenabled = bool(request.args.get('valueallnumenabled', 'false'))
        currentdomain = request.args.get('currentdomain', 'animationdoctorstudio.net')
        print("appending values to dict of values")
        for key, value in request.args.items():
            if value != valuenodupe and value != table and value != path and value != debug and value != database and value != valueallnum and value != str(valueallnumenabled) and value != currentdomain:
                values[key] = value
        log.write("Finished getting parameters. Inserting data... \n")
        log.flush()
        print(currentdomain)
        if debug == True:
            print(valuenodupe)
            print(str(values))
            print(table)
            print(path)
            print(debug)
        path = path.replace("/", "")
        result = dbinst.insert(database, table, values, valuenodupe, debug, valueallnum, valueallnumenabled)
        if result == "success":
            log.write("Successfully inserted data. Redirecting...")
            log.flush()
            return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changessaved=success' )
        elif result == "debuginfoprinted":
            print("Debug info was printed successfully.")
            return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path)
        elif result == "error-duplicate":
            log.write("Duplicate found. Redirecting...")
            return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changessaved=error-duplicate')
        elif result == "error-unhandled":
            log.write("An unhandled error occured while inserting data. Redirecting...")
            return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changessaved=error-other&error='+dbinst.error+'&errorlocation=common-py-inserting-data')
        elif result == "valuenotallnum":
            return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changessaved=error-other&error=value isn\'t all numbers&errorlocation=common-py-inserting-data')
        else:
            return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changessaved=error-other&error=unknown error&errorlocation=common-py-inserting-data')
    except Exception as e:
        print("Error: " + str(e) + ". Check the log file for more details.")
        log.write("Error: " + str(e) + ". \n")
        log.flush()
        return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changesaved=error-other&error=\''+str(e)+'\'&errorlocation=savechanges-api')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
