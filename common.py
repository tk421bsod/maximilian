#common.py: common functions used throughout the backend and frontend organized into classes in one file, eliminating global variables, increasing readability, and reducing file size.
#this is a WIP, so some of these don't work
from cryptography.fernet import Fernet
import pymysql.cursors
class db:

    decrypted_databasepassword = ""
    dbobj = ""
    dbc = ""
    def __init__(self):
        with open("k.txt", "r") as kfile:
            key = kfile.readline()
        with open("dbp.txt", "r") as dbpfile:
            encrypted_data = dbpfile.readline()
            f = Fernet(key)
            self.decrypted_databasepassword = f.decrypt(encrypted_data.encode('UTF-8'))
    
    def connect(self):
        self.dbobj=pymysql.connect(host='10.0.0.193',
                    user="tk421bsod",
                    password=self.decrypted_databasepassword.decode(),
                    db="maximilian",
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True)
        self.dbc=self.dbobj.cursor()

    def insert(self, valuesdict, table, valuenodupe, debug):
        try:
            #connect to db
            self.connect()
            #for each key and value, join them together with a comma and space
            valuenames = ', '.join(list(valuesdict.keys()))
            valuestoinsert = ', '.join(list(valuesdict.values()))
            #use one %s for each key as a placeholder
            valueplaceholders = ', '.join(['%s' for i in range(len(list(valuesdict.keys())))])
            #then put it all together
            inserttokens = []
            inserttokens.append(table)
            inserttokens.append(valuenames)
            inserttokens.append(valuestoinsert)
            #for every key, there's a value, so the same amount of placeholders should be used for both keys and values
            sql = "insert into %s (" + valueplaceholders + ") values (" + valueplaceholders + ")"
            if debug == True:
                print("Value Names: " + str(valuenames))
                print("Placeholders: " + str(valueplaceholders))
                print("Data to insert: " + str(inserttokens))
                print("Table: " + str(table))
                print("SQL Query: " + str(sql))
                return
            dbc.execute("select count(*) from %s where %s=%s", (table, valuenodupe, valuesdict[str(valuenodupe)] ))
            row = dbc.fetchone()
            if row[0] > 0:
                return "error-duplicate"
            else:
                dbc.execute(sql, (table, inserttokens))
                return "successful"
        except Exception as e: 
            print(e)
class token:
    def decrypt(self):
        with open("token.txt", "r") as tokenfile:
            encrypted_token = tokenfile.readline()
            f = Fernet(key)
            decrypted_token = f.decrypt(encrypted_token.encode('UTF-8'))
            return decrypted_token.decode()
