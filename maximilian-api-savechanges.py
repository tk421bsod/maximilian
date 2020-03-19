#flask, datetime, pymysql.cursors, and cryptography.fernet are needed for this, so import them
from flask import Flask, escape, request, redirect
import datetime
import pymysql.cursors
from cryptography.fernet import Fernet
#once imported, open the log file in append mode, as we don't want to overwrite the file every time this is ran
log = open("maximilian-api-savechanges-log.txt", "a")
#write the time the log file was opened and flush the buffer so changes appear immediately
log.write("Log opened at " + str(datetime.datetime.now()) + ". \n")
log.flush()

app = Flask('maximilian-api-savechanges')

@app.route('/other-projects/maximilian/api/savechanges', methods=['GET', 'POST'])
def save():
    try:
        try:
            #decrypts database password using Fernet, resulting in better security at the cost of a couple tenths of a second
            log.write("Decrypting database password... \n")
            log.flush()
            print("Decrypting database password...")
            with open("k.txt", "r") as kfile:
                #opens key file and assigns its contents to a variable
                key = kfile.readline()
            with open("dbp.txt", "r") as dbpfile:
                #opens file containing encrypted password and assigns its contents to a variable
                encrypted_data = dbpfile.readline()
                #then creates an instance of Fernet with the key
                f = Fernet(key)
                #and decrypts the data with Fernet's decrypt function, making sure that the encrypted data has the proper encoding
                decrypted_data = f.decrypt(encrypted_data.encode('UTF-8'))
            log.write("Password decrypted. \n")
            log.flush()
            print("Password decrypted.")
            print("Connecting to the database, this may take a bit.")
            log.write("Connecting to the database, this may take a bit. \n")
            log.flush()
            #after decrypting the password, connect to the database
            dbfile=pymysql.connect(host='10.0.0.193',-
                                    user='tk421bsod',
                                    password=decrypted_data.decode(),
                                    db='maximilian',
                                    charset='utf8mb4',
                                    cursorclass=pymysql.cursors.DictCursor)
            #create the cursor object
            db=dbfile.cursor()
            #then write that the connection was successful, to both the log and the terminal
            log.write("Successfully connected to the database at " + str(datetime.datetime.now()) + ". \n")
            print("Successfully connected to the database at " + str(datetime.datetime.now()) + ".")
            log.flush()
        except Exception as e:
            #if there's an error while executing any of this code
            print("Error while connecting to the database: " + str(e) + " Check the log file for more details.")
            log.write("Error while connecting to the database: " + str(e) + ". \n")
            log.flush()
        log.write("Request recieved at " + str(datetime.datetime.now()) + ". Processing request... \n")
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
            log.write("No duplicates found. Validating guild ID... \n")
            log.flush()
            try:
                test=int(guild_id)
                print(test)
            except Exception as e:
                log.write("The guild ID isn't a number. Redirecting... \n")
                log.flush()
                print("The guild ID isn't a number. Redirecting...")
                return redirect('http://animationdoctorstudio.net/other-projects/maximilian?redirectsource=saveresponse&responsesaved=error-guildid-invalid')
                pass
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
            db.close()
            return redirect('http://animationdoctorstudio.net/other-projects/maximilian?redirectsource=saveresponse&responsesaved=error-duplicate')
    except Exception as e:
        print("Error: " + str(e) + ". Check the log file for more details.")
        log.write("Error: " + str(e) + ". \n")
        log.flush()



if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)