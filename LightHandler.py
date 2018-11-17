import time, threading, math, json
from websocket import create_connection
from MalachiExceptions import QLCConnectionError, LightingBlockedError

class LightHandler():

    def __init__(self):
        try:
            self.fixture_channels = [5, 6, 7, 8] # TODO: Store and load in from JSON
            self.saved_channels = [[0 for j in range(2)] for i in range(len(self.fixture_channels))]
            self.blackout_channels = [[0 for j in range(2)] for i in range(len(self.fixture_channels))]
            for i in range(len(self.fixture_channels)):
                self.saved_channels[i][0] = self.fixture_channels[i]
                self.blackout_channels[i][0] = self.fixture_channels[i]
            self.light_socket = create_connection('ws://localhost:9999/qlcplusWS')
            print("LightHandler connected to QLC+")
            self.connected = True
            self.blocked = False
        except:
            print("LightHandler unable to connect to QLC+")
            self.connected = False
            self.blocked = True

    def set_channel(self, channel, val):
        if not self.connected:
            raise QLCConnectionError()
        if self.blocked:
            raise LightingBlockedError()
        self.light_socket.send("CH|" + str(channel) + "|" + str(val))

    def set_channels(self, channels):
        if not self.connected:
            raise QLCConnectionError()
        if self.blocked:
            raise LightingBlockedError()
        for channel in channels:
            self.light_socket.send("CH|" + str(channel[0]) + "|" + str(channel[1]))

    def get_channels(self):
        if not self.connected:
            raise QLCConnectionError()
        self.light_socket.send("QLC+API|getChannelsValues|1|1|32")
        result = self.light_socket.recv().split("|")[2:]
        output_channels = [[0 for j in range(2)] for i in range(len(self.fixture_channels))]
        for i in range(len(self.fixture_channels)):
            output_channels[i][0] = self.fixture_channels[i]
            output_channels[i][1] = int(result[(3*self.fixture_channels[i])-2])
        return output_channels

    def save_fixture_channels(self):
        if not self.connected:
            raise QLCConnectionError()
        self.light_socket.send("QLC+API|getChannelsValues|1|1|32")
        result = self.light_socket.recv().split("|")[2:]
        for i in range(len(self.fixture_channels)):
            self.saved_channels[i][1] = int(result[(3*self.fixture_channels[i])-2])

    def fade_channels(self, end_channels, duration):
        # Duration is in ms, 40Hz
        if not self.connected:
            raise QLCConnectionError()
        if self.blocked:
            raise LightingBlockedError()
        self.blocked = True
        self.light_socket.send("QLC+API|getChannelsValues|1|1|32")
        result = self.light_socket.recv().split("|")[2:] # [0] = QLC+API, [1] = getChannelsValues, 
        # result is now [channel, value, details, channel, value, details, ...]
        start_channels = [[0 for j in range(2)] for i in range(len(end_channels))]
        for i in range(len(end_channels)):
            start_channels[i][0] = end_channels[i][0] # Channel number
            start_channels[i][1]  = int(result[(3*end_channels[i][0])-2])
        steps = math.floor(duration / 40)
        for i in range(steps+1):
            for c in range(len(end_channels)):
                val = ((end_channels[c][1] - start_channels[c][1])*(i/steps))+start_channels[c][1]
                self.light_socket.send("CH|" + str(end_channels[c][0]) + "|" + str(int(val)))
            time.sleep(0.025)
        # Release lock on LightHandler
        self.blocked = False