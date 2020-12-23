
from cryptography.fernet import Fernet
import pymysql.cursors
import datetime

class db:
    decrypted_databasepassword = ""
    dbobj = ""
    dbc = ""
    def __init__(self):
        self.error=""
        with open("k.txt", "r") as kfile:
            self.key = kfile.readline()
        with open("dbp.txt", "r") as dbpfile:
            encrypted_data = dbpfile.readline()
            f = Fernet(self.key)
            self.decrypted_databasepassword = f.decrypt(encrypted_data.encode('UTF-8'))
    
    def connect(self, database):
        self.dbobj=pymysql.connect(host='10.0.0.51',
                    user="maximilianbot",
                    password=self.decrypted_databasepassword.decode(),
                    db=database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True)
        self.dbc=self.dbobj.cursor()
        return self.dbc

    def insert(self, database, table, valuesdict, valuenodupe, debug, valueallnum, valueallnumenabled, extraparam, extraparamenabled):
        if debug == False:
            self.connect(database)
        else:
            pass
        valuenameplaceholders = ', '.join([f'{i}' for i in list(valuesdict.keys())])
        valueplaceholders = ', '.join(['%s' for i in list(valuesdict.values())])
        valueslist = list(valuesdict.values())
        sql = f"insert into {table} (" + valuenameplaceholders + ") values (" + valueplaceholders + ")"
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
        if debug == False:
            if valueallnumenabled:
                try:
                    checkallnum=int(valuesdict[valueallnum])
                except Exception:
                    return "error-valuenotallnum"
            try:
                if extraparamenabled:
                    self.dbc.execute("select count(*) from {} where {}=%s and {}=%s".format(table, valuenodupe, extraparam), (valuesdict[valuenodupe], valuesdict[extraparam]))
                else:
                    self.dbc.execute("select count(*) from {} where {}=%s".format(table, valuenodupe), (valuesdict[valuenodupe]))
                row = self.dbc.fetchone()
                if row['count(*)'] > 0:
                    print("duplicates found")
                    return "error-duplicate"
                else:
                    print("no duplicates")
                    self.dbc.execute(sql, (valueslist))
                    self.dbobj.close()
                    return "success"
            except KeyError:
                print("no duplicates")
                self.dbc.execute(sql, (valueslist))
                self.dbobj.close()
                return "success"
    
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
            encrypted_token = tokenfile.readline()
            f = Fernet(self.key)
            decrypted_token = f.decrypt(encrypted_token.encode('UTF-8'))
            return decrypted_token.decode()

