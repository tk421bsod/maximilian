from passlib.context import CryptContext
from common import db
from flask import Flask, escape, request, redirect
import pymysql.cursors
import os

dbinst = db()

app = Flask('maximilian-api-login')

pwd_context = CryptContext(
        schemes=["pbkdf2_sha256"],
        default="pbkdf2_sha256",
        pbkdf2_sha256__default_rounds=1000000
)

def encrypt_password(password, username, insert):
    print("encrypting password")
    encrypted_password = pwd_context.hash(bytes(password, "UTF-8"))
    print("encrypted password")
    values = {'username':username, 'encrypted_password':encrypted_password}
    print("concatenated dict")
    if insert == True:
        print("inserting data...")
        result = dbinst.insert("maximilian", "passwords", values, "username", False, "", False)
        print("inserted values into database")
    return encrypted_password

def check_encrypted_password(password, encrypted_password):
    hashed = dbinst.retrieve("maximilian", "passwords", "encrypted_password", encrypted_password, "encrypted_password")
    return pwd_context.verify(password, hashed)

def generate_token(username):
    token = pwd_context.encrypt(username)
    return token

@app.route('/other-projects/maximilian/api/login', methods=['GET', 'POST'])
def login():
    try:
        print("Request recieved")
        username = request.args.get('username', '')
        password = request.args.get('password', '')
        print("Got parameters")
        register = bool(request.args.get('register', 'False'))
        resp = app.make_response({'location': 'http://animationdoctorstudio.net/other-projects/maximilian/webinterface'})
        print("created response object")
        if register == True:
            print("user has registered")
            encrypted_password = encrypt_password(password, username, True)
            print("encrypted password")
            row = dbinst.retrieve("maximilian", "passwords", "encrypted_password", encrypted_password, "encrypted_password", False)
            print("retrieved password")
            os._exit()
            if check_encrypted_password(password, row):
                resp.set_cookie('token', token)
            return resp
        else:
            if request.cookies.get('token') != None:
                return redirect("http://animationdoctorstudio.net/other-projects/maximilian/webinterface")
            else:
                encrypted_password = encrypt_password(password, username, False)
                row = dbinst.retrieve("maximilian", "passwords", "encrypted_password", encrypted_password, "encrypted_password", False)
                if check_encrypted_password(password, row):
                    resp.set_cookie('token', token)
                return resp    
    except Exception as e:
        print(e)
if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)