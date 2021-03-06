# Should include
#   - Simulating data for a specific node
#   - Node = {id, power, time, flexible, category, priority, group id}

# Should have the following variables:
# ID/Name
# Power - Watt
# Time - If battery charge or runtime to heat up the house, how long time to load?
# Flexible - Can you schedule it? 
# ... 0 means interactive loads since we cannot control them at all
# ... 1 means background load that need to be run in a certain interval (slack), 
# ... 2 (extended) means that we have a deadline, but nothing else to consider
# Category - Category of the load
# ... 0 - Heating
# ... 1 - Fridge
# ... 2 - Electronics (TV/Computer etc.)
# ... 3 - Kitchen
# ... 4 - Lights
# ... 5 - Charging
# Priority - How important it is compared to other products
# Group ID (Fas) - Feature to be able to restrict total consumption at the same phase

import socket
import sys
import json
import time
from threading import Thread
import time

HOST, PORT = 'localhost', 9000

class Node(Thread):
    def __init__(self, id, power, time, flexible, deadline, activity):
        # Set up threading
        Thread.__init__(self)
        self.daemon = True

        # Connect to the Smart Meter
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))
        self.sock.setblocking(0)
        self.id = id
        self.power = power
        self.time = time
        self.flexible = flexible
        self.deadline = deadline
        self.activity = activity
        self.block_per_hour = 6

        self.data = {'id':self.id, 'details':{'power':power, 'time':time, 'flexible':flexible, 'deadline':deadline}}

        payload = {'action': 'register', 'payload':self.data}

        self.send(payload)

        # Start the thread
        self.start()
        
    def update(self):
        payload = {'action':'update', 'payload':self.data}
        self.send(payload)

    def request(self):
        payload = {'action':'request', 'payload':{'id':self.id}}
        self.send(payload)

    def change_load(self, power):
        self.power = power
        self.data['details']['power'] = power
        self.update()

    def disconnect(self):
        payload = {'action':'disconnect', 'payload':{'id':self.id}}
        self.send(payload)

    def send(self, payload):
        payload = json.dumps(payload).encode('utf-8')
        self.sock.sendall(payload)

    def thread_print(self, msg):
        print("Node: " + str(self.id) + ", msg: " + str(msg))

    def handle_recv(self):
        try:
            data = self.sock.recv(1024)
        except Exception as e:
            return

        if not data:
            return
        data = data.decode('utf-8')
        res = []
        try:
            data = data.split('}')
            for part in data:
                if part:
                    part = part + '}'
                    part = json.loads(part)
                    res.append(part)
                else:
                    continue  
        except Exception as e:
            self.thread_print(e)
            return

        return res

    def check_msg(self):
        data = self.handle_recv()
        if data:
            pass
        else:
            return

        self.thread_print(data)
        for action in data:
            self.handle_action(action)

    def handle_action(self, data):
        
        # Check if our request was approved
        if (data['action'] == 'approved'):
            self.switch_on() 

        # Check if we should perform our background activity now
        elif (data['action'] == 'activate'):
            self.switch_on()

        # Check if we should disconnect
        elif (data['action'] == 'disconnect'):
            self.switch_off()
        
        # Invalid
        else:
            self.thread_print (data)
            raise Exception

    def handle_activity(self, action):
        if (action == 1):
            self.request()
        elif (action == 2):
            self.disconnect()
        elif (action == 0):
            pass
        else:
            raise Exception

    def switch_on(self):
        # Connect PlugWise here
        print('Turning on node: ' + str(self.id))
        pass

    def switch_off(self):
        # Disconnect PlugWise here
        print('Turning off node: ' + str(self.id))
        pass

    def run(self):
        print("Node: " + str(self.id) + " is alive")
        #index = 16*self.block_per_hour # start at 16 pm instead of middle of night
        index = 0
        current_second = int(time.strftime('%S', time.gmtime()))

        # Run as long as the nodes has simulated activities
        while(index < len(self.activity)):
            
            # If we are flexible we only want to check messages, otherwise check activity list
            self.check_msg()
            if (self.flexible != 1):
                if (current_second != int(time.strftime('%S', time.gmtime()))):
                    self.handle_activity(self.activity[index])
                    index += 1
                    #index = index % (self.block_per_hour*24)
                    current_second = int(time.strftime('%S', time.gmtime()))
        print("Node Done")

if __name__ == '__main__':
    # id, power, time, flexible, deadline, activity
    # Array that tell the node when and how long to request power                                    7                                                           12                                  15          16                      18          19

    # Interactive loads
    activity0 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity1 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity2 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    activity3 = [0,0,0,0,1,0,0,0,2,0,0,0,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity4 = [0,0,0,0,0,1,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity5 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity6 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    activity7 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity8 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity9 = [0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity10 =[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    # Background loads
    activity11 =[0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity12 =[0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity13 =[0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    # Background loads modelled as interactive instead
    activity11_interactive =[0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0,0,0,1,0,2,0]
    activity12_interactive =[1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0]
    activity13_interactive =[0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0,0,1,0,0,2,0]

    # Deadline loads
    activity14 =[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity15 =[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity16 =[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]

    # Deadline loads modelled as interactive instead
    activity14_interactive =[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity15_interactive =[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]
    activity16_interactive =[0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,1,0,0,0,0,0,2,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0]


    # Create the nodes, time should always be based on 6 (one hour)
    # id, power, time, flexible, deadline, activity

    # Background loads
    #node11 = Node(11, 600, 2, 1, 0, activity11) # AC
    #node12 = Node(12, 600, 3, 1, 0, activity12) # Water Heater
    #node13 = Node(13, 160, 3, 1, 0, activity13) # Refrigerator

    # Background loads modelled as interactive instead
    node11 = Node(11, 600, 2, 0, 0, activity11_interactive) # AC
    node12 = Node(12, 600, 3, 0, 0, activity12_interactive) # Water Heater
    node13 = Node(13, 160, 3, 0, 0, activity13_interactive) # Refrigerator

    # Interactive loads
    node0 = Node(0, 150, 0, 0, 0, activity0) # Livingroom TV
    node1 = Node(1, 90, 0, 0, 0, activity1) # Bedroom TV
    node2 = Node(2, 40, 0, 0, 0, activity2) # Lights Big
    node3 = Node(3, 20, 0, 0, 0, activity3) # Lights Small
    node4 = Node(4, 950, 0, 0, 0, activity4) # Stove
    node5 = Node(5, 700, 0, 0, 0, activity5) # Oven
    node6 = Node(6, 600, 0, 0, 0, activity6) # Iron
    node7 = Node(7, 150, 0, 0, 0, activity7) # Outdoor lights
    node8 = Node(8, 200, 0, 0, 0, activity8) # Computer
    node9 = Node(9, 1200, 0, 0, 0, activity9) # Water Boiler
    node10 = Node(10, 900, 0, 0, 0, activity10) # Hair dryer

    # Deadline loads
    #node14 = Node(14, 2500, 4, 2, 8, activity14) # Electric Car
    #node15 = Node(15, 850, 1, 2, 23, activity15) # Laundry Machine
    #node16 = Node(16, 850, 1, 2, 7, activity16) # Dish Washer

    # Deadline loads modelled as interactive loads
    node14 = Node(14, 2500, 4, 0, 8, activity14_interactive) # Electric Car
    node15 = Node(15, 850, 1, 0, 23, activity15_interactive) # Laundry Machine
    node16 = Node(16, 850, 1, 0, 7, activity16_interactive) # Dish Washer
    
    while True:
        pass
