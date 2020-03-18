from flask import Flask, escape, request, redirect
import datetime
import pymysql.cursors
from cryptography.fernet import Fernet
log = open("maximilian-api-savechanges-log.txt", "a")
log.write("Log opened at " + str(datetime.datetime.now()) + ". \n")
log.flush()
try:
    log.write("Decrypting database password...")
    log.flush()
    print("Decrypting database password...")
    with open("k.txt", "r") as kfile:
        key = kfile.readline()
    with open("dbp.txt", "r") as dbpfile:
        encrypted_data = dbpfile.readline()
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data.encode('UTF-8'))
    log.write("Password decrypted.")
    log.flush()
    print("Password decrypted.")
    print("Connecting to the database, this may take a bit.")
    log.write("Connecting to the database, this may take a bit. \n")
    log.flush()
    dbfile=pymysql.connect(host='10.0.0.193',
                             user='tk421bsod',
                             password=decrypted_data.decode(),
                             db='maximilian',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)
    db=dbfile.cursor()
    log.write("Successfully connected to the database at " + str(datetime.datetime.now()) + ". \n")
    print("Successfully connected to the database at " + str(datetime.datetime.now()) + ".")
    log.flush()
except Exception as e:
    print("Error while connecting to the database: " + str(e) + " Check the log file for more details.")
    log.write("Error while connecting to the database: " + str(e) + "\n")
    log.flush()


app = Flask('maximilian-api-savechanges')

@app.route('/other-projects/maximilian/api/savechanges', methods=['GET', 'POST'])
def save():
    try:
        log.write("Request recieved at" + str(datetime.datetime.now()) + ". Processing request... \n")
        log.flush()
        log.write("Getting parameters from URL... \n")
        log.flush()
        guild_id = request.args.get('guild_id', '')
        print(guild_id)
        response_trigger = request.args.get('response_trigger', '')
        print(response_trigger)
        response_text = request.args.get('response_text', '')
        print(response_text)
        log.write("Finished getting parameters. Checking for duplicate database entries... \n")
        log.flush()
        db.execute("select * from responses where guild_id=%s and response_trigger=%s;", (guild_id, response_trigger))
        row = db.fetchone()
        print(row)
        if row == None:
            log.write("No duplicates found. Inserting data into table... \n")
            log.flush()
            db.execute("INSERT INTO responses(guild_id, response_trigger, response_text) VALUES (%s, %s, %s);", (guild_id, response_trigger, response_text))
            log.write("Data inserted. Committing response... \n")
            log.flush()
            dbfile.commit()
            log.write("Changes committed. Redirecting... \n")
            log.flush()
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian?redirectsource=saveresponse&responsesaved=successful')
        else:
            log.write("Duplicate found. Redirecting... \n")
            log.flush()
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian?redirectsource=saveresponse&responsesaved=error-duplicate')
    except Exception as e:
        print("Error: " + str(e) + " Check the log file for more details.")
        log.write("Error: " + str(e) + "\n")
        log.flush()



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)