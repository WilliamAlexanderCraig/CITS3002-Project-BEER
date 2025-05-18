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



HOST = '127.0.0.1'
PORT = 8081 #port 5000 was taken on my pc for some reason



connections = []


##############
#Battleships stuff
#############
BOARD_SIZE = 10
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


    def place_ships_manually(self, ships=SHIPS):
        """
        Prompt the user for each ship's starting coordinate and orientation (H or V).
        Validates the placement; if invalid, re-prompts.
        """
        print("\nPlease place your ships manually on the board.")
        for ship_name, ship_size in ships:
            while True:
                self.print_display_grid(show_hidden_board=True)
                print(f"\nPlacing your {ship_name} (size {ship_size}).")
                coord_str = input("  Enter starting coordinate (e.g. A1): ").strip()
                orientation_str = input("  Orientation? Enter 'H' (horizontal) or 'V' (vertical): ").strip().upper()

                try:
                    row, col = parse_coordinate(coord_str)
                except ValueError as e:
                    print(f"  [!] Invalid coordinate: {e}")
                    continue

                # Convert orientation_str to 0 (horizontal) or 1 (vertical)
                if orientation_str == 'H':
                    orientation = 0
                elif orientation_str == 'V':
                    orientation = 1
                else:
                    print("  [!] Invalid orientation. Please enter 'H' or 'V'.")
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
                    print(f"  [!] Cannot place {ship_name} at {coord_str} (orientation={orientation_str}). Try again.")


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

    return (row, col)


def run_single_player_game_locally():
    """
    A test harness for local single-player mode, demonstrating two approaches:
     1) place_ships_manually()
     2) place_ships_randomly()

    Then the player tries to sink them by firing coordinates.
    """
    board = Board(BOARD_SIZE)

    # Ask user how they'd like to place ships
    choice = input("Place ships manually (M) or randomly (R)? [M/R]: ").strip().upper()
    if choice == 'M':
        board.place_ships_manually(SHIPS)
    else:
        board.place_ships_randomly(SHIPS)

    print("\nNow try to sink all the ships!")
    moves = 0
    while True:
        board.print_display_grid()
        guess = input("\nEnter coordinate to fire at (or 'quit'): ").strip()
        if guess.lower() == 'quit':
            print("Thanks for playing. Exiting...")
            return

        try:
            row, col = parse_coordinate(guess)
            result, sunk_name = board.fire_at(row, col)
            moves += 1

            if result == 'hit':
                if sunk_name:
                    print(f"  >> HIT! You sank the {sunk_name}!")
                else:
                    print("  >> HIT!")
                if board.all_ships_sunk():
                    board.print_display_grid()
                    print(f"\nCongratulations! You sank all ships in {moves} moves.")
                    break
            elif result == 'miss':
                print("  >> MISS!")
            elif result == 'already_shot':
                print("  >> You've already fired at that location. Try again.")

        except ValueError as e:
            print("  >> Invalid input:", e)


def run_single_player_game_online(rfile, wfile):
    """
    A test harness for running the single-player game with I/O redirected to socket file objects.
    Expects:
      - rfile: file-like object to .readline() from client
      - wfile: file-like object to .write() back to client
    
    #####
    NOTE: This function is (intentionally) currently somewhat "broken", which will be evident if you try and play the game via server/client.
    You can use this as a starting point, or write your own.
    #####
    """
    def send(msg):
        wfile.write(msg + '\n')
        wfile.flush()

    def send_board(board):
        wfile.write("GRID\n")
        wfile.write("  " + " ".join(str(i + 1).rjust(2) for i in range(board.size)) + '\n')
        for r in range(board.size):
            row_label = chr(ord('A') + r)
            row_str = " ".join(board.display_grid[r][c] for c in range(board.size))
            wfile.write(f"{row_label:2} {row_str}\n")
        wfile.write('\n')
        wfile.flush()

    def recv():
        return rfile.readline().strip()

    board = Board(BOARD_SIZE)
    board.place_ships_randomly(SHIPS)

    send("Welcome to Online Single-Player Battleship! Try to sink all the ships. Type 'quit' to exit.")

    moves = 0
    while True:
        send_board(board)
        send("Enter coordinate to fire at (e.g. B5):")
        guess = recv()
        if guess.lower() == 'quit':
            send("Thanks for playing. Goodbye.")
            return

        try:
            row, col = parse_coordinate(guess)
            result, sunk_name = board.fire_at(row, col)
            moves += 1

            if result == 'hit':
                if sunk_name:
                    send(f"HIT! You sank the {sunk_name}!")
                else:
                    send("HIT!")
                if board.all_ships_sunk():
                    send_board(board)
                    send(f"Congratulations! You sank all ships in {moves} moves.")
                    return
            elif result == 'miss':
                send("MISS!")
            elif result == 'already_shot':
                send("You've already fired at that location.")
        except ValueError as e:
            send(f"Invalid input: {e}")

##############
#END OF Battleships stuff
#############

#Class to hold state of game 
class GameState:
    def __init__(self):
        self.player_1 = None
        self.player_2 = None
        self.current_player = None
        self.waiting_player = None
        self.successful_turn = False
    
    def set_player_1(self, player_1):
        self.player_1 = player_1
    
    def set_player_2(self, player_2):
        self.player_2 = player_2

    def set_current_and_waiting_player(self, current_player, waiting_player):
        self.current_player = current_player
        self.waiting_player = waiting_player
    
    def set_successful_turn(self, successful_turn):
        self.successful_turn = successful_turn

def game_logic(GameState):

    #Send the current state of both boards to the current player


    #Send "Waiting for other player to choose coordinate" to waiting player

    #Get the "guess" from the current player

    #If the "guess" is "quit" then remove that player 


        #parse the coordinate

        #





    pass


#Class to hold all data for each client 
class Client: #this is renamed from "Player"
    def __init__(self, connection, address, player_num):

        #IP address and port of the client 
        self.address = address
        self.connection = connection
        self.port = str(address[1])


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
            #run 2 times per second 
            #I believe that the sleep call allows the threads to run at the same time 
            time.sleep(0.5)

            #read the line and strip() to remove any whitespace
            packet = client.rfile.readline().strip()
            
            #check if the connection is broken
            if not packet:
                print(f"Player {client.address} disconnected")
                running = False
                break
            
            dict_packet = json.loads(packet)

            history_in.append(dict_packet)
    
        else:
            break


def print_client_messages_to_console():
    global running
    global history_in
    
    while True:
        if running:

            if len(history_in) != 0:
                        
                #read the most recent message from the server (if it hasnt been read )
                recent_packet = history_in[-1] 
                if recent_packet["read"] != True:
                    from_addr = recent_packet["from_addr"]
                    print(f"[{from_addr}]: " + str(recent_packet["message"]))
                    recent_packet["read"] = True
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
    
    #Set up the game 
    game = GameState()
    #set player 1 and player 2
    for connection in connections:
        if connection.player_num == 1:
            game.set_player_1(connection)
        if connection.player_num == 2:
            game.set_player_2(connection)
    #   Set current and waiting players
    game.set_current_and_waiting_player(game.player_1, game.player_2)


    #create a listening thread for each player 
    #TODO make this a loop
    listen_thread_player_1 = threading.Thread(target=listen_for_player_messages, args=(game.player_1,))
    listen_thread_player_2 = threading.Thread(target=listen_for_player_messages, args=(game.player_2,))
    listen_thread_player_1.start()
    listen_thread_player_2.start()

    printing_client_messages_thread = threading.Thread(target=print_client_messages_to_console)
    printing_client_messages_thread.start()

    print("active threads: " + str(threading.active_count()))


    
    #send welcome message
    message = "Welcome to Online Single-Player Battleship! Try to sink all the ships. Type 'quit' to exit."
    game.player_1.send_packet_to_client(message, False)
    game.player_2.send_packet_to_client(message, False)
    game.player_1.send_packet_to_client("You are Player 1", False)
    game.player_2.send_packet_to_client("You are Player 2", False)

    game.player_1.send_packet_to_client("send me something", 1)

    


    while True: 
        #if the server is still running 
        if running:
            time.sleep(0.5)

            #game_logic
            game_logic(game)

            
                     
            


            '''
            print(f"Main server THREAD:  {time.time()}")
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
            print("sent packet to player 1 ")
            battleship_game.player_1.wfile.write(packed)
            battleship_game.player_1.wfile.flush()

            message = "different message"
            packet_dict = {
                "time" : time.time(),
                "message" : message,
                "checksum" : hash(time.time())
            }

            #"pack"  the packet into a json thing
            packed = json.dumps(packet_dict) + "\n"
            print("sent packet to player 2")
            battleship_game.player_2.wfile.write(packed)
            battleship_game.player_2.wfile.flush()
            
            
            '''
        else:
            break
            



# HINT: For multiple clients, you'd need to:
# 1. Accept connections in a loop
# 2. Handle each client in a separate thread
# 3. Import threading and create a handle_client function

if __name__ == "__main__":
    main()