# -*- coding: utf-8 -*-
# pylint: disable=C0103 # Snake-case naming convention

"""Control lights with QLC from within Malachi"""

import time
import math
from websocket import create_connection
from MalachiExceptions import QLCConnectionError, LightingBlockedError

class LightHandler():
    """Control lights with QLC from within Malachi"""

    def __init__(self, channel_list):
        try:
            self.fixture_channels = channel_list
            self.saved_channels = [[0 for j in range(2)] for i in range(len(self.fixture_channels))]
            self.blackout_channels = [[0 for j in range(2)] \
                for i in range(len(self.fixture_channels))]
            for i in range(len(self.fixture_channels)):
                self.saved_channels[i][0] = self.fixture_channels[i]
                self.blackout_channels[i][0] = self.fixture_channels[i]
            self.light_socket = create_connection('ws://localhost:9999/qlcplusWS')
            print("LightHandler connected to QLC+")
            self.connected = True
            self.blocked = False
        except ConnectionRefusedError:
            print("LightHandler unable to connect to QLC+")
            self.connected = False
            self.blocked = True

    def set_channel(self, channel, val):
        """
        Set the value of a single lighting channel.

        Arguments:
        channel -- the channel number
        val -- the new value

        Possible exceptions:
        QLCConnectionError -- raised if QLC was not running when Malachi was started
        and/or is not running at present
        LightingBlockedError -- raised if a fade has exclusive use of QLC at present
        """
        if not self.connected:
            raise QLCConnectionError()
        if self.blocked:
            raise LightingBlockedError()
        self.light_socket.send("CH|" + str(channel) + "|" + str(val))

    def set_channels(self, channels):
        """
        Set the value of multiple lighting channels.

        Arguments:
        channels -- a list of [channel number, new value] pairs.

        Possible exceptions:
        QLCConnectionError -- raised if QLC was not running when Malachi was started
        and/or is not running at present
        LightingBlockedError -- raised if a fade has exclusive use of QLC at present
        """
        if not self.connected:
            raise QLCConnectionError()
        if self.blocked:
            raise LightingBlockedError()
        for channel in channels:
            self.light_socket.send("CH|" + str(channel[0]) + "|" + str(channel[1]))

    def get_channels(self):
        """
        Get the values of all watched lighting channels as a list of [channel, value]
        pairs. The list of watched channels is specified in ./lights/light_presets.json,
        under the key "channels".

        Possible exceptions:
        QLCConnectionError -- raised if QLC was not running when Malachi was started
        and/or is not running at present
        """
        if not self.connected:
            raise QLCConnectionError()
        output_channels = [[0 for j in range(2)] for i in range(len(self.fixture_channels))]
        self.light_socket.send("QLC+API|getChannelsValues|1|1|32")
        result = self.light_socket.recv().split("|")[2:]
        for i in range(len(self.fixture_channels)):
            output_channels[i][0] = self.fixture_channels[i]
            output_channels[i][1] = int(result[(3*self.fixture_channels[i])-2])
        return output_channels

    def save_fixture_channels(self):
        """
        Save the values of all watched lighting channels to self.saved_channels.

        Possible exceptions:
        QLCConnectionError -- raised if QLC was not running when Malachi was started
        and/or is not running at present
        """
        if not self.connected:
            raise QLCConnectionError()
        self.light_socket.send("QLC+API|getChannelsValues|1|1|32")
        result = self.light_socket.recv().split("|")[2:]
        for i in range(len(self.fixture_channels)):
            self.saved_channels[i][1] = int(result[(3*self.fixture_channels[i])-2])

    def fade_channels(self, end_channels, duration):
        """
        Fade lighting channels at 40Hz over a specified duration.
        The lighting system will be blocked during this duration to prevent other
        fades or channel adjustments from affecting the fade.

        Arguments:
        end_channels -- the ending state of the lighting channels, specified as a
        list of [channel number, end value] pairs.
        duration -- the length of the fade in milliseconds.

        Possible exceptions:
        QLCConnectionError -- raised if QLC was not running when Malachi was started
        and/or is not running at present
        LightingBlockedError -- raised if another fade has exclusive use of QLC at present
        """
        if not self.connected:
            raise QLCConnectionError()
        if self.blocked:
            raise LightingBlockedError()
        self.blocked = True
        self.light_socket.send("QLC+API|getChannelsValues|1|1|32")
        result = self.light_socket.recv().split("|")[2:] # [0] = QLC+API, [1] = getChannelsValues
        # result is now [channel, value, details, channel, value, details, ...]
        channel_count = len(end_channels)
        start_channels = [[0 for j in range(2)] for i in range(channel_count)]
        for i in range(channel_count):
            start_channels[i][0] = end_channels[i][0] # Channel number
            start_channels[i][1] = int(result[(3*end_channels[i][0])-2])
        steps = math.floor(duration / 40)
        for i in range(steps+1):
            for c in range(channel_count):
                val = ((end_channels[c][1] - start_channels[c][1])*(i/steps))+start_channels[c][1]
                self.light_socket.send("CH|" + str(end_channels[c][0]) + "|" + str(int(val)))
            time.sleep(0.025)
        # Release lock on LightHandler
        self.blocked = False
