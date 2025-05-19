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

refresh_rate = 10

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

    global response_id

    global my_address_port

    while True:
        
        if running:
            #run 2 times per second 
            #I believe that the sleep call allows the threads to run at the same time 
            time.sleep(0.5 / refresh_rate)

            #read the line and strip() to remove any whitespace
            packet = rfile.readline().strip()
            
            #check if the connection is broken
            if not packet:
                print(f"Server disconnected")
                running = False
                break
            
            #"unpack" the packet
            dict_packet = json.loads(packet)

            #append the packet (dictionary) to the history
            history_in.append(dict_packet)

            #print message of the new packet to the terminal
            print(f"[Server]: {dict_packet['message']} \n")

            #set the port 
            my_address_port = dict_packet["to_addr"]
            
            #if the new packet is waiting for a response, set the response_id
            if dict_packet["response_id"] != False:
                response_id = dict_packet["response_id"]
        else:
            break

def send_message_to_server(wfile, message):
        global my_address_port
        global response_id

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

    global response_id
    response_id = False

    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    print("Connecting to server...")
    server.connect((HOST, PORT))
    #print("Successfully connected to server...")
    #print("Waiting for other player to connect...")

    rfile = server.makefile('r')
    wfile = server.makefile('w')
    
    

    thread = threading.Thread(target=listen_for_server_messages, args=(rfile,))
    thread.start()

    
    
    while True:
        
        if running:
                
            time.sleep(0.1 / refresh_rate)

            response = input("")
            print(f"Sending to server: {response}" )
            
            send_message_to_server(wfile,response)


        else:
            break
            
            

        

if __name__ == "__main__":
    main()

