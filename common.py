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
        self.error=""
        #ran when an instance of this class is created
        #decrypts database password
        with open("k.txt", "r") as kfile:
            self.key = kfile.readline()
        with open("dbp.txt", "r") as dbpfile:
            #get encrypted data from file
            encrypted_data = dbpfile.readline()
            #create an instance of Fernet
            f = Fernet(self.key)
            #self refers to this class, so any variable defined outside functions becomes self.<name>, and can be accessed from anywhere in the class. 
            #in this case, we need the decrypted database password to be accessible from anywhere in the class, like the connect function below.
            #this uses Fernet to decrypt the password
            self.decrypted_databasepassword = f.decrypt(encrypted_data.encode('UTF-8'))
    
    def connect(self, database):
        #connect to db, this instance is also self.<name> because it needs to be accessible from elsewhere in the class
        self.dbobj=pymysql.connect(host='10.0.0.51',
                    user="maximilianbot",
                    password=self.decrypted_databasepassword.decode(),
                    db=database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True)
        #creates a cursor object, which then can be used to execute sql queries
        #again, this needs to be accessible from elsewhere in the class
        self.dbc=self.dbobj.cursor()
        return self.dbc

    def insert(self, database, table, valuesdict, valuenodupe, debug, valueallnum, valueallnumenabled, extraparam, extraparamenabled):
        #maximilian-api-savechanges.py passes data to this, where it concatenates lists of values to insert, value placeholders, and checks if data is valid and has no duplicates.
        #this is one of the only functions that actually connects to a db
        #try to execute this code, if an exception occurs, stop execution of this function and execute code in the Except block at the bottom
        try:
            #connect to db
            if debug == False:
                self.connect(database)
            else:
                pass
            #for each key and value, join them together with a comma and space
            #use one %s for each key as a placeholder
            valuenameplaceholders = ', '.join([f'{i}' for i in list(valuesdict.keys())])
            valueplaceholders = ', '.join(['%s' for i in list(valuesdict.values())])
            valueslist = list(valuesdict.values())
            #then put it all together (append each item to a list, one at a time, except for placeholders)
            #for every key, there's a value, so the same amount of placeholders should be used for both keys and values
            sql = f"insert into {table} (" + valuenameplaceholders + ") values (" + valueplaceholders + ")"
            #if debug is enabled (set to true), print out some debugging information and exit
            if debug == True:
                valuenames = ', '.join(list(valuesdict.keys()))
                values =  ', '.join([i for i in list(valuesdict.values())])
                print("Value Names: " + str(valuenames))
                print("Placeholders: " + str(valuenameplaceholders))
                print("Data to insert: " + str(values))
                print("Table: " + str(table))
                print("SQL Query: " + str(sql))
                print("Exiting...")
                return "debuginfoprinted"
            #if debug is disabled (set to false)
            if debug == False:
                if valueallnumenabled:
                    try:
                        checkallnum=int(valuesdict[valueallnum])
                    except Exception:
                        return "error-valuenotallnum"
                #get the number of rows with duplicate values, valuenodupe is the value that distinguishes rows (like response_trigger for responses)
                try:
                    if extraparamenabled:
                        self.dbc.execute("select count(*) from {} where {}=%s and {}=%s".format(table, valuenodupe, extraparam), (valuesdict[valuenodupe], valuesdict[extraparam]))
                    else:
                        self.dbc.execute("select count(*) from {} where {}=%s".format(table, valuenodupe), (valuesdict[valuenodupe]))
                    #set a variable to that result
                    row = self.dbc.fetchone()
                    #if the number of rows is greater than 0,
                    if row['count(*)'] > 0:
                        print("duplicates found")
                        #there's a duplicate
                        #if there's a duplicate, exit and return an error message
                        return "error-duplicate"
                    else:
                        print("no duplicates")
                        self.dbc.execute(sql, (valueslist))
                        #then close the connection (since autocommit = True, changes don't need to be commited)
                        self.dbobj.close()
                        #and exit, showing that it succeeded
                        return "success"
                except KeyError:
                    print("no duplicates")
                    self.dbc.execute(sql, (valueslist))
                    self.dbobj.close()
                    return "success"
        #if an exception occurs, assign that exception message to a variable
        except Exception as e: 
            #then print it and log the event to a file
            print("Error: " + e + ". Exiting...")
            self.error=e
            raise pymysql.err.OperationalError
    
    def retrieve(self, database, table, valuetoretrieve, valuenametoretrieve,  retrievedvalue, debug):
        self.connect(database)
        self.dbc.execute("select {} from {} where {} = %s".format(valuetoretrieve, table, valuenametoretrieve), (retrievedvalue))
        row = self.dbc.fetchone()
        if debug == True:
            print("Value to retrieve: " + str(valuetoretrieve))
            print("Table: " + str(table))
            print("Value name: " + str(valuenametoretrieve))
            print("Value = " + str(retrievedvalue))
            print("SQL Query: select " + valuetoretrieve + " from " + table + " where " + valuenametoretrieve + "=" + retrievedvalue)
            print(str(row))
            return row
        if row != None:
            return row[valuetoretrieve]
        else:
            return row

    def delete(self, database, table, valuetodelete, valuenametodelete, extraparam, extraparamvalue, extraparamenabled):
        self.connect(database)
        if self.retrieve(database, table, valuenametodelete, valuenametodelete, valuetodelete, False) == None:
            return "value-non-existent"
        if extraparamenabled:
            self.dbc.execute("delete from {} where {} = '{}' and {} = {}".format(table, valuenametodelete, valuetodelete, extraparam, extraparamvalue))
        else:
            self.dbc.execute("delete from {} where {} = '{}'".format(table, valuenametodelete, valuetodelete))
        if self.retrieve(database, table, valuenametodelete, valuenametodelete, valuetodelete, False) == None or self.retrieve(database, table, valuenametodelete, valuenametodelete, valuetodelete, False):
            return "successful"
        else:
            return "error"
            
    def exec_query(self, database, querytoexecute, debug, fetchallrows):
        self.connect(database)
        self.dbc.execute(str(querytoexecute))
        if fetchallrows:
            row = self.dbc.fetchall()
        else:
            row = self.dbc.fetchone()
        return row

class token:
    def decrypt(self, filename):
        with open(filename, "r") as tokenfile:
            with open("k.txt", "r") as kfile:
                self.key = kfile.readline()
            #use fernet to decrypt token, returning token
            encrypted_token = tokenfile.readline()
            f = Fernet(self.key)
            decrypted_token = f.decrypt(encrypted_token.encode('UTF-8'))
            return decrypted_token.decode()

