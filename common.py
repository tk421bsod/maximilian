#common.py: common functions used throughout the backend and frontend organized into classes in one file, eliminating global variables, 
#increasing readability, and reducing file size.

from cryptography.fernet import Fernet
import pymysql.cursors
import datetime

#start of class
class db:
    #set variables used throughout class
    decrypted_databasepassword = ""
    dbobj = ""
    dbc = ""
    def __init__(self):
        #ran when an instance of this class is created
        #decrypts database password
        with open("k.txt", "r") as kfile:
            key = kfile.readline()
        with open("dbp.txt", "r") as dbpfile:
            #get encrypted data from file
            encrypted_data = dbpfile.readline()
            #create an instance of Fernet
            f = Fernet(key)
            #self refers to this class, so any variable defined outside functions becomes self.<name>, and can be accessed from anywhere in the class. 
            #in this case, we need the decrypted database password to be accessible from anywhere in the class, like the connect function below.
            #this uses Fernet to decrypt the password
            self.decrypted_databasepassword = f.decrypt(encrypted_data.encode('UTF-8'))
    
    def connect(self, database):
        #connect to db, this instance is also self.<name> because it needs to be accessible from elsewhere in the class
        self.dbobj=pymysql.connect(host='10.0.0.51',
                    user="tk421bsod",
                    password=self.decrypted_databasepassword.decode(),
                    db=database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True)
        #creates a cursor object, which then can be used to execute sql queries\
        #again, this needs to be accessible from elsewhere in the class
        self.dbc=self.dbobj.cursor()

    def insert(self, database, table, valuesdict, valuenodupe, debug):
        #try to execute this code, if an exception occurs, stop execution of this function and execute code in the Except block at the bottom
        try:
            #connect to db
            if debug == False:
                self.connect(database)
            else:
                pass
            #for each key and value, join them together with a comma and space
            valuenames = ', '.join(list(valuesdict.keys()))
            valuestoinsert = ', '.join(list(valuesdict.values()))
            #use one %s for each key as a placeholder
            valueplaceholders = ', '.join(['%s' for i in range(len(list(valuesdict.keys())))])
            #then put it all together (append each item to a list, one at a time, except for placeholders)
            inserttokens = []
            inserttokens.append(table)
            inserttokens.append(valuenames)
            inserttokens.append(valuestoinsert)
            #for every key, there's a value, so the same amount of placeholders should be used for both keys and values
            sql = "insert into %s (" + valueplaceholders + ") values (" + valueplaceholders + ")"
            #if debug is enabled (set to true), print out some debugging information and exit
            if debug == True:
                print("Value Names: " + str(valuenames))
                print("Placeholders: " + str(valueplaceholders))
                print("Data to insert: " + str(inserttokens))
                print("Table: " + str(table))
                print("SQL Query: " + str(sql))
                print("Exiting...")
                return "debuginfoprinted"
            #if debug is disabled (set to false)
            if debug == False:
                #get the number of rows with duplicate values, valuenodupe is the value that distinguishes rows (like response_trigger for responses)
                self.dbc.execute("select count(*) from %s where %s=%s", (table, valuenodupe, valuesdict["\'" + str(valuenodupe) + "\'"]))
                #set a variable to that result
                row = self.dbc.fetchone()
                #if the number of rows is greater than 0,
                if row[0] > 0:
                    #there's a duplicate
                    #if there's a duplicate, exit and return an error message
                    return "error-duplicate"
                else:
                    #if there aren't any duplicate values, insert data
                    self.dbc.execute(sql, (table, inserttokens))
                    #then close the connection (since autocommit = True, changes don't need to be commited)
                    self.dbobj.close()
                    #and exit, showing that it succeeded
                    return "success"
        #if an exception occurs, assign that exception message to a variable
        except Exception as e: 
            #then print it and log the event to a file
            print("Error: " + e + ". Exiting...")
            with open("exceptiondump.txt", "a") as dumpfile:
                dumpfile.write("\n An exception occurred while inserting data into the database at " + str(datetime.datetime.now()) + ".\n The exception was " + str(e) + ". Check the log file for more details.")
            #and return an error message
            return "error-unhandled"
class token:
    def decrypt(self):
        with open("token.txt", "r") as tokenfile:
            #use fernet to decrypt token, returning token
            encrypted_token = tokenfile.readline()
            f = Fernet(key)
            decrypted_token = f.decrypt(encrypted_token.encode('UTF-8'))
            return decrypted_token.decode()
