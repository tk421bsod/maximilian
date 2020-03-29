import csv
import requests
import pymysql.cursors
from cryptography.fernet import Fernet

try:

    datalocation = "https://raw.githubusercontent.com/nytimes/covid-19-data/master/us-states.csv"

    with open("k.txt", "r") as kfile:
                    key = kfile.readline()
    with open("dbp.txt", "r") as dbpfile:
        encrypted_data = dbpfile.readline()
        f = Fernet(key)
        decrypted_data = f.decrypt(encrypted_data.encode('UTF-8'))
    dbfile=pymysql.connect(host='10.0.0.193',
                            user='tk421bsod',
                            password=decrypted_data.decode(),
                            db='covid19data',
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
    #create the cursor object
    db=dbfile.cursor()

    r = requests.get(datalocation)
    csvfile = r.text
    with open("covid-data.csv", "w") as datafile:
        datafile.write(csvfile)
    with open("covid-data.csv", "r") as data:
        reader = csv.DictReader(data)
        for row in reader:
            date = row['date']
            state = row['state']
            cases = row['cases']
            deaths = row['deaths']
            db.execute("select * from covid19data where date=%s and state=%s and cases=%s and deaths=%s;", (date, state, cases, deaths))
            dbrow = db.fetchone()
            print(dbrow)
            if dbrow == None:
                print("Inserted row")
                db.execute("insert into covid19data(date, state, cases, deaths) values (%s, %s, %s, %s);", (date, state, cases, deaths))
                dbfile.commit()
            else:
                print("Duplicate found")
                pass
    db.close()
except Exception as e:
    print(e)