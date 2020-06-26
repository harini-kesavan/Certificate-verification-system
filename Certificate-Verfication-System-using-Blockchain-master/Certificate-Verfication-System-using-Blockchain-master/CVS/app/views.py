import datetime
import json
import requests
import pyrebase
from flask import render_template, redirect, request
from app import app
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP
import binascii
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import db

if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_SA.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://cvs-blockchain.firebaseio.com/'
    })
# The node with which our application interacts, there can be multiple
# such nodes as well.
CONNECTED_NODE_ADDRESS = "http://127.0.0.1:8000"

config = {
    "apiKey": "AIzaSyC2eJyeyWARXyEZQrfTuy0eI0-sjuPVmTQ",
    "authDomain": "cvs-blockchain.firebaseapp.com",
    "databaseURL": "https://cvs-blockchain.firebaseio.com",
    "projectId": "cvs-blockchain",
    "storageBucket": "cvs-blockchain.appspot.com",
    "messagingSenderId": "918062606882",
    "appId": "1:918062606882:web:090324c027f0e07ed2787b",
    "measurementId": "G-YYFQMFBN9V"
}

firebase = pyrebase.initialize_app(config)
auth = firebase.auth()


@app.route('/', methods=['GET', 'POST'])
def basic():
    if request.method == 'POST':
        email = request.form['name']
        password = request.form['pass']
        try:
            auth.sign_in_with_email_and_password(email, password)
            app_ref = db.reference('/users')
            for user in app_ref.get():
                if user['email'] == email:
                    if user['auth'] == 'UN':
                        return redirect('/home')
                    if user['auth'] == 'CM':
                        return redirect('/company')
            return 'wrong credentials'
        except:
            return 'wrong credentials'
    return render_template('login.html', title='Certificate Verification System',
                           title2='New Certificate')


if __name__ == '__main__':
    app.run(debug=true)

# a post(arr) to store all the post got from the Blockchain
posts = []

# gets the whole chain from localhost:8000/chain api.


def fetch_posts():
    get_chain_address = "{}/chain".format(CONNECTED_NODE_ADDRESS)
    response = requests.get(get_chain_address)

    # if the request is Success proceed further.
    if response.status_code == 200:
        content = []
        # get the json content from api and use the values-Keys.
        chain = json.loads(response.content)
        for block in chain["chain"]:
            for tx in block["transactions"]:
                tx["index"] = block["index"]
                tx["hash"] = block["previous_hash"]
                content.append(tx)

        global posts
        posts = sorted(content, key=lambda k: k['timestamp'],
                       reverse=True)


@app.route('/home')
def index():
    fetch_posts()
    return render_template('index.html',
                           title='Certificate Verification System',
                           title2='New Certificate',
                           posts=posts,
                           node_address=CONNECTED_NODE_ADDRESS,
                           readable_time=timestamp_to_string)


@app.route('/company')
def company():
    return render_template('company.html',
                           title='Certificate Verification System',
                           title2='Verify Certificate')


@app.route('/submit', methods=['POST'])
def submit_textarea():

    #  get content and author from the site via the request.
    name = request.form["nameTV"]
    batch = request.form["batchTV"]
    dept = request.form["deptTV"]
    cgpa = request.form["cgpaTV"]
    author = request.form["authorTV"]
    email = request.form["emailTV"]
    rollno = request.form["rollnoTV"]

# create the post object to add to the transaction.
    post_object = {
        'author': author,
        'name': name,
        'batch': batch,
        'dept': dept,
        'cgpa': cgpa,
        'email': email,
        'rollno': rollno
    }

# Submit a transaction
    new_tx_address = "{}/new_transaction".format(CONNECTED_NODE_ADDRESS)

    requests.post(new_tx_address,
                  json=post_object,
                  headers={'Content-type': 'application/json'})

    return redirect('/home')


@app.route('/get_certificate', methods=['POST'])
def get_certificate():

    #  get content and author from the site via the request.
    rollno = request.form["rollnoTV"]

    # Query details
    app_chain_ref = db.reference('/application/chain')
    app_length_ref = db.reference('/application/length')
    len_check = app_length_ref.get()
    # Initializing the blockchain from the data base;
    for x in range(len_check):
        if x != 0:
            temp_block = app_chain_ref.get()[x]['transactions']
            block = temp_block[0]
            if block['rollno'] == rollno:
                print("BLOCK *****\n\n", block)
                post_object = {
                    'author': block['author'],
                    'name': block['name'],
                    'batch': block['batch'],
                    'dept': block['dept'],
                    'cgpa': block['cgpa'],
                    'email': block['email'],
                    'rollno': block['rollno']
                }
                return render_template('certificate.html',
                                       title='Certificate Verification System',
                                       title2='Student Certificate',
                                       posts=post_object)
    return "WRONG CREDENTIALS"


def timestamp_to_string(epoch_time):
    return datetime.datetime.fromtimestamp(epoch_time).strftime('%H:%M')

# @app.route('/rsa', methods=['GET','POST'])
# def rsa():
#     return render_template('rsaget.html', title='Certificate Verification System',
#                            title2='New Certificate')
#
#
# @app.route('/rsaget', methods=['GET','POST'])
# def rsaget():
#
#     name = request.form['name']
#     keyPair = RSA.generate(3072)
#     pubKey = keyPair.publickey()
#     print(f"Public key:\n\n (n={pubKey})\n\n")
#     print(f"Key Pair:\n\n (n={keyPair})\n\n")
#     pubKeyPEM = pubKey.exportKey()
#     print(pubKeyPEM.decode('ascii'))
#     # print(f"Private key: (n={hex(pubKey.n)}, d={hex(keyPair.d)})")
#     privKeyPEM = keyPair.exportKey()
#     print(privKeyPEM.decode('ascii'))
#     msg = b'A message for encryption'
#     encryptor = PKCS1_OAEP.new(pubKey)
#     encrypted = encryptor.encrypt(msg)
#     print("Encrypted:", binascii.hexlify(encrypted))
#     finalencrypted = binascii.hexlify(encrypted)
#     return render_template('rsaget.html', title='Certificate Verification System',
#                            title2='New Certificate', name=name, rsakey=finalencrypted)
