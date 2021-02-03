import pymysql.cursors
import datetime

class db:
    dbobj = ""
    dbc = ""
    def __init__(self, bot):
        self.error=""
        with open("dbp.txt", "r") as dbpfile:
            self.databasepassword = dbpfile.readline()
        self.ip = bot.dbip
        
    def connect(self, database):
        self.dbobj=pymysql.connect(host=self.ip,
                    user="maximilianbot",
                    password=self.databasepassword,
                    db=database,
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    autocommit=True)
        self.dbc=self.dbobj.cursor()
        return self.dbc

    def insert(self, database, table, valuesdict, valuenodupe, debug=False, valueallnum=None, valueallnumenabled=False, extraparam=None, extraparamenabled=False):
        #this might be vulnerable to sql injection, it depends on whether pymysql escapes stuff passed to execute as a positional argument after the query. i've heard it does, but i'm still skeptical.
        #valuesdict's values are the only things that are passed by the user
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
    
    def retrieve(self, database, table, valuetoretrieve, valuenametoretrieve,  retrievedvalue, debug=False):
        self.connect(database)
        self.dbc.execute("select {} from {} where {} = %s".format(valuetoretrieve, table, valuenametoretrieve), (retrievedvalue))
        row = self.dbc.fetchone()
        if debug == True:
            print("Value to retrieve: " + str(valuetoretrieve))
            print("Table: " + str(table))
            print("Value name: " + str(valuenametoretrieve))
            print("Value = " + str(retrievedvalue))
            #note that this isn't an actual query that's being executed; it's used to show what the query would look like if it actually were executed (if it were, it would be a pretty serious vulnerability)
            print("SQL Query: select " + valuetoretrieve + " from " + table + " where " + valuenametoretrieve + "=" + retrievedvalue)
            print(str(row))
            return row
        if row != None:
            return row[valuetoretrieve]
        else:
            return None

    def delete(self, database, table, valuetodelete, valuenametodelete, extraparam=None, extraparamvalue=None, extraparamenabled=False):
        self.connect(database)
        if self.retrieve(database, table, valuenametodelete, valuenametodelete, valuetodelete, False) == None:
            return "value-non-existent"
        if extraparamenabled:
            self.dbc.execute("delete from {} where {} = %s and {} = %s".format(table, valuenametodelete, extraparam), (valuetodelete, extraparamvalue))
        else:
            self.dbc.execute("delete from {} where {} = %s".format(table, valuenametodelete), valuetodelete)
        if self.retrieve(database, table, valuenametodelete, valuenametodelete, valuetodelete, False) == None or self.retrieve(database, table, valuenametodelete, valuenametodelete, valuetodelete, False):
            return "successful"
        else:
            return "error"
            
    def exec_query(self, database, querytoexecute, debug=False, fetchallrows=False):
        self.connect(database)
        self.dbc.execute(str(querytoexecute))
        if fetchallrows:
            row = self.dbc.fetchall()
        else:
            row = self.dbc.fetchone()
        return row

    def exec_safe_query(self, database, querytoexecute, params, debug=False, fetchallrows=False):
        self.connect(database)
        self.dbc.execute(str(querytoexecute), params)
        if fetchallrows:
            row = self.dbc.fetchall()
        else:
            row = self.dbc.fetchone()
        return row

class token:
    def get(self, filename):
        with open(filename, "r") as tokenfile:
            return tokenfile.readline()

