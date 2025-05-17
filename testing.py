import json


this = "this"
newline = "\n"


dictionary = {
            "to_socket" : this+this+newline+this,
            "from_socket" : "me",
            "message" : "MESSAGE BFJBSALBJFBJAKLWBFJKASBFJK(end)"
            "(begin)nsakldnjndjklsa(end)"
            "(begin)asndjkasndjlkankasmdkas(end)",
            "checksumhash" : "", #not using this yet
            "packet_id" : "" #not using this yet
        }

#print(json.dumps(dictionary, indent=4))
print(json.dumps(dictionary))


#print(this+this+newline+this)

thing = json.loads(json.dumps(dictionary, indent=4))
#print(thing)
#print(thing["to_socket"])