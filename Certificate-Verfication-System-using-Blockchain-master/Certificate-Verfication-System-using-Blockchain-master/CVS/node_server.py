from hashlib import sha256
import json
import time
import firebase_admin
from firebase_admin import credentials
from firebase_admin import firestore
from firebase_admin import db
import datetime

from flask import Flask, request
import requests
if not firebase_admin._apps:
    cred = credentials.Certificate("firebase_SA.json")
    firebase_admin.initialize_app(cred, {
        'databaseURL': 'https://cvs-blockchain.firebaseio.com/'
    })

class Block:
    # creating a block in the blockchain with some attributes
    def __init__(self, index, transactions, timestamp, previous_hash, nonce=0):
        self.index = index
        self.transactions = transactions
        self.timestamp = timestamp
        self.previous_hash = previous_hash
        self.nonce = nonce

# computing hash to block by considering the entire block
# RETURNS : Hash value
    def compute_hash(self):
        # dumps() method convert a python object(dictionary type) to a json
        block_string = json.dumps(self.__dict__, sort_keys=True)
        return sha256(block_string.encode()).hexdigest()


class Blockchain:
    # difficulty of our PoW algorithm
    difficulty = 2

    # Initiating a Blochian with a chain and a transaction to store un-mined transactions.
    def __init__(self):
        self.unconfirmed_transactions = []
        self.chain = []

# creating the genesis block of the chain
# RETURNS : null (but creates genesis block)
    def create_genesis_block(self):
        genesis_block = Block(0, [], 0, "0")
        genesis_block.hash = genesis_block.compute_hash()
        self.chain.append(genesis_block)

# getting the last block from the blockchain
# RETURNS : get the single last block from  chain.
    @property
    def last_block(self):
        return self.chain[-1]

# adding a new block to the chain
# RETURNS : Success-state (but adds to chain if true)
    def add_block(self, block, proof):
        previous_hash = self.last_block.hash

        # verifies whether the blocks-pre_hash and the actual previous_hash are same
        if previous_hash != block.previous_hash:
            return False

        # some of these are removed by Ezhil.
        # verifies whether the hash starts with n number of "0's"
        # also verifies whether proof and actual hash value are same.
        # if everything is good sets proof as the blocks hash and adds to chain
        # if not Blockchain.is_valid_proof(block, proof):
        block.hash = proof

        self.chain.append(block)
        chain_data = []
        for block in self.chain:
            chain_data.append(block.__dict__)
        print("chain = ", chain_data)
        applicationref = db.reference('/application')
        applicationref.set({
            'length': len(chain_data),
            "chain": chain_data,
            "peers": list(peers)
        })
        # return json.dumps({"length": len(chain_data),
        #                    "chain": chain_data,
        #                    "peers": list(peers)})
        return True

# alters our manual variable nonce until a hash that satisfies our difficulty criteria.
# RETURNS : the computed_hash (that satisfies our difficulty criteria )
    @staticmethod
    def proof_of_work(block):
        block.nonce = 0

        computed_hash = block.compute_hash()
        while not computed_hash.startswith('0' * Blockchain.difficulty):
            block.nonce += 1
            computed_hash = block.compute_hash()

        return computed_hash

# adds new un-mined transaction to the unconfirmed_transactions
# RETURNS : null but adds to unconfirmed_trans.
    def add_new_transaction(self, transaction):
        self.unconfirmed_transactions.append(transaction)

# verifies whether the hash starts with n number of "0's"
# also verifies whether proof and actual hash value are same.
# here block_hash is nothing but proof.add_new_transaction
# RETURNS : true (when both satisfied) or false
    @classmethod
    def is_valid_proof(cls, block, block_hash):
        """
        Check if block_hash is valid hash of block and satisfies
        the difficulty criteria.
        """
        return (block_hash.startswith('0' * Blockchain.difficulty) and
                block_hash == block.compute_hash())

# remove the hash field to recompute the hash again
# using `compute_hash` method.
# RETURNS : true  or false
    @classmethod
    def check_chain_validity(cls, chain):
        result = True
        previous_hash = "0"

        for block in chain:
            block_hash = block.hash
            delattr(block, "hash")
            if not cls.is_valid_proof(block, block_hash) or \
                    previous_hash != block.previous_hash:
                result = False
                break
            block.hash, previous_hash = block_hash, block_hash

        return result

# mine adds any unconfirmed_transactions left to the chain.
# RETURNS : true if added / false if there is no unconfirmed_trans
    def mine(self):
        if not self.unconfirmed_transactions:
            return False

        last_block = self.last_block

        new_block = Block(index=last_block.index + 1,
                          transactions=self.unconfirmed_transactions,
                          timestamp=time.time(),
                          previous_hash=last_block.hash)

        proof = self.proof_of_work(new_block)
        print(proof)
        value = self.add_block(new_block, proof)
        print("value : ", value)
        self.unconfirmed_transactions = []

        return True


app = Flask(__name__)

# the node's copy of blockchain
blockchain = Blockchain()
# blockchain.create_genesis_block()
app_get_ref = db.reference('/application/chain')
app_ref = db.reference('/application/length')
len_check = app_ref.get()
#Initializing the blockchain from the data base;
if len_check == 0 or len_check is None:
    blockchain.create_genesis_block()
else:
    for x in range(len_check):
        if x==0:
            block = Block(x,
                          [],
                          app_get_ref.get()[x]['timestamp'],
                          app_get_ref.get()[x]['previous_hash'],
                          app_get_ref.get()[x]['nonce'])
            block.hash = app_get_ref.get()[x]['hash']
        else:
            block = Block(x,
                          app_get_ref.get()[x]['transactions'],
                          app_get_ref.get()[x]['timestamp'],
                          app_get_ref.get()[x]['previous_hash'],
                          app_get_ref.get()[x]['nonce'])
            block.hash = app_get_ref.get()[x]['hash']
        blockchain.chain.append(block)

# the address to other participating members of the network
peers = set()


# Called by the submit button.
# it gets the json sent from the submit api
@app.route('/new_transaction', methods=['POST'])
def new_transaction():
    tx_data = request.get_json()
    required_fields = ["author", "name", "dept", "batch", "cgpa","email","rollno"]

    for field in required_fields:
        if not tx_data.get(field):
            return "Invalid transaction data", 404

    tx_data["timestamp"] = time.time()
    tx_data["student_verify"] = 0
    tx_data["university_verify"] = 0
    blockchain.add_new_transaction(tx_data)

    return "Success", 201


# Called by the fetch method from views.property
# displays all the blocks from the chain
@app.route('/chain', methods=['GET'])
def get_chain():
    chain_data = []
    for block in blockchain.chain:
        chain_data.append(block.__dict__)
    return json.dumps({"length": len(chain_data),
                       "chain": chain_data,
                       "peers": list(peers)})


# 1.first called.
# Used to mine the Unconfirmed_transaction
@app.route('/mine', methods=['GET'])
def mine_unconfirmed_transactions():
    result = blockchain.mine()
    if not result:
        return "No transactions to mine"
    else:
        print(result)
        chain_length = len(blockchain.chain)
        consensus()
        if chain_length == len(blockchain.chain):
            # announce the recently mined block to the network
            announce_new_block(blockchain.last_block)
        return "Block #{} is mined.".format(blockchain.last_block.index)


# To add a new peer to the system.
@app.route('/register_node', methods=['POST'])
def register_new_peers():
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    # Add the node to the peer list
    peers.add(node_address)

    # Return the consensus blockchain to the newly registered node
    # so that he can sync
    return get_chain()


@app.route('/register_with', methods=['POST'])
def register_with_existing_node():
    """
    Internally calls the `register_node` endpoint to
    register current node with the node specified in the
    request, and sync the blockchain as well as peer data.
    """
    node_address = request.get_json()["node_address"]
    if not node_address:
        return "Invalid data", 400

    data = {"node_address": request.host_url}
    headers = {'Content-Type': "application/json"}

    # Make a request to register with remote node and obtain information
    response = requests.post(node_address + "/register_node",
                             data=json.dumps(data), headers=headers)

    if response.status_code == 200:
        global blockchain
        global peers
        # update chain and the peers
        chain_dump = response.json()['chain']
        blockchain = create_chain_from_dump(chain_dump)
        peers.update(response.json()['peers'])
        return "Registration successful", 200
    else:
        # if something goes wrong, pass it on to the API response
        return response.content, response.status_code


def create_chain_from_dump(chain_dump):
    generated_blockchain = Blockchain()
    generated_blockchain.create_genesis_block()
    for idx, block_data in enumerate(chain_dump):
        if idx == 0:
            continue  # skip genesis block
        block = Block(block_data["index"],
                      block_data["transactions"],
                      block_data["timestamp"],
                      block_data["previous_hash"],
                      block_data["nonce"])
        proof = block_data['hash']
        added = generated_blockchain.add_block(block, proof)
        if not added:
            raise Exception("The chain dump is tampered!!")
    return generated_blockchain


# endpoint to add a block mined by someone else to
# the node's chain. The block is first verified by the node
# and then added to the chain.
@app.route('/add_block', methods=['POST'])
def verify_and_add_block():
    block_data = request.get_json()
    block = Block(block_data["index"],
                  block_data["transactions"],
                  block_data["timestamp"],
                  block_data["previous_hash"],
                  block_data["nonce"])

    proof = block_data['hash']
    added = blockchain.add_block(block, proof)

    if not added:
        return "The block was discarded by the node", 400

    return "Block added to the chain", 201


# to get the unconfirmed_transaction if they are not yet mined.
@app.route('/pending_tx')
def get_pending_tx():
    return json.dumps(blockchain.unconfirmed_transactions)

# to find the longest blockchain from the peers networks.


def consensus():
    global blockchain
    longest_chain = None
    current_len = len(blockchain.chain)

    for node in peers:
        response = requests.get('{}chain'.format(node))
        length = response.json()['length']
        chain = response.json()['chain']
        if length > current_len and blockchain.check_chain_validity(chain):
            current_len = length
            longest_chain = chain

    if longest_chain:
        blockchain = longest_chain
        return True

    return False


def announce_new_block(block):
    """
    A function to announce to the network once a block has been mined.
    Other blocks can simply verify the proof of work and add it to their
    respective chains.
    """
    for peer in peers:
        url = "{}add_block".format(peer)
        headers = {'Content-Type': "application/json"}
        requests.post(url,
                      data=json.dumps(block.__dict__, sort_keys=True),
                      headers=headers)


# Uncomment this line if you want to specify the port number in the code
app.run(debug=True, port=8000)
