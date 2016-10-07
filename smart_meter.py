# Should include
#   - Algorithm
#   - Communication between all nodes
#   - Polling price from NordPool

# May have this structures:
#   - WaitingList = {id, time, power, (group id), deadline}
#   - Price = {Hour, avg price}


import socketserver
import json
import download_price
import socket
import threading
import time
import select
import matplotlib.pyplot as plt

class SmartMeter():
    def __init__(self):
        # Fetch electricity price for the following 24 hours
        self.pricelist = self.update_price()
        self.next_pricelist = self.update_price() # This should be different from the first one

        # Start the server
        HOST, PORT = "localhost", 9000
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((HOST, PORT))
        self.server_socket.listen(10)
        self.sockets = {}
        print ("Listening on port: " + str(PORT))
        
        # Variables for plotting
        self.xAxisMinArray = []
        self.totalValue = [] # Power consumption

        # Scheduling variables
        self.node_list = {} # Dict with all known devices
        self.waiting_list = {} # Dict with all waiting background loads
        self.active_list = {} # Dict with all active devices
        self.background_list = {} # Dict with all known background devices(active and inactive)
        self.background_load = {} # Dict with all active background devices
        self.deadline_load = {} # Dict with all active deadline tasks
        self.current_power = 0 
        self.threshold = 1000  # maximum allowed power
        self.blocks_per_hour = 6 # Set how many blocks there is per hour
        self.clock = 0
        
        # TODO: Is there a better way than initialize this list?
        # length of all blocks for the following 24 hours, keep track of scheduled power consumption every block
        self.block_schedule = [[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[],[]] 
        self.current_hour = 0 # Keeps track of the current hour of the day
    
    def update_price(self):
        return download_price.downloadPrice("elspot_prices.xls")

    # TODO: Should maybe have an input with number of blocks that's needed and be returned the number to the blocks of the cheapest ones
    # Find cheapest hour and return hour and price for that
    # Should consider if there are several hours with same lowest price, which one has least schedule?
    def find_cheapest_hour(self):
        
        lowest_price = (min(self.pricelist.items(), key=lambda x: x[1]))
        # print ("Hour: " + str(lowest[0]) + " is chepeast, " + str(lowest[1]) + "kr/kWh")
        return lowest_price

    # Find cheapest hour that not already is chosen
    def find_cheapest_hour_with_exception(self, tmp_list):
        
        tmp_pricelist = self.pricelist.copy()

        # Get the cheapest value
        cheapest_price = 1000.0 # Value just to make sure it will be lower

        for k, v in tmp_pricelist.items():
            if (k not in tmp_list):
                if (v < cheapest_price):
                    cheapest_price = v
                    hour = k

        return hour

    # Find cheapest price based on price within the time limit
    def find_cheapest_hour_with_limitation(self, tmp_list, start, deadline):

        # Get the cheapest value
        cheapest_price = 1000.0 # Value just to make sure it will be lower
        
        valid_hours = []

        # Create a list with all valid hours
        while (start != deadline):
            valid_hours.append(start)
            # Increase by one and modulo 24 to catch cases where deadline is lower than starttime
            start += 1
            start = start % 24

        # Pick out the hour with cheapest price and fulfill the requirements
        for k, v in self.pricelist.items():
            if ((k not in tmp_list) and (k in valid_hours)):
                if (v < cheapest_price):
                    cheapest_price = v
                    hour = k

        return hour

    # Find the total price for the schedule task if we would have started it 
    # directly when request
    def find_worstcase_price(self, duration, power):
        total_price = 0

        index = self.current_hour
        stop = (self.current_hour + duration) % 24
        
        # Make it to kW instead of Watt since price is per kWh
        power = power / 1000

        # Calculate total price from current hour and so many hours the device need to run
        while (index != stop):
            total_price += (self.pricelist[index] * power) 

        return total_price
    
    # Find the best hours based on price
    def find_hours(self, duration, deadline):
        tmp = []

        for i in range(0, duration):
            tmp.append(self.find_cheapest_hour_with_limitation(tmp, self.current_hour, deadline))

        return tmp
        
    def schedule(self, node_id, deadline, duration):
        
        print(self.pricelist)

        # TODO: Should it include power as well? Checking threshold and so on
        hours = self.find_hours(duration, deadline)
        print("hours = " + str(hours))

        power = self.node_list[node_id]['power']
        print("power : " + str(power))

        # Add the power consumption for each block of the best suitable hours
        for h in hours:
            # Find the blocks representing each hour
            index = h * self.blocks_per_hour
            for i in range(index, (index + self.blocks_per_hour)):
                # Add id and power to that index in the list, id to be able to 
                # call it later when it should be activated

                self.block_schedule[i].append(({'id' : node_id, 'power': power}))
                #item for item in self.block_schedule if item[0] == id

        print("Node " + str(node_id) + " scheduled!")

    def handle_register(self, payload):

        # Add the node to the list of all nodes
        print('Register from node: ' + str(payload['id']))
        self.node_list[payload['id']] = payload['details'].copy()
        id = payload['id']
        
        # Check if the node is a background task
        if (payload['details']['flexible'] == 1):
            self.background_list[payload['id']] = payload['details']
            self.waiting_list[payload['id']] = payload['details']

        elif (payload['details']['flexible'] == 2):
            print("Scheduable task")

        return id

    # Called every hour to update last hours price with the following days price
    def update_pricelist(self, current_hour):
        # Update the price for the last hour with the price for that hour next day
        self.pricelist[current_hour-1] = self.next_pricelist[current_hour-1]

    # Helpfunction that help finding the best backgroundload to pause, 
    # with shortest time left, since it is easier to schedule later
    def find_least_slack(self, temp_list):
        # Sort by lowest time block left, and if same, sort by lowest power
        if (len(temp_list) > 0):
            # slack = 6 means run 6/6 blocks/hour, meaning maximum and no scheduable
            slack = self.blocks_per_hour
            
            # Temporary list that keeps track of nodes with identical values
            tmp_list = {}

            # Find minimum time
            for k, v in temp_list.items():
                if (v['time'] < slack):
                    slack = v['time']
                    node_id = k
                    tmp_list = {}
                    tmp_list.update({k: v})
                elif (v['time'] == slack and slack != self.blocks_per_hour):
                    tmp_list.update({k: v})

            # Find which node that has lowest power and return it
            if (len(tmp_list) > 1):
                # Infinite high number to make sure no device has higher power
                low_pow = 99999
                # Find minimum power consumption
                for k, v in tmp_list.items():
                    if (v['power'] < low_pow):
                        low_pow = v['power']

                for k, v in tmp_list.items():
                    if v['power'] == low_pow:
                        node_id = k
                        val = v
                        break    
            else:
                val = tmp_list[node_id]

            #print(str(node_id) + " has the highest slack")
            return node_id, val
        
        # If no backgroundloads exists, send back a message for that
        else:
            return None, None

    def handle_request(self, payload):
        print('Request from node: ' + str(payload['id']))
        id = payload['id']
        # Get the tuple of details based on the requested node's id
        details = self.node_list[payload['id']]
        
        # Check which flexibility the node has
        # Interactive load
        if (details['flexible'] == 0):
            print('Interactive load')
            
            # Add the power to the total consumption
            self.current_power += details['power']
            
            # Add device to active list
            self.active_list[payload['id']] = {'id': payload['id']}

            # Send approval to the node
            payload = json.dumps({'action':'approved'}).encode('utf-8')
            
            self.sockets[id].send(payload)

            # TODO, check so we don't disconnect any emergency load that has to run

            # If interactive load exceed the limit, turn off background load
            if self.current_power > self.threshold:
                # Until we have a current power below threshold, continue
                while (self.current_power > self.threshold):
                    # find the background node that should be turned off
                    node_id, node_details = self.find_least_slack(self.background_load)
                    # Check that there arent any background loads to disconnect
                    if (not node_id):
                        break
                    
                    # Send disconnect msg to the background node
                    payload = json.dumps({'action':'disconnect'}).encode('utf-8')
                    self.sockets[node_id].send(payload)

                    # Remove it from the active list
                    self.active_list.pop(node_id)
                    
                    # Add the device back to the waiting list
                    self.waiting_list[node_id] = node_details

                    # Decrease the power
                    self.current_power -= self.node_list[node_id]['power']
                    self.background_load.pop(node_id)

        # Background load with time interval
        elif (details['flexible'] == 1):
            print('Background')
            self.active_list[payload['id']] = {'id' : payload['id']}
            self.background_load[payload['id']] = payload

            payload = json.dumps({'action':'approved'}).encode('utf-8')
            self.sockets[id].send(payload)

            self.current_power += details['power']

        # Background load with deadline
        elif (details['flexible'] == 2):
            print('Schedulable')

            deadline = details['deadline']
            duration = details['time']

            self.schedule(id, deadline, duration)
            #print(self.block_schedule)
        
        # Invalid flexible type
        else:
            print('Invalid flexible type')

    def handle_disconnect(self, payload):
        print('Disconnect from node: ' + str(payload['id']))
        id = payload['id']

        self.active_list.pop(id)

        payload = json.dumps({'action':'disconnect'}).encode('utf-8')
        self.sockets[id].send(payload)

        details = self.node_list[id]
        self.current_power -= details['power']

    def handle_update(self, payload):
        print('Update from node: ' + str(payload['id']))

    def handle_recv(self, s):
        try:
            data = s.recv(1024)
        except Exception as e:
            return

        if not data:
            return
        data = data.decode('utf-8')
        try:
            data = json.loads(data)
        except Exception as e:
            print (e)
            return

        return data

    def handle_action(self, data):
        action = data['action']
        payload = data['payload']

        # Request action
        if (action == 'request'):
            self.handle_request(payload)

        # Update action
        elif (action == 'update'):
            self.handle_update(payload)

        # Disconnect action
        elif (action == 'disconnect'):
            self.handle_disconnect(payload)

        # Invalid, drop it 
        else:
            print('Invalid action received')

    def check_scheduled_tasks(self):
        # Get which block in the schedule list we should look at
        # Go through all tasks in the block schedule and see if some of them not is 
        # active, then we know it should be started now
        for node in self.block_schedule[self.clock]:
            
            # v could looks like [{1:300}, {2:500}]  should check if id:s is in active list already
            if node['id'] not in self.active_list:
                print("ID not in active list, should start it now instead")
                # Send activate message
                payload = json.dumps({'action':'activate'}).encode('utf-8')
                self.sockets[node['id']].send(payload)

                # Add device to lists that keep track of the active ones
                self.active_list[node['id']] = {'id': node['id']}
                self.deadline_load[node['id']] = {'id': node['id']}

                # add power to current_power as well
                self.current_power += node['power']

    def decrease_time(self):
        disc_list = []

        # If it is a background task
        if (self.background_load):
            for k, v in self.background_load.items():
                v['time'] = v['time'] - 1
                
                # If time is 0, disconnect the device
                if (v['time'] == 0):
                    print(str(k) + " is done for this hour")
                    # Send disconnect msg to the background node
                    payload = json.dumps({'action':'disconnect'}).encode('utf-8')
                    self.sockets[k].send(payload)
                    
                    self.current_power -= v['power']
                    self.active_list.pop(k)

                    # add id:s to a temporary list since you can't change size of the list you iterate over
                    disc_list.append(k)
            
            # Remove all loads that are done 
            for k in disc_list:
                self.background_load.pop(k)

        # If it is a deadline task
        if (self.deadline_load):

            # Get all scheduled task next hour
            next_step = self.block_schedule[self.clock+1]

            for node in self.block_schedule[self.clock]:
                if ((node['id'] in self.active_list) and (node not in next_step)):
                    
                    payload = json.dumps({'action':'disconnect'}).encode('utf-8')
                    self.sockets[node['id']].send(payload)
                    
                    self.current_power -= self.node_list[node['id']]['power']
                    self.active_list.pop(node['id'])
                    self.deadline_load.pop(node['id'])

    def schedule_background(self, clock):
        disc_list = []

        # Check if there are any loads that have to be turned on this round
        if (self.waiting_list):
            time_left = self.blocks_per_hour - clock
            for k, v in self.waiting_list.items():
                if (v['time'] == time_left):
                    print("Turn on emergency background for node: " + str(k))
                    # Send activate msg to the background node
                    payload = json.dumps({'action':'approved'}).encode('utf-8')
                    self.sockets[k].send(payload)
                    
                    # Update current power
                    self.current_power += v['power']

                    # Add it to the active list and remove it from waiting list
                    self.active_list[k] = {'id': k}                   

                    # Add it to background loads to be able to see active backgrounds
                    self.background_load[k] = v

                    # add id:s to a temporary list since you can't change size of the list you iterate over
                    disc_list.append(k)
            
            # Remove all loads that are started 
            for k in disc_list:
                self.waiting_list.pop(k)

            while ((self.current_power < self.threshold) and self.waiting_list):
                # find the background node that should be turned off
                node_id, node_details = self.find_least_slack(self.waiting_list)
                print("Should turn on " + str(node_id))
                
                # Send activate msg to the background node
                payload = json.dumps({'action':'approved'}).encode('utf-8')
                self.sockets[node_id].send(payload)
                
                # Update current power
                self.current_power += node_details['power']

                # Add it to the active list and remove it from waiting list
                self.active_list[node_id] = {'id': node_id}
                self.waiting_list.pop(node_id)

                # Add it to background loads to be able to see active backgrounds
                self.background_load[node_id] = node_details
            else:
                print("Uses to much power to enable background")
    
    def reset_backgrounds(self):

        # Loop through all background devices and reset the time
        for k, v in self.background_list.items():
            v['time'] = self.node_list[k]['time']
            self.background_list.update({k: v})

        # If we miss someone, should throw error or empty the list
        if ((len(self.waiting_list) != 0) or (len(self.background_load) != 0)):
            # Remove all background loads from active list
            for k, v in self.background_list.items():
                try:
                    self.active_list.pop(k)
                    self.current_power -= self.node_list[k]['power']
                except:
                    continue

            self.waiting_list.clear()
            self.background_load.clear()
            print("Opps! Missed to schedule some background loads")
        #else:
        # Add all reset items to the list again
        for k, v in self.background_list.items():
            self.waiting_list[k] = v

    # Function from previous project to plot the data
    def drawPlot(self, minutesArray, powerArray):
        '''
        Draw final simulation plot. (Not used anymore)
        '''
        plt.plot(minutesArray, powerArray)
        plt.ylabel('Watt')
        plt.xlabel('Hours')
        plt.show() 
    
    # Function from previous project to plot the data
    #def on_running(self, xdata, ydata, y2data):
    def on_running(self, xdata, ydata):
        # Update data (with the new _and_ the old points)
        self.lines.set_xdata(xdata)
        self.lines.set_ydata(ydata)
        #self.lines2.set_xdata(xdata)
        #self.lines2.set_ydata(y2data)
        # Need both of these in order to rescale
        self.ax.relim()
        self.ax.autoscale_view()
        # We need to draw *and* flush        
        self.figure.canvas.draw()
        self.figure.canvas.flush_events()

    def main(self):

        # Initialize real-time plot
        plt.ion()
        self.figure, self.ax = plt.subplots()
        self.lines, = self.ax.plot([],[], 'r-', label="LSF")
        self.lines2, = self.ax.plot([],[], 'b-', label="Without LSF")
        self.ax.set_autoscaley_on(True)
        self.ax.set_xlim(0, 144)
        self.ax.set_ylim(0, 350)
        self.ax.set_xlabel('Minutes')
        self.ax.set_ylabel('Watt')
        self.ax.grid()
        plt.legend()
        plt.show()

        while True:
            '''
            current_second = int(time.strftime('%S', time.gmtime()))
            if (current_second != int(time.strftime('%S', time.gmtime()))):
                print("Inne på sekund: " + str(current_second))
                #self.schedule()
                current_second = int(time.strftime('%S', time.gmtime()))
            '''
            print("======== New block ========")
            print("Current power: " + str(self.current_power))
            print("Active list: " + str(self.active_list))
            print("Background load: " + str(self.background_load))
            print("Deadline load: " + str(self.deadline_load))
            print("Waiting list: " + str(self.waiting_list))

            self.current_second = int(time.strftime('%S', time.gmtime()))

            # The scheduler for the background loads
            self.schedule_background((self.clock%self.blocks_per_hour))

            # The scheduler for already scheduled tasks, check if some should be turned on
            self.check_scheduled_tasks()

            # Function that decrease the time for all background loads, type 1
            self.decrease_time()

            # Check if the main socket has connection
            readable, writable, errored = select.select([self.server_socket], [], [], 0)
            for s in readable:
                if s is self.server_socket:
                    client_socket, address = self.server_socket.accept()
                    data = client_socket.recv(1024)

                    if not data:
                        continue
                    data = data.decode('utf-8')
                    try:
                        data = json.loads(data)
                    except Exception as e:
                        print (e)
                        continue

                    # Set it up
                    # Might need to set up a much higher timeout here as well, AND in node.py sockets
                    client_socket.setblocking(0)

                    # Fetch the id and add it to the socket list
                    id = self.handle_register(data['payload'])
                    self.sockets[id] = client_socket

            # Check if the other sockets have sent something to us
            for s in self.sockets.values():
                data = self.handle_recv(s)
                if data:
                    self.handle_action(data)
                else:
                    continue

            # Wait here until next second
            while(self.current_second == int(time.strftime('%S', time.gmtime()))):
                pass
            
            # Update plot data
            self.xAxisMinArray.append(self.clock)
            self.totalValue.append(self.current_power)

            # Increase time
            print("Clock: " + str(self.clock))
            self.clock += 1

            if (self.clock % self.blocks_per_hour == 0):
                print("================== NEW HOUR =================")
                # Increase to new hour and keep it between 0 and 23
                self.current_hour += 1
                self.current_hour = self.current_hour % 24

                # Reset function that reset the internal time for all background devices every 6th block (seconds)
                self.reset_backgrounds()

                # Update pricelist with the last hour
                self.update_pricelist(self.current_hour)

            if (self.clock % (self.blocks_per_hour*24) == 0):
                print("!!!!!!!!!!!!!!!!!! New day! !!!!!!!!!!!!!!!!!!")

                # Should maybe reset the list that keeps track of the price for each device every hour, or just continue calculate
            
            # Plot dynamically
            #self.on_running(xAxisMinArray, totalValue, totalValueWithoutLSF)
            print(self.xAxisMinArray)
            print(self.totalValue)
            #self.on_running(self.xAxisMinArray, self.totalValue)
            self.drawPlot(self.xAxisMinArray, self.totalValue)
            
            # Sleep for a while! Should not be necessary later when time is working
            time.sleep(0.6)

if __name__ == "__main__":
    # Host info
    smart_meter = SmartMeter()
    smart_meter.main()
