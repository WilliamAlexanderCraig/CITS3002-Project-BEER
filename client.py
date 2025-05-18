"""
client.py

Connects to a Battleship server which runs the single-player game.
Simply pipes user input to the server, and prints all server responses.

TODO: Fix the message synchronization issue using concurrency (Tier 1, item 1).
"""

import socket
import json
import time
import threading


HOST = '127.0.0.1'
PORT = 8081

# HINT: The current problem is that the client is reading from the socket,
# then waiting for user input, then reading again. This causes server
# messages to appear out of order.
#
# Consider using Python's threading module to separate the concerns:
# - One thread continuously reads from the socket and displays messages
# - The main thread handles user input and sends it to the server
#





def listen_for_server_messages(rfile):
#     """Continuously receive and display messages from the server"""
    #reference to the global running variable
    global running 
    #reference to the global history_in variable
    global history_in

    while True:

        if running:
            #run 2 times per second 
            #I believe that the sleep call allows the threads to run at the same time 
            time.sleep(0.5)

            #read the line and strip() to remove any whitespace
            packet = rfile.readline().strip()
            
            #check if the connection is broken
            if not packet:
                print(f"Server disconnected")
                running = False
                break
            
            dict_packet = json.loads(packet)

            history_in.append(dict_packet)
        else:
            break

def send_message_to_server(wfile, message, response_id):
        global my_address

        packet_dict = {
            "time" : time.time(),
            "message" : message,
            "checksum" : hash(time.time()),
            "to_addr" : "127.0.0.1:8081",
            "from_addr" : my_address_port,
            "read" : False,
            "response_id" : response_id
        }

        #"pack"  the packet into a json thing
        packed = json.dumps(packet_dict) + "\n"

        print(f"sent packet to Server")
        wfile.write(packed)
        wfile.flush()

def main():

    global running
    running = True

    global history_in
    history_in = []

    global my_address_port
    my_address_port = None

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    print("Connecting to server...")
    server.connect((HOST, PORT))
    print("Successfully connected to server...")
    print("Waiting for other player to connect...")

    rfile = server.makefile('r')
    wfile = server.makefile('w')
    
    

    thread = threading.Thread(target=listen_for_server_messages, args=(rfile,))
    thread.start()

    
    
    while True:
            
        if running:
                
            time.sleep(0.1)
            
            if len(history_in) != 0:
                
                #read the most recent message from the server (if it hasnt been read )
                recent_packet = history_in[-1] 
                if recent_packet["read"] != True:
                    print("[Server]: " + str(recent_packet["message"]))
                    recent_packet["read"] = True
                    my_address_port = recent_packet["to_addr"]

                    if recent_packet["response_id"] != False:
                        
                        response_id = recent_packet["response_id"]
                        response = input(">>")
                        print("Sending to server: " + response)
                        print("response_id: " + str(response_id))
                        send_message_to_server(wfile,response, response_id)

            

        else:
            break
            
            
            '''
            print("\n\n")
            print(f"Main client thread: {time.time()}")
            print("\n")
            print(history_in)

            message = "message to server;"
            packet_dict = {
                "time" : time.time(),
                "message" : message,
                "checksum" : hash(time.time())
            }

            #"pack"  the packet into a json thing
            packed = json.dumps(packet_dict) + "\n"
            print("sent packet to Server ")
            wfile.write(packed)
            wfile.flush()
            '''
            

        

if __name__ == "__main__":
    main()

