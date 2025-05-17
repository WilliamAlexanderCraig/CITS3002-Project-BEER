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

def print_once(thing):
    print(thing)

input_requested_from_server = False

client_history = []

def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        print("Connecting to server...")
        s.connect((HOST, PORT))
        print("Successfully connected to server...")
        print("Waiting for other player to connect...")

        rfile = s.makefile('r')
        wfile = s.makefile('w')
        communicator = communication.Communicator()
        communicator.set_run_when_new_packet(print_once)
        communicator.set_rw_files(rfile,wfile)
        #communicator.start_listening_thread(history)

        thread = threading.Thread(target=communicator.communicator_listening_loop, args=(client_history,))
        thread.start()
        
        running = True

        #
        # 
        # time.sleep(10)
        '''
        try:
            while running:

                #communicator.lock.aquire()
                print("alive " + str(time.time()))
                print("active threads " + str(threading.active_count()))

                print(history)

                time.sleep(1)
                
                if input_requested_from_server == True:
                    print(">>")
                    input_string = input()
                #communicator.lock.release()
            

                
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
            communicator.stop_listening_thread()
        '''
        

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

