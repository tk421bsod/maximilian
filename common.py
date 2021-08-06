import pymysql.cursors
import logging

class db:
    dbobj = ""
    dbc = ""
    def __init__(self, bot=None):
        self.error=""
        try:
            with open("dbp.txt", "r") as dbpfile:
                self.databasepassword = dbpfile.readline().strip()
        except FileNotFoundError:
            print("Couldn't find a file containing the database password. It needs to be named 'dbp.txt'.")
            quit()
        if bot:
            self.ip = bot.dbip
        else:
            self.ip = "10.0.0.51"
        self.logger = logging.getLogger(name=__name__)

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

    def exec_query(self, database, query, params, *, noreturn=False, fetchall=False):
        #TODO: Don't try to connect on every call of this, maybe do a query and reconnect if it fails
        self.dbc = self.connect(database)
        self.dbc.execute(str(query), params)
        if fetchall:
            row = self.dbc.fetchall()
        if noreturn:
            return True
        else:
            row = self.dbc.fetchone()
        return row if row else None

class token:
    def get(self, filename):
        try:
            with open(filename, "r") as tokenfile:
                return tokenfile.readline()
        except:
            print("Couldn't find a file containing a token. It needs to be named either 'token.txt' (stable), 'betatoken.txt' (beta), or 'devtoken.txt' (dev).")
            quit()
