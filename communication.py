import json
import threading
import communication
# This is a implementation of a network protocol which both the server and the client use to communicate to each other 
# the basic premise is 
#       Communicator object only serves 1 connection (2 sockets)
#       Both sender and receiver will have an instance of a Communicator object (server will have 2 , one for each player connection)
#       Sender will create a packet object which contains the message they want to send 
#       When the packet is complete, the Sender will send the packet to the communicator 
#       the sender communicator will turn the data in the packet into a json string using the json library
#       the sender communicator will send the json string, line by line to its write file
#       the sender communicator have a thread which is always listening to the readfile of its connection
#           if the receiver communicator reads "{" as a line in the readfile, it knows this is the beginning of a packet
#           the receiver will append all lines to a string(or list) until it receives "}" (end of packet)
#           receiver uses the json library to "unzip" the string into a python dictionary 
#           receiver will send this python information to the main process to use the data 

#Why is this function here: from experience in Agile, it seems that the loop running in a thread can NOT be inside another function or in a class, it must be "top level" 
def communicator_listening_loop(communicator):
    
    #     """Continuously receive and display messages from the server"""
    line = communicator.rfile.readline()

    running = True
    while running:
        #line = communicator.rfile.readline()
        
        #check if the connection has dropped 
        if not line:
            communicator.connection_dropped()
            return
        #print(line)

        #I dont think we want strip for the json input
        #line = line.strip() #The strip() method removes any leading, and trailing whitespaces.

        

        json_of_line = json.loads(line)

        #communicator.run_when_new_packet(json_of_line)
        print("testing")
        #print("JSON OF LINE : \n\n\n\n" + json.dumps(json_of_line))

        '''
        #Look for beginning of packet
        if line == "{":
            received_packet_as_string = ""
            #add the line to received_packet_as_string
            received_packet_as_string += line
            while True:
                packet_line = communicator.rfile.readline()
                
                #Check if connection has dropped 
                if not packet_line:
                    communicator.connection_dropped()
                    break

                #If the connection is alive, check if we have received the end of the json packet
                if packet_line != "}":
                    received_packet_as_string += packet_line
                else: #we have gotten to the end of the packet
                    received_packet_as_string += packet_line
                    break
            
            #We have now received ALL of the packet 
            #turn the packet string into a python dictionary 
            received_packet_as_string = json.dumps(received_packet_as_string)
            packet = json.loads(received_packet_as_string) #json.loads stands for load-"s" not "loads" where s is "string" (json.load returns a file i think)
            #send this packet to the communicator (for it to send the data to the main thread of its process)
            communicator.run_when_new_packet(packet)
            #TODO maybe turn packet dictionary back into a Packet object before sending 
        '''
        

    pass




class Communicator:
    def __init__(self):
        pass
        #self.from_socket = from_socket # the socket of the process hosting this communicator 
        #self.to_socket = to_socket #the socket of the process that is on the other end of the connection 


    def set_run_when_new_packet(self, function):
        self.function_to_run_when_new_packet = function

    def run_when_new_packet(self, packet):
        self.function_to_run_when_new_packet(packet)

    def set_rw_files(self,rfile, wfile):
        self.rfile = rfile
        self.wfile = wfile

    def start_listening_thread(self):
        self.listening_thread = threading.Thread(target=communicator_listening_loop, args=(self,))
        self.listening_thread.daemon = True
        self.listening_thread.start()
        
    
    def stop_listening_thread(self):
        self.listening_thread.join()

    def connection_dropped(self):
        print(f"Connection has dropped")
        #Handle dropped connection nicely

    def send_packet(self, packet):
        #create a dictonary which contains all the information from the packet object 
        dictionary = {
            "to_socket" : str(packet.to_socket),
            "from_socket" : str(packet.from_socket),
            "message" : str(packet.message),
            "checksumhash" : "", #not using this yet
            "packet_id" : "" #not using this yet
        }

        #turn that dictionary into json
        json_packet = json.dumps(dictionary) #indent gives you the nice formatting with whitespace 
        
        #Warning:
        # using indents is is why i think we need to avoid using .strip() in the reading loop when looking for "{" 
        
        #Warning: We might need to split the json_packet into a list, with splits at each "\n" character to avoid funkyness

        #write the json string to the 
        self.wfile.write(json_packet)
        self.wfile.flush()
        

        

class Packet:
    def __init__(self, from_socket, to_socket):
        self.from_socket = from_socket # the socket that this packet is being sent from 
        self.to_socket = to_socket #the socket that this packet it being sent to
        self.message = ""
        self.checksumhash = None #not using this yet
        self.packet_id = None #not using this yet

    def set_message(self,message):
        self.message = message
    
    def add_to_message(self,message):
        self.message += "\n" + message

