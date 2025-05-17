import threading
import random
import time
import socket 
import json

HOST = '127.0.0.1'
PORT = 8081

def main ():
    global running
    running = True


    print("setting up server...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
    s.bind((HOST, PORT)) #Blocking (it wont go further until this has happened)
    s.listen(1) # waiting for connections blocked until 2 people connect
    conn, addr = s.accept()
    print(f"[INFO] Client connected from {addr}")
    rfile = conn.makefile('r')
    wfile = conn.makefile('w')
    
        
    
    print("i think this is blocked ")


    while True:
        time.sleep(1)

        if running == True:

            message = "MESSAHEBDA"
            packet_dict = {
                "time" : time.time(),
                "message" : message,
                "checksum" : hash(time.time())
            }

            #"pack"  the packet into a json thing
            packed = json.dumps(packet_dict) + "\n"

            
            
            wfile.write(packed)
            wfile.flush()
        else:
            break



if __name__ == "__main__":
    main()