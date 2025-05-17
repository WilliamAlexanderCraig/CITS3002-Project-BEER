import threading
import random
import time
import socket 
import json

HOST = '127.0.0.1'
PORT = 8081




def looping(readfile):
    global running
    global history
    

    while True:
       
        if running:
            time.sleep(0.1)

            line = readfile.readline()

            #Is connection still alive?
            if not line:
                    print("[INFO] Server disconnected.")
                    running = False
                    break
            #print(line)
            history.append(line)
            
        else:
            break
        



def main():

    global running 
    running = True
    
    rfile = None
    wfile = None


    global history
    history = []
    
    

    #establish connection
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    print("Connecting to server...")
    s.connect((HOST, PORT))
    #print("Successfully connected to server...")
    #print("Waiting for other player to connect...")
    
    rfile = s.makefile('r')
    wfile = s.makefile('w')
    
    looping_thread = threading.Thread(target=looping, args=(rfile,))
    looping_thread.start()

    while True:
        
        if looping_thread.is_alive() == False:
            break
        if running == True:
            if history:
                last = history[-1]
                last = last.strip()
                unstringed_json = json.loads(last)
                print(unstringed_json["checksum"]) # please help with this bit
        else:
            break
        time.sleep(0.1)
        




        

    






if __name__ == "__main__":
    main()