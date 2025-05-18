import json
from base64 import b64encode
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad
from conversation_tree_analysis import check_json_file


with open("config.json","r") as fp:
    config = json.load(fp)

PATH = config["path"]
PASSWORD = config["password"]
START_NODE = config["start_node"]
END_NODE = config["end_node"]
LOADING_MESSAGES = config["loading_messages"]
SHUTDOWN_MESSAGES = config["shutdown_messages"]




def hash_tree(plaintext_nodes):
    plaintext_nodes_hashed = {}
    for key in plaintext_nodes.keys():
        hashed_key = SHA256.new(data=key.encode()).hexdigest()
        this_node = plaintext_nodes[key]
        plaintext_nodes_hashed[hashed_key] = this_node
        hashed_options = [
            {
                "text": option["text"],
                "goto": SHA256.new(data=option["goto"].encode()).hexdigest()
            }
            for option in this_node["options"]
        ]
        plaintext_nodes_hashed[hashed_key]["options"] = hashed_options
    return plaintext_nodes_hashed


def encrypt_aes(text):
    key = SHA256.new(PASSWORD.encode()).digest()
    iv = get_random_bytes(16)
    cipher = AES.new(key, AES.MODE_CBC, iv)
    ct_bytes = cipher.encrypt(pad(text.encode(), AES.block_size))
    return b64encode(iv + ct_bytes).decode()


def encrypt_flat_tree(tree):
    encrypted_tree = {}
    for tag, node in tree.items():
        enc_node = {
            "text": encrypt_aes(json.dumps(node["text"])),
            "options": []
        }
        for option in node.get("options", []):
            enc_node["options"].append({
                "text": encrypt_aes(option["text"]),
                "goto": encrypt_aes(option["goto"])
            })
        encrypted_tree[tag] = enc_node
    return encrypted_tree


def encrypt_conversation(plaintext_nodes):
    hashed_nodes = hash_tree(plaintext_nodes)
    encrypted_tree = encrypt_flat_tree(hashed_nodes)
    return encrypted_tree


with open(PATH, "r") as fp:
    plaintext_nodes = json.load(fp)


with open(LOADING_MESSAGES,"r") as fp:
    loading_messages = json.load(fp)

with open(SHUTDOWN_MESSAGES,"r") as fp:
    shutdown_messages = json.load(fp)


encrypted_tree = encrypt_conversation(plaintext_nodes)
encrypted_tree_string = json.dumps(encrypted_tree,sort_keys=True)

inlay = {
    "enc_loading_messages": encrypt_aes(json.dumps(loading_messages)),
    "encrypted_tree_string": encrypted_tree_string,
    "start_node_enc": encrypt_aes(SHA256.new(data=START_NODE.encode()).hexdigest()),
    "end_node": SHA256.new(data=END_NODE.encode()).hexdigest(),
    "end_node_enc": encrypt_aes(SHA256.new(data=END_NODE.encode()).hexdigest()),
    "enc_shutdown_messages": encrypt_aes(json.dumps(shutdown_messages)),
}

with open("carol-template.html","r",encoding="utf-8") as fp:
    template = fp.read()

html_code = template.format(**inlay)

check_json_file(PATH,START_NODE,END_NODE)

with open("carol.html", "w", encoding="utf-8") as f:
    f.write(html_code)


print("Written")