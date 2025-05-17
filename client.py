"""
client.py

Connects to a Battleship server which runs the single-player game.
Simply pipes user input to the server, and prints all server responses.

TODO: Fix the message synchronization issue using concurrency (Tier 1, item 1).
"""

import socket


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

import threading

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print("Connecting to server...")
        s.connect((HOST, PORT))
        print("Successfully connected to server...")
        print("Waiting for other player to connect...")

        rfile = s.makefile('r')
        wfile = s.makefile('w')

        try:
            while True:
                   
                line = rfile.readline() 
                
                #if there is no response when the loop comes back to here 
                #then the server is disconnected
                if not line:
                    print("[INFO] Server disconnected.")
                    break

                line = line.strip()


                #Print the game board
                if line == "GRID":
                    # Begin reading board lines
                    print("\n[Board]")
                    while True:
                        board_line = rfile.readline()
                        if not board_line or board_line.strip() == "":
                            break
                        print(board_line.strip())
                

                # if the message is "OVER" that means the server is done and will wait for user response
                elif(line == "OVER"):
                    
                    user_input = input(">> ") # this should halt the thread until something is entered in the terminal
                    wfile.write(user_input + '\n')
                    wfile.flush()
    
                else:
                    #this is a normal message
                    print(line)
                    pass
                    
                


        except KeyboardInterrupt:
            print("\n[INFO] Client exiting.")

# HINT: A better approach would be something like:
#
# def receive_messages(rfile):
#     """Continuously receive and display messages from the server"""
#     while running:
#         line = rfile.readline()
#         if not line:
#             print("[INFO] Server disconnected.")
#             break
#         # Process and display the message
#
# def main():
#     # Set up connection
#     # Start a thread for receiving messages
#     # Main thread handles sending user input

if __name__ == "__main__":
    main()

