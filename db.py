#db.py: some database utilities
import logging
import os
import inspect

import pymysql

class db:
    """
    Methods used for interaction with the database.

    This class provides no public attributes.

    Methods
    -------

    ensure_tables() - Ensures that all required tables exist. Called by main.run().
    exec(query, params, *,  fetchall) - Executes 'query' with 'params'. Uses pymysql's parameterized queries. 'params' can be empty.
    exec_query(query, *, fetchall) - Executes 'query'. DEPRECATED due to the potential for SQL injection. Will show a warning if used.
    """

    def __init__(self, bot=None, password=None, ip=None, database=None):
        """
        Parameters
        ----------
        bot : discord.ext.commands.Bot, optional
            A discord.ext.commands.Bot instance. This parameter may be removed in the future.
        password : str, optional
            The database password in plain text. TODO: why is this optional
        ip : str, optional
            The IP address to use for the database. Defaults to 'localhost'. Optional if `bot` has a `dbip` attribute.
        database : str, optional
            The name of the database to connect to. Optional if `bot` has a `database` attribute. 
        """
        try:
            with open("dbp.txt", "r") as dbpfile:
                print("It looks like you still have some files left over from the configuration data format change. Run `bash setup.sh delete-old` to get rid of them.")
        except FileNotFoundError:
            pass
        self.databasepassword = password
        if bot:
            self.ip = bot.dbip
            self.database = bot.database
        else:
            if not ip:
                ip = "localhost"
            self.ip = ip
            self.database = database
        self.TABLES = {'mute_roles':'guild_id bigint, role_id bigint', 'reminders':'user_id bigint, channel_id bigint, reminder_time datetime, now datetime, reminder_text text, uuid text', 'prefixes':'guild_id bigint, prefix text', 'responses':'guild_id bigint, response_trigger varchar(255), response_text text, constraint pk_responses primary key (guild_id, response_trigger)', 'config':'guild_id bigint, category varchar(255), setting varchar(255), enabled tinyint, constraint pk_config primary key (guild_id, setting, category)', 'blocked':'user_id bigint', 'roles':'guild_id bigint, role_id bigint, message_id bigint, emoji text', 'songs':'name text, id text, duration varchar(8), thumbnail text', 'todo':'user_id bigint, entry text, timestamp datetime', 'active_requests':'id bigint', 'chainstats':'user_id bigint, breaks tinyint unsigned, starts tinyint unsigned, constraint users primary key (user_id)'}
        self.logger = logging.getLogger(__name__)
        self.failed = False
        #try to open a connection to the database
        self.conn = self.attempt_connection()
        self.logger.info("Connected to database.")

    def requires_connection(func):
        def requires_connection_inner(self, *args, **kwargs):
            """Attempts a reconnect if OperationalError is raised"""
            try:
                self.logger.debug(f"Calling {func.__name__} with {args}")
                return func(self, *args, **kwargs)
            except (pymysql.err.OperationalError, pymysql.err.InterfaceError) as e:
                self.logger.warn("unknown database error, attempting a reconnect")
                self.reconnect()
                return func(self, *args, **kwargs)
        return requires_connection_inner

    @requires_connection
    def ensure_tables(self):
        self.logger.info("Finishing database setup...")
        for table, schema in self.TABLES.items():
            try:
                self.conn.execute(f'select * from {table}')
            except pymysql.err.ProgrammingError:
                self.logger.debug(f'Table {self.database}.{table} doesn\'t exist. Creating it.')
                self.logger.debug(f"Schema for this table is {schema}")
                self.conn.execute(f'create table {table}({schema})')
                if not self.failed:
                    self.failed = True
        if not self.failed:
            self.logger.info('Database setup was already finished, nothing to do')
        else:
            self.logger.warning('Database setup finished.')

    def attempt_connection(self):
        self.logger.info(f"Attempting to connect to database '{self.database}' on '{self.ip}'...")
        return self.connect()

    def reconnect(self):
        self.conn = self.connect()

    def connect(self):
        return pymysql.connect(host=self.ip, user="maximilianbot", password=self.databasepassword, db=self.database, charset='utf8mb4', cursorclass=pymysql.cursors.DictCursor, autocommit=True).cursor()

    @requires_connection
    def exec(self, query, params, *, fetchall=False):
        """Executes 'query' with 'params'. Uses pymysql's parameterized queries.

        Parameters
        ----------
        query : str
            The SQL query to execute. 
        params : str
            The parameters for the query.
        """
        self.conn.execute(str(query), params)
        row = self.conn.fetchall()
        if len(row) == 1:
            row = row[0]
        return row if row != () and row != "()" else None
	
