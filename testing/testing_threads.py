import threading
import time
import random

def thread_function(thread_number):
    global count
    count = 0
    while True:

        if running:
            time.sleep(random.random())
            count += 1
            print(f"Thread Number {thread_number} : count = {count}")
        else:
            break
        
        
def main():

    global running
    running = True

    for num in range(50):
        thread = threading.Thread(target=thread_function, args=(num, ))
        thread.start()
    
    

    while True:
        
        print(f"MAIN THREAD {count}")
        if count > 1000:
            running = False
            break
        time.sleep(0.1)
        

    






if __name__ == "__main__":
    main()