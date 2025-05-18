"""
server.py

Serves a single-player Battleship session to one connected client.
Game logic is handled entirely on the server using battleship.py.
Client sends FIRE commands, and receives game feedback.

TODO: For Tier 1, item 1, you don't need to modify this file much. 
The core issue is in how the client handles incoming messages.
However, if you want to support multiple clients (i.e. progress through further Tiers), you'll need concurrency here too.
"""

import socket
import random
import time
import threading
import battleship
import json

#import multiprocessing
#import platform
#if platform.system() == "Darwin":
#            multiprocessing.set_start_method("fork") 

HOST = '127.0.0.1'
PORT = 8081 #port 5000 was taken on my pc for some reason

#players = [] # list of all the Player class objects
player_threads = []

connections = []


player_1 = None
player_2 = None


#Class to hold all data for each client 
class Client: #this is renamed from "Player"
    def __init__(self, connection, address, player_num):

        #IP address and port of the client 
        self.address = address
        self.connection = connection


        # player_num 
        #   If player_num = 0 then the player is not playing 
        #   If player_num = 1 then the player is playing and is player 1 
        #   If player_num = 2 then the player is playing and is player 2 
        self.player_num = player_num

        

    def set_rw_files(self,rfile,wfile):
        self.rfile = rfile
        self.wfile = wfile
        
    def set_board(self, BOARD):
        self.board = BOARD

    def set_moves(self, moves):
        self.moves = moves

def setup(s):

    ########
    # This function currently waits for exactly 2 connections and assumes that both connections are players 
    # later we will need to rewrite this to include the possibility of non-players (spectators)
    # this function will likely have to be rewritten to be threaded 
    ########


    #s stands for socket 
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    s.bind((HOST, PORT)) # creates a pseudo server on this address
        
    #loop to get connections
    # Get 2 connections 
    for player_connection in [1,2]:
        
        print(f"[INFO] Waiting for player {player_connection} connection")
        s.listen(1) # open for 1 availiable connection
        
        #wait until a player connects
        connection, client_addr = s.accept()
        newPlayer = Client(connection, client_addr, player_connection) # make a new player object to store all the data about this connection
        
        print(f"[INFO] Client {player_connection} connected from {client_addr}")
        connections.append(newPlayer)
        
        
        rfile = connection.makefile('r')
        wfile = connection.makefile('w')
        newPlayer.set_rw_files(rfile,wfile)

        if(newPlayer.rfile == None):
            print("BFIABLFKlABW HDILBAUILFBAWUI:FBAUWI")

        
        
    #check that both players exist 
    if player_1 != None and player_2 != None:
        print(f"First Player = {player_1.address}")
        print(f"Second Player = {player_2.address}") 

def listen_for_player_messages(client):
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
            line = client.rfile.readline().strip()
            
            #check if the connection is broken
            if not line:
                print(f"Player {client.address} disconnected")
                running = False
                break
            
            history_in.append(line)
    
        else:
            break



        

def main():
    # is the server running
    global running 
    running = True

    #history of all packets received by the server
    global history_in
    history_in = []

    #history of all packets sent by the server 
    history_out = []

    ##################
    # Set up the socket and establish connections with clients
    ##################
    print("[INFO] Making Socket")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    setup(s)
    

    print("Begin game")

    #check that rfile exists
    if connections[0] == None:
        print(f"Connections 0 doesnt exist")
        return
    
    if connections[0].rfile == None:
        print(f"Connections 0 rfile doesnt exist")
        return

    #create a listening thread for each player 
    #TODO make this a loop
    listen_thread_player_1 = threading.Thread(target=listen_for_player_messages, args=(connections[0],))
    listen_thread_player_2 = threading.Thread(target=listen_for_player_messages, args=(connections[1],))
    listen_thread_player_1.start()
    listen_thread_player_2.start()

    print("active threads: " + str(threading.active_count()))

    while True: 
        #if the server is still running 
        if running:
            time.sleep(0.5)

            print(f"Main server loop:  {time.time()}")
            print("\n")
            print("history_in: " + str(history_in))

            message = "bhflbashlbsajkldbjiasdno;"
            packet_dict = {
                "time" : time.time(),
                "message" : message,
                "checksum" : hash(time.time())
            }

            #"pack"  the packet into a json thing
            packed = json.dumps(packet_dict) + "\n"
            print("sent packet")
            connections[0].wfile.write(packed)
            connections[0].wfile.flush()
        
        
        
        else:
            break
            


    #battleship.run_dual_player_game_online(player_1,player_2)

    # Make a thread to listen for each player's incoming messages
    #player1_thread = threading.Thread(group=None, target=listen_for_player_messages, args=(players[0],))
    #player2_thread = threading.Thread(group=None, target=listen_for_player_messages, args=(players[1],))
    #player1_thread.start()
    #player2_thread.start()

    #print("active threads: " + str(threading.active_count()))

    

    


    

    

# HINT: For multiple clients, you'd need to:
# 1. Accept connections in a loop
# 2. Handle each client in a separate thread
# 3. Import threading and create a handle_client function

if __name__ == "__main__":
    main()