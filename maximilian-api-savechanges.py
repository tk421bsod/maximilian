from flask import Flask, escape, request, redirect
import datetime
import pymysql.cursors
from cryptography.fernet import Fernet
import os
from common import db
<<<<<<< HEAD
import requests

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
        db.connect()
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
        results = {"success":"?redirectsource=savechanges&changessaved=success", "debuginfoprinted":"", "error-duplicate":"?redirectsource=savechanges&changessaved=error-duplicate", "error-unhandled":"?redirectsource=savechanges&changessaved=error-other&error="+dbinst.error+"&errorlocation=common-py-inserting-data", "valuenotallnum":"?redirectsource=savechanges&changessaved=error-valuenotallnum"}
        for key in results.keys():
            if result == key:
                if result == "success":
                    makegetrequest()
                return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + results[result])
        return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + "'?redirectsource=savechanges&changessaved=error-other&error=unknown&errorlocation=common-py-inserting-data'")
        
    except Exception as e:
        print("Error: " + str(e) + ". Check the log file for more details.")
        log.write("Error: " + str(e) + ". \n")
        log.flush()
        return redirect('http://' + currentdomain + '/other-projects/maximilian/' + path + '?redirectsource=savechanges&changesaved=error-other&error=\''+str(e)+'\'&errorlocation=savechanges-api')


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
