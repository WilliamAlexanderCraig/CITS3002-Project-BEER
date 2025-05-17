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



import threading

HOST = '127.0.0.1'
PORT = 8081 #port 5000 was taken on my pc for some reason

num_players = 2 # flag to see if there are two players with active connections

players = [] # list of all the Player class objects
player_threads = []


#Class to hold all data for each player
class Player:
    def __init__(self, connection, address):
        self.connection = connection
        self.address = address
        #self.game_state = "WAITING"
    
    def set_files(self, rfile, wfile):
        self.rfile = rfile
        self.wfile = wfile

    def set_board(self, BOARD):
        self.board = BOARD

    def set_moves(self, moves):
        self.moves = moves

def setup(s):
    #s stands for socket 
    print(f"[INFO] Server listening on {HOST}:{PORT}")
    s.bind((HOST, PORT)) # creates a pseudo server on this address
        
    #loop to get connections 
    for player_connection in range(num_players):
        
        print(f"[INFO] Waiting for player {player_connection} connection")
        s.listen(1) # open for 1 availiable connection
        
        #wait until a player connects
        conn, addr = s.accept()
        newPlayer = Player(conn, addr) # make a new player object to store all the data about this connection
        
        print(f"[INFO] Client {player_connection} connected from {addr}")
        players.append(newPlayer)
        
        with conn:
            rfile = conn.makefile('r')
            wfile = conn.makefile('w')
            newPlayer.set_files(rfile,wfile)
        
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


    # Make a thread to listen for each player's incoming messages
    player1_thread = threading.Thread(group=None, target=listen_for_player_messages, args=(players[0],))
    player2_thread = threading.Thread(group=None, target=listen_for_player_messages, args=(players[1],))

    
    player1_thread.start()
    player2_thread.start()

    print("active threads: " + str(threading.active_count()))

    

    battleship.run_dual_player_game_online(players[0],players[1])


    

    

# HINT: For multiple clients, you'd need to:
# 1. Accept connections in a loop
# 2. Handle each client in a separate thread
# 3. Import threading and create a handle_client function

if __name__ == "__main__":
    main()