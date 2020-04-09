#common.py: common functions used throughout the backend and frontend organized into classes in one file, eliminating global variables, increasing readability, and reducing file size.

from cryptography.fernet import Fernet
import pymysql.cursors
class db:

    def __init__():
        with open("k.txt", "r") as kfile:
            key = kfile.readline()
        with open("dbp.txt", "r") as dbpfile:
            encrypted_data = dbpfile.readline()
            f = Fernet(key)
            decrypted_databasepassword = f.decrypt(encrypted_data.encode('UTF-8'))
        dbobj=pymysql.connect(host='10.0.0.193',
                            user="tk421bsod",
                            password=decrypted_databasepassword.decode(),
                            db="maximilian",
                            charset='utf8mb4',
                            cursorclass=pymysql.cursors.DictCursor)
        dbc=dbobj.cursor()

    def insert(values, table):
        dbc.execute("select * from %s where guild_id=%s", (table, message.guild.id))
        row = dbc.fetchone()
        if row != None:


class token:
    def decrypt()
    with open("token.txt", "r") as tokenfile:
        encrypted_token = tokenfile.readline()
        f = Fernet(key)
        decrypted_token = f.decrypt(encrypted_token.encode('UTF-8'))
        return decrypted_token.decode()
