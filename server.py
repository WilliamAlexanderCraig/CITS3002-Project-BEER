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
from battleship import run_single_player_game_online


import battleship

import communication

import threading

#import multiprocessing
#import platform
#if platform.system() == "Darwin":
#            multiprocessing.set_start_method("fork") 

HOST = '127.0.0.1'
PORT = 8081 #port 5000 was taken on my pc for some reason

num_players = 2 # flag to see if there are two players with active connections

players = [] # list of all the Player class objects
player_threads = []


#Class to hold all data for each client 
class Client: #this is renamed from "Player"
    def __init__(self, from_socket, to_socket, address):
        #self.connection = connection
        
        self.from_socket = from_socket
        self.to_socket = to_socket

        self.communicator = communication.Communicator()
        self.communicator.set_run_when_new_packet(self.received_new_packet_from_client)
        self.address = address

        self.is_player = True # use this later when we have spectators and such
   
    def received_new_packet_from_client(self, packet):
        pass

    def set_rw_files(self,rfile,wfile):
        self.communicator.rfile = rfile
        self.communicator.wfile = wfile
        

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
    for player_connection in range(num_players):
        
        print(f"[INFO] Waiting for player {player_connection} connection")
        s.listen(1) # open for 1 availiable connection
        
        #wait until a player connects
        socket_to_client, client_addr = s.accept()
        newPlayer = Client(s, socket_to_client, client_addr) # make a new player object to store all the data about this connection
        
        print(f"[INFO] Client {player_connection} connected from {client_addr}")
        players.append(newPlayer)
        
        with socket_to_client:
            rfile = socket_to_client.makefile('r')
            wfile = socket_to_client.makefile('w')
            newPlayer.set_rw_files(rfile,wfile)
        
        
        
    #check that both players exist 
    if players[0] != None and players[1] != None:
        print(f"First Player = {players[0].address}")
        print(f"Second Player = {players[1].address}") 

def listen_for_player_messages(player):
#     """Continuously receive and display messages from the server"""
    running = True
    while running:
        line = player.rfile.readline()
        if not line:
            print(f"Player {player.address} disconnected")
            break
        print(line)



        

def main():

    ##################
    # Set up the socket and establish connections with clients
    ##################
    print("[INFO] Making Socket")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    setup(s)
    

    print("Begin game")

    player_1 = players[0]
    player_2 = players[1]

    player_1_history = []
    player_2_history = []

    player_1.communicator.start_listening_thread(player_1_history)
    player_2.communicator.start_listening_thread(player_2_history)
    print("active threads: " + str(threading.active_count()))

    battleship.run_dual_player_game_online(player_1,player_2)

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