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
import json



HOST = '127.0.0.1'
PORT = 8081 #port 5000 was taken on my pc for some reason


time_out_wait_time = 20 #seconds

refresh_rate = 1 






##############
#Battleships stuff
#############
testing = True
BOARD_SIZE = 10
SHIPS = []
if testing:
    SHIPS = [("Dinghy",1)]
else:
    SHIPS = [
        ("Carrier", 5),
        ("Battleship", 4),
        ("Cruiser", 3),
        ("Submarine", 3),
        ("Destroyer", 2)
    ]

class Board:
    """
    Represents a single Battleship board with hidden ships.
    We store:
      - self.hidden_grid: tracks real positions of ships ('S'), hits ('X'), misses ('o')
      - self.display_grid: the version we show to the player ('.' for unknown, 'X' for hits, 'o' for misses)
      - self.placed_ships: a list of dicts, each dict with:
          {
             'name': <ship_name>,
             'positions': set of (r, c),
          }
        used to determine when a specific ship has been fully sunk.

    In a full 2-player networked game:
      - Each player has their own Board instance.
      - When a player fires at their opponent, the server calls
        opponent_board.fire_at(...) and sends back the result.
    """

    def __init__(self, size=BOARD_SIZE):
        self.size = size
        # '.' for empty water
        self.hidden_grid = [['.' for _ in range(size)] for _ in range(size)]
        # display_grid is what the player or an observer sees (no 'S')
        self.display_grid = [['.' for _ in range(size)] for _ in range(size)]
        self.placed_ships = []  # e.g. [{'name': 'Destroyer', 'positions': {(r, c), ...}}, ...]

    def place_ships_randomly(self, ships=SHIPS):
        """
        Randomly place each ship in 'ships' on the hidden_grid, storing positions for each ship.
        In a networked version, you might parse explicit placements from a player's commands
        (e.g. "PLACE A1 H BATTLESHIP") or prompt the user for board coordinates and placement orientations; 
        the self.place_ships_manually() can be used as a guide.
        """
        for ship_name, ship_size in ships:
            placed = False
            while not placed:
                orientation = random.randint(0, 1)  # 0 => horizontal, 1 => vertical
                row = random.randint(0, self.size - 1)
                col = random.randint(0, self.size - 1)

                if self.can_place_ship(row, col, ship_size, orientation):
                    occupied_positions = self.do_place_ship(row, col, ship_size, orientation)
                    self.placed_ships.append({
                        'name': ship_name,
                        'positions': occupied_positions
                    })
                    placed = True


    def place_ships_manually(self, client, ships=SHIPS):
        """
        Prompt the user for each ship's starting coordinate and orientation (H or V).
        Validates the placement; if invalid, re-prompts.
        """
        global history_in
        global running
        global response_id_count


        client.send_packet_to_client("\nPlease place your ships manually on the board.", False)
        for ship_name, ship_size in ships:
            while True:

                time.sleep(1 * refresh_rate)
                #print board
                client.send_packet_to_client("\nThis is the state of your board", False)
                board_string = client.board.get_string_display_grid(True)
                client.send_packet_to_client(board_string, False)

                client.send_packet_to_client(f"\nPlacing your {ship_name} (size {ship_size}).", False)
                
                
                ## Blocks this thread here until gets a response 
                client.send_packet_to_client("  Enter starting coordinate (e.g. A1): ", response_id_count)
                coord_str = block_until_received_response(client,0)["message"]
                
                    
                #response_id_count += 1
            
                ## Blocks this thread here until gets a response 
                client.send_packet_to_client("  Orientation? Enter 'H' (horizontal) or 'V' (vertical): ", response_id_count)
                orientation_str = block_until_received_response(client,0)["message"]
                #response_id_count += 1

                
                try:
                    row, col, error_check = parse_coordinate(coord_str)
                except ValueError as e:
                    client.send_packet_to_client(f" [!] Invalid coordinate: {e}", False)
                    continue

                # Convert orientation_str to 0 (horizontal) or 1 (vertical)
                if orientation_str == 'H':
                    orientation = 0
                elif orientation_str == 'V':
                    orientation = 1
                else:
                    client.send_packet_to_client("  [!] Invalid orientation. Please enter 'H' or 'V'.", False)
                    continue

                # Check if we can place the ship
                if self.can_place_ship(row, col, ship_size, orientation):
                    occupied_positions = self.do_place_ship(row, col, ship_size, orientation)
                    self.placed_ships.append({
                        'name': ship_name,
                        'positions': occupied_positions
                    })
                    break
                else:
                    client.send_packet_to_client(f"  [!] Cannot place {ship_name} at {coord_str} (orientation={orientation_str}). Try again.", False)


    def can_place_ship(self, row, col, ship_size, orientation):
        """
        Check if we can place a ship of length 'ship_size' at (row, col)
        with the given orientation (0 => horizontal, 1 => vertical).
        Returns True if the space is free, False otherwise.
        """
        if orientation == 0:  # Horizontal
            if col + ship_size > self.size:
                return False
            for c in range(col, col + ship_size):
                if self.hidden_grid[row][c] != '.':
                    return False
        else:  # Vertical
            if row + ship_size > self.size:
                return False
            for r in range(row, row + ship_size):
                if self.hidden_grid[r][col] != '.':
                    return False
        return True

    def do_place_ship(self, row, col, ship_size, orientation):
        """
        Place the ship on hidden_grid by marking 'S', and return the set of occupied positions.
        """
        occupied = set()
        if orientation == 0:  # Horizontal
            for c in range(col, col + ship_size):
                self.hidden_grid[row][c] = 'S'
                occupied.add((row, c))
        else:  # Vertical
            for r in range(row, row + ship_size):
                self.hidden_grid[r][col] = 'S'
                occupied.add((r, col))
        return occupied

    def fire_at(self, row, col):
        """
        Fire at (row, col). Return a tuple (result, sunk_ship_name).
        Possible outcomes:
          - ('hit', None)          if it's a hit but not sunk
          - ('hit', <ship_name>)   if that shot causes the entire ship to sink
          - ('miss', None)         if no ship was there
          - ('already_shot', None) if that cell was already revealed as 'X' or 'o'

        The server can use this result to inform the firing player.
        """
        cell = self.hidden_grid[row][col]
        if cell == 'S':
            # Mark a hit
            self.hidden_grid[row][col] = 'X'
            self.display_grid[row][col] = 'X'
            # Check if that hit sank a ship
            sunk_ship_name = self._mark_hit_and_check_sunk(row, col)
            if sunk_ship_name:
                return ('hit', sunk_ship_name)  # A ship has just been sunk
            else:
                return ('hit', None)
        elif cell == '.':
            # Mark a miss
            self.hidden_grid[row][col] = 'o'
            self.display_grid[row][col] = 'o'
            return ('miss', None)
        elif cell == 'X' or cell == 'o':
            return ('already_shot', None)
        else:
            # In principle, this branch shouldn't happen if 'S', '.', 'X', 'o' are all possibilities
            return ('already_shot', None)

    def _mark_hit_and_check_sunk(self, row, col):
        """
        Remove (row, col) from the relevant ship's positions.
        If that ship's positions become empty, return the ship name (it's sunk).
        Otherwise return None.
        """
        for ship in self.placed_ships:
            if (row, col) in ship['positions']:
                ship['positions'].remove((row, col))
                if len(ship['positions']) == 0:
                    return ship['name']
                break
        return None

    def all_ships_sunk(self):
        """
        Check if all ships are sunk (i.e. every ship's positions are empty).
        """
        for ship in self.placed_ships:
            if len(ship['positions']) > 0:
                return False
        return True

    def print_display_grid(self, show_hidden_board=False):
        """
        Print the board as a 2D grid.
        
        If show_hidden_board is False (default), it prints the 'attacker' or 'observer' view:
        - '.' for unknown cells,
        - 'X' for known hits,
        - 'o' for known misses.
        
        If show_hidden_board is True, it prints the entire hidden grid:
        - 'S' for ships,
        - 'X' for hits,
        - 'o' for misses,
        - '.' for empty water.
        """
        # Decide which grid to print
        grid_to_print = self.hidden_grid if show_hidden_board else self.display_grid

        # Column headers (1 .. N)
        print("  " + "".join(str(i + 1).rjust(2) for i in range(self.size)))
        # Each row labeled with A, B, C, ...
        for r in range(self.size):
            row_label = chr(ord('A') + r)
            row_str = " ".join(grid_to_print[r][c] for c in range(self.size))
            print(f"{row_label:2} {row_str}")
    
    def get_string_display_grid(self, show_hidden_board=False):
        """
        Print the board as a 2D grid.
        
        If show_hidden_board is False (default), it prints the 'attacker' or 'observer' view:
        - '.' for unknown cells,
        - 'X' for known hits,
        - 'o' for known misses.
        
        If show_hidden_board is True, it prints the entire hidden grid:
        - 'S' for ships,
        - 'X' for hits,
        - 'o' for misses,
        - '.' for empty water.
        """
        # Decide which grid to print
        grid_to_print = self.hidden_grid if show_hidden_board else self.display_grid

        # Column headers (1 .. N) 
        response_string = "\n  " + "".join(str(i + 1).rjust(2) for i in range(self.size))
        response_string += "\n"
        # Each row labeled with A, B, C, ...
        for r in range(self.size):
            row_label = chr(ord('A') + r)
            row_str = " ".join(grid_to_print[r][c] for c in range(self.size))
            response_string += f"{row_label:2} {row_str}\n"
        
        return response_string


def parse_coordinate(coord_str):
    """
    Convert something like 'B5' into zero-based (row, col).
    Example: 'A1' => (0, 0), 'C10' => (2, 9)
    HINT: you might want to add additional input validation here...
    """
    coord_str = coord_str.strip().upper()
    row_letter = coord_str[0]
    col_digits = coord_str[1:]

    row = ord(row_letter) - ord('A')
    col = int(col_digits) - 1  # zero-based

    #andrew will change 

    error_check = "ALL GOOD"

    #if row > J then error_check == "ERROR"

    return row, col, error_check


##############
#END OF Battleships stuff
#############

#Class to hold state of game 
#container to hold all this information about a particular game
class GameState:
    def __init__(self):
        self.player_1 = None
        self.player_2 = None
        self.players = []
        self.current_player = None
        self.waiting_player = None
        self.successful_turn = False
        self.is_playing = False
    
    def set_player_1(self, player_1):
        self.player_1 = player_1
    
    def set_player_2(self, player_2):
        self.player_2 = player_2
    
    
    def set_players(self,players):
        self.players = players
    
    def set_current_and_waiting_player(self, current_player, waiting_player):
        self.current_player = current_player
        self.waiting_player = waiting_player
        self.players = [self.current_player, self.waiting_player]
    
    def set_successful_turn(self, successful_turn):
        self.successful_turn = successful_turn



#Class to hold all data for each client 
class Client: #this is renamed from "Player"
    def __init__(self, connection, address):

        #IP address and port of the client 
        self.address = address
        self.connection = connection
        self.port = str(address[1])
        self.moves = 0


        # player_num 
        #   If player_num = 0 then the player is not playing 
        #   If player_num = 1 then the player is playing and is player 1 
        #   If player_num = 2 then the player is playing and is player 2 
        self.player_name = ""
        self.board = None
        self.playing = False

    def set_name(self,name):
        self.player_name = name

    def set_board(self,board):
        self.board = board

    def set_rw_files(self,rfile,wfile):
        self.rfile = rfile
        self.wfile = wfile
        
    def set_board(self, BOARD):
        self.board = BOARD

    def add_move(self):
        self.moves += 1
    
    def send_packet_to_client(self, message, response_id):
        
        packet_dict = {
            "time" : time.time(),
            "message" : message,
            "checksum" : hash(time.time()),
            "to_addr" : self.port,
            "from_addr" : "8081",
            "read" : False,
            "response_id" : response_id
        }

        #"pack"  the packet into a json thing
        packed = json.dumps(packet_dict) + "\n"

        print(f"sent packet to {self.address}")
        self.wfile.write(packed)
        self.wfile.flush()


def play_game(game):
    global running
    global history_in
    global response_id_count

    #game.is_playing = True

    while True: 
        #if the server is still running 
        if running:
            time.sleep(0.01 * refresh_rate)

            #THIS IS THE GAME LOGIC IN HERE 
            
            game.successful_turn = False

            
            #send CURRENT PLAYERS board
            game.current_player.send_packet_to_client("\nThis is the state of your board", False)
            board_string = game.current_player.board.get_string_display_grid(True)
            game.current_player.send_packet_to_client(board_string, False)

            #send WAITING PLAYERS board
            game.current_player.send_packet_to_client("\nThis is the state of your opponents board", False)
            board_string = game.waiting_player.board.get_string_display_grid(False)
            game.current_player.send_packet_to_client(board_string, False)

            ## Blocks this thread here until gets a response 
            game.current_player.send_packet_to_client("\nEnter coordinate to fire at (e.g. B5):", response_id_count)
            guess = block_until_received_response(game.current_player,0)["message"]
            
        
            if guess.lower() == 'quit':
                
                game.current_player.send_packet_to_client("Thanks for playing. Goodbye.", False)
                #running = False
                #connections.remove(game.current_player)
                #game.current_player = None
                return "quit" , game.current_player
            
            try:
                row, col, error_check = parse_coordinate(guess)

                if error_check == "ERROR":
                    raise ValueError("Your coordinate was out of scope ")
                    


                result, sunk_name = game.waiting_player.board.fire_at(row, col)
                
                game.current_player.add_move()

                if result == 'hit':
                    if sunk_name:
                        game.current_player.send_packet_to_client(f"HIT! You sank the {sunk_name}!", False)
                        game.successful_turn = True 
                    else:
                        game.current_player.send_packet_to_client(f"HIT! ", False)
                        game.successful_turn = True 
                    if game.waiting_player.board.all_ships_sunk():
                        
                        board_string = game.waiting_player.board.get_string_display_grid(True) 
                        game.current_player.send_packet_to_client(board_string, False)

                        message = f"Congratulations! You sank all ships in {game.current_player.moves} moves."
                        game.current_player.send_packet_to_client(message, False)
                        
                        game.successful_turn = True 
                        return "win" , game.current_player
                    
                elif result == 'miss':
                    game.current_player.send_packet_to_client("MISS!", False)
                    
                    game.successful_turn = True 
                elif result == 'already_shot':
                    game.current_player.send_packet_to_client("You've already fired at that location.", False)
                    
                    game.successful_turn = False

            except ValueError as e:
                game.current_player.send_packet_to_client(f" Invalid input: {e}", False)
                game.successful_turn = False 

            if game.successful_turn: 
                if game.current_player == game.player_1:
                    game.set_current_and_waiting_player(game.player_2, game.player_1)
                else:
                    game.set_current_and_waiting_player(game.player_1, game.player_2)

            

            
        else:
            
            return "not_running" , None

def setup_game(game):
    global response_id_count

    #send welcome message
    message = "Welcome to Online Dual-Player Battleship! Try to sink all the ships. Type 'quit' to exit."
    game.current_player.send_packet_to_client(message, False)
    game.waiting_player.send_packet_to_client(message, False)
    
    #create boards for players
    game.current_player.set_board(Board(BOARD_SIZE))
    game.waiting_player.set_board(Board(BOARD_SIZE))

    for player in [game.current_player, game.waiting_player]:
        while True:

            #ask if the players want random or manual ship placement 
            player.send_packet_to_client("\nWould you like random or manual ship placement? Send R or M respectively", response_id_count)
            placement_mode = block_until_received_response(player,0)["message"]

            try:
                if placement_mode == "M":
                    player.board.place_ships_manually( player, SHIPS)
                    break
                elif placement_mode == "R":
                    player.board.place_ships_randomly( SHIPS)
                    break
                elif placement_mode == "QUIT":
                    return "QUIT"
                else:
                    raise ValueError("You didnt send 'R' or 'M', Try again :)'")
                
            except ValueError as e:
                player.send_packet_to_client(f" Invalid input: {e}", False)    

                            
#no longer used
def setup(s):

    ########
    # This function currently waits for exactly 2 connections and assumes that both connections are players 
    # later we will need to rewrite this to include the possibility of non-players (spectators)
    # this function will likely have to be rewritten to be threaded 
    ########


    
    '''
    while True:
        try:

             # creates a pseudo server on this address
            break
        except:
            print("didnt work, trying again in 5 seconds")
            time.sleep(5)
    '''
    
        
    #loop to get connections
    # Get 2 connections 
    for player_connection in [1,2]:
        
        print(f"[INFO] Waiting for player {player_connection} connection")
        s.listen(1) # open for 1 availiable connection
        
        #wait until a player connects
        connection, client_addr = s.accept()
        newPlayer = Client(connection, client_addr) # make a new player object to store all the data about this connection
        
        print(f"[INFO] Client {player_connection} connected from {client_addr}")
        
        #add this connection to the connections list
        connections.append(newPlayer)
        
        
        rfile = connection.makefile('r')
        wfile = connection.makefile('w')
        newPlayer.set_rw_files(rfile,wfile)
 

def listen_for_player_messages(client):
#     """Continuously receive and display messages from the server"""
    #reference to the global running variable
    global running 
    #reference to the global history_in variable
    global history_in

    while True:
        
        if running:
            time.sleep(0.5 * refresh_rate)
            
            #run 2 times per second 
            #I believe that the sleep call allows the threads to run at the same time 
            

            #read the line and strip() to remove any whitespace
            packet = client.rfile.readline().strip()
            
            #check if the connection is broken
            if not packet:
                print(f"Player {client.address} disconnected")
                #running = False
                break
            
            #unpacks the packet
            dict_packet = json.loads(packet)

            history_in.append(dict_packet)
            
            #print messages
            print(f"[{dict_packet['from_addr']}]: {dict_packet['message']}  (r_id: {dict_packet['response_id']}) ")
        
        else:
            break

#no longer used
def print_client_messages_to_console():
    global running
    global history_in
    
    while True:
        if running:

            time.sleep(0.1 * refresh_rate)
            if len(history_in) != 0:
                        
                #read the most recent message from the server (if it hasnt been read )
                recent_packet = history_in[-1] 
                if recent_packet["read"] != True:
                    from_addr = recent_packet["from_addr"]
                    print(f"[{from_addr}]: " + str(recent_packet["message"]))
                    recent_packet["read"] = True
        else:
            break


def block_until_received_response(client, extra_time):
    global running
    global history_in
    global response_id_count

    ############
    #acts as a "Block" to the current thread until we get a response from the user 
    
    start_time = time.perf_counter()
    

    while True:
        if running:
            time.sleep(1 * refresh_rate)
            
            #Timeout functionality
            if time.perf_counter() <= start_time + time_out_wait_time + extra_time:
                time_used = time.perf_counter() - start_time
                countdown = round(time_out_wait_time - time_used)
                
                if countdown in [5,3,2,1]:
                    client.send_packet_to_client(f"Countdown: {countdown}", False)

                #print("countdown : " + str(countdown))
            

                #check if any of the packets have the matching response id
                for packet in history_in:
                    if len(history_in)!= 0 and packet["response_id"] == response_id_count:
                        response_id_count += 1
                        return packet
            else:
                client.send_packet_to_client(f"You have forfeited your game due to inactivity :(", False)
                response_id_count += 1
                
                #make fake "quit" packet
                quit_packet = {
                    "message" : "QUIT",
                }
                        
                return quit_packet
        else:
            break
    ############
    
def listen_for_new_connections(socket):
    global running
    global response_id_count
    global connections
    
    while True:
        if running:
            time.sleep(0.5*refresh_rate) #change yeet

            socket.listen(1) # open for 1 availiable connection

            #wait until a player connects
            connection, client_addr = socket.accept()

            print(f"[INFO] New Client connected from {client_addr}")
            
            #set up new player object 
            newClient = Client(connection, client_addr)
            rfile = connection.makefile('r')
            wfile = connection.makefile('w')
            newClient.set_rw_files(rfile,wfile)

            #Ask player for their name
            #connections.append(newClient)
            newClient.send_packet_to_client("\n HELLO! Please send your name", response_id_count)
            packet = rfile.readline().strip()
            dict_packet = json.loads(packet)
            name = dict_packet["message"]
            print(name)
            newClient.send_packet_to_client(f"\n\n#####################\n\n WELCOME {name}\n YOU ARE IN THE WAITING ROOM \n\n#####################\n\n",False)
            #newClient.send_packet_to_client(f"\n\n#####################\n\n YOU ARE IN THE WAITING ROOM \n\n#####################\n\n",False)
            newClient.set_name(name)
            connections.append(newClient)

            listening_thread = threading.Thread(target=listen_for_player_messages, args=(newClient,))
            listening_thread.start()
            
            
        else:
            break


def waiting_room():

    global running
    global connections
    global game
    # Build out a message string, and then send to everyone in the waiting room every 5 seconds

    while True:

        print("WAITING ROOM ALIVE")
        print(f"game.is_playing : {game.is_playing}")

        if running:
            

            time.sleep(5*refresh_rate)

            message = ""

            for connection in connections:
                    if connection.playing == False:
                        message += str("\n\n#####################\n\n WAITING ROOM\n\n #####################\n\n")
                        message += str(f"\nPlayer 1 is {game.player_1.player_name}\n")
                        p1_board = str(game.player_1.board.get_string_display_grid(True)) #might need to be False KACHOW
                        message += str(f"\n {game.player_1.player_name}'s Board: \n\n {p1_board}\n")
                        message += str("\n\n #####################\n\n")
                        message += str(f"\nPlayer 2 is {game.player_2.player_name}\n")
                        p2_board = str(game.player_2.board.get_string_display_grid(True)) #might need to be False KACHOW
                        message += str(f"\n {game.player_2.player_name}'s Board: \n\n {p2_board}\n")
                        message += str("\n\n #####################\n\n")
                        message += str(f"Current turn : {game.current_player.player_name}")

                        connection.send_packet_to_client(message, False)

                
                    

        else:
            break
    



    pass
            

    


def main():
    # is the server running
    global running 
    running = True

    #history of all packets received by the server
    global history_in
    history_in = []
    
    global response_id_count
    response_id_count = 1

    global connections
    connections = []

    global waiting_room_list
    waiting_room_list = []

    global game
    game = GameState()

    #global connections
    #connections = []

    ##################
    # Set up the socket and establish connections with clients
    ##################
    print("[INFO] Making Socket")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM) 
    s.bind((HOST, PORT))
    
    listening_for_connections_thread = threading.Thread(target=listen_for_new_connections, args=(s,))
    listening_for_connections_thread.start()
    
    #listen_for_player_messages_thread = threading.Thread(target=listen_for_player_messages)
    #listen_for_player_messages_thread.start()

    waiting_room_thread = threading.Thread(target=waiting_room)
    waiting_room_thread.start()

    
    
    
    
    
    
    
    while True:

        if running:

            #global connections

            #wipe the gamestate
            game = GameState()
            
            print("waiting for at least 2 clients")
            print(f"Connections: {connections}")
            time.sleep(2)

            #check for at least 2 connections
            #if 0 connection
            if len(connections) == 0:
                print("No Clients connected")
                continue
                
            #if 1 connection
            if len(connections) == 1:
                message = "1 Client connected, waiting for at least 2 clients"
                print(message)
                connections[0].send_packet_to_client(message,False)
                continue
            
            #if exactly 2 players, then run game with 2 players
            if len(connections) == 2:
                message = "Exactly 2 players connected, Starting game with two players"
                print(message)
                connections[0].send_packet_to_client(message,False)
                connections[1].send_packet_to_client(message,False)
                
                #set up the game
                game.set_player_1(connections[0])
                game.set_player_2(connections[1])
                game.set_current_and_waiting_player(game.player_1, game.player_2)

                
                #play_game(game)

                game.is_playing = True
                game.player_1.playing = True
                game.player_2.playing = True
                if setup_game(game) == "QUIT":
                    #running = False
                    print("One of the players quit during the Setup Process")
                    game.player_1.playing = False
                    game.player_2.playing = False
                    continue
                
                play_game(game)
                game.is_playing = False
                game.player_1.playing = False
                game.player_2.playing = False
                #result, current_player = play_game(game)
                '''
                if result == "win":
                    for player in game.players:
                        if player == current_player:
                            player.send_packet_to_client("You Win :)", None)
                        else:
                            player.send_packet_to_client("You Lost :(", None)
                
                elif result == "quit":
                    for player in game.players:
                        if player == current_player:
                            player.send_packet_to_client("You Lost :(", None)
                        else:
                            player.send_packet_to_client("You Win :)", None)
                '''
                

            #Have some mechanism to choose the players 
            if len(connections) >= 2:

                #choose 2 random players from the waiting room
                temp = []
                for connection in connections:
                    temp.append(connection)

                p1 = random.choice(temp)
                temp.remove(p1)
                p2 = random.choice(temp)

                message = "More than 2 Clients connected, selecting 2 random clients to play"
                print(message)
                for client in connections:
                    client.send_packet_to_client(message,False)
                    client.send_packet_to_client(f"Player 1: {p1.player_name}",False)
                    client.send_packet_to_client(f"Player 2: {p2.player_name}",False)
                
                #set up the game
                game.set_player_1(p1)
                game.set_player_2(p2)
                game.set_current_and_waiting_player(game.player_1, game.player_2)
                
                #play_game(game)


                if setup_game(game) == "QUIT":
                    #running = False
                    print("One of the players quit during the Setup Process")
                    continue
                

                play_game(game)


                
                

                


                
            

            
        else:
            break
    
        

    #running = False
    
    




# HINT: For multiple clients, you'd need to:
# 1. Accept connections in a loop
# 2. Handle each client in a separate thread
# 3. Import threading and create a handle_client function

if __name__ == "__main__":
    main()