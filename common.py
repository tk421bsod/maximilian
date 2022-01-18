import logging
import os

import pymysql


class db:
    dbobj = ""
    dbc = ""
    def __init__(self, bot=None, password=None):
        self.error=""
        try:
            if not password:
                bot.logger.debug("Getting database password from dbp.txt.")
                with open("dbp.txt", "r") as dbpfile:
                    self.databasepassword = dbpfile.readline().strip()
            else:
                self.databasepassword = password
        except FileNotFoundError:
            print("Couldn't find a file containing the database password. \nIf you haven't run setup.sh yet, run it.")
            os._exit(14)
        if bot:
            self.ip = bot.dbip
            self.database = bot.database
        else:
            self.ip = "10.0.0.51"
        self.logger = logging.getLogger(name=f'maximilian.{__name__}')
        #mapping of schema to table name
        self.tables = {'mute_roles':'guild_id bigint, role_id bigint', 'reminders':'user_id bigint, channel_id bigint, reminder_time datetime, now datetime, reminder_text text, uuid text', 'prefixes':'guild_id bigint, prefix text', 'responses':'guild_id bigint, response_trigger text, response_text text', 'config':'guild_id bigint, setting text, enabled tinyint', 'blocked':'user_id bigint', 'roles':'guild_id bigint, role_id bigint, message_id bigint, emoji text', 'songs':'name text, id text, duration varchar(8), thumbnail text', 'todo':'user_id bigint, entry text, timestamp datetime', 'active_requests':'id bigint', 'chainstats':'user_id bigint, breaks tinyint unsigned, starts tinyint unsigned'}
        self.failed = False

    def ensure_tables(self):
        self.logger.info("Making sure all required tables exist...")
        self.connect(self.database)
        for table, schema in self.tables.items():
            try:
                self.dbc.execute(f'select * from {table}')
            except pymysql.err.ProgrammingError:
                self.logger.warning(f'Table {self.database}.{table} doesn\'t exist. Creating it...')
                self.logger.debug(f"Schema for this table is {schema}")
                self.dbc.execute(f'create table {table}({schema})')
                if not self.failed:
                    self.failed = True
        if not self.failed:
            self.logger.info('All required tables exist.')
        else:
            self.logger.info('Done creating tables.')

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

    #maybe make this an alias to exec_safe_query or rename exec_safe query to this?
    def exec_query(self, database, querytoexecute, debug=False, fetchall=False):
        self.connect(database)
        self.dbc.execute(str(querytoexecute))
        if fetchall:
            row = self.dbc.fetchall()
        else:
            row = self.dbc.fetchone()
        return row if row != () and row != "()" else None

    def exec_safe_query(self, database, querytoexecute, params, debug=False, fetchall=False):
        self.dbc = self.connect(database)
        self.dbc.execute(str(querytoexecute), params)
        if fetchall:
            row = self.dbc.fetchall()
        else:
            row = self.dbc.fetchone()
        return row if row != () and row != "()" else None

class token:
    def get(self, filename):
        self.logger = logging.getLogger(name=f'maximilian.{__name__}')
        self.logger.info(f"Getting token from {filename}.")
        try:
            with open(filename, "r") as tokenfile:
                return tokenfile.readline()
        except:
            print("Couldn't find a file containing a token. It needs to be named either 'token.txt' (stable), 'betatoken.txt' (beta), or 'devtoken.txt' (dev).")
            os._exit(96)
