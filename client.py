"""
client.py

Connects to a Battleship server which runs the single-player game.
Simply pipes user input to the server, and prints all server responses.

TODO: Fix the message synchronization issue using concurrency (Tier 1, item 1).
"""

import socket

import multiprocessing
import platform
if platform.system() == "Darwin":
            multiprocessing.set_start_method("fork") 


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
# import threading


import communication
import json
import time
import threading







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
            line = rfile.readline().strip()
            
            #check if the connection is broken
            if not line:
                print(f"Player {player.address} disconnected")
                running = False
                break
            
            history_in.append(line)
        else:
            break




def main():

    global running
    running = True

    global history_in
    history_in = []

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
                
            time.sleep(0.5)
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

        

if __name__ == "__main__":
    main()

