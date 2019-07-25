import time

from pymavlink import mavutil


class Pixhawk():
    def __init__(self, url='udpout:0.0.0.0:9000'):
        print("Starting set up")

        # Create the connection
        #  Companion is already configured to allow script connections under the port 9000
        # Note: The connection is done with 'udpout' and not 'udpin'.
        #  You can check in http:192.168.1.2:2770/mavproxy that the communication made for 9000
        #  uses a 'udp' (server) and not 'udpout' (client).
        self.master = mavutil.mavlink_connection(url)

        self._check_conn()

    def disarm(self):
        """
        Disarm the Pixhawk
        """
        self.master.mav.command_long_send(
                                        self.master.target_system,
                                        self.master.target_component,
                                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                                        0,
                                        0, 0, 0, 0, 0, 0, 0)

    def arm(self):
        """
        Arm the Pixhawk
        """
        self.master.mav.command_long_send(
                                        self.master.target_system,
                                        self.master.target_component,
                                        mavutil.mavlink.MAV_CMD_COMPONENT_ARM_DISARM,
                                        0,
                                        1, 0, 0, 0, 0, 0, 0)


    def change_mode(self, mode):
        """
        Change mode of the Pixhawk

        mode (string): New mode of Pixhawk
        """
        # Check if mode is available
        if mode not in self.master.mode_mapping():
            print('Unknown mode : {}'.format(mode))
            print('Try:', list(self.master.mode_mapping().keys()))
            exit(1)

        # Get mode ID
        mode_id = self.master.mode_mapping()[mode]

        self.master.mav.set_mode_send(
            self.master.target_system,
            mavutil.mavlink.MAV_MODE_FLAG_CUSTOM_MODE_ENABLED,
            mode_id)

        # Check ACK
        ack = False
        while not ack:
            # Wait for ACK command
            ack_msg = self.master.recv_match(type='COMMAND_ACK', blocking=True)
            ack_msg = ack_msg.to_dict()

            # Check if command in the same in `set_mode`
            if ack_msg['command'] != mavutil.mavlink.MAVLINK_MSG_ID_SET_MODE:
                continue

            # Print the ACK result !
            print(mavutil.mavlink.enums['MAV_RESULT'][ack_msg['result']].description)
            break

    # Check for server connection
    def _check_conn(self):
        msg = None
        while not msg:
            self.master.mav.ping_send(
                time.time(),  # Unix time
                0,  # Ping number
                0,  # Request ping of all systems
                0  # Request ping of all components
            )
            msg = self.master.recv_match()
            time.sleep(0.5)

        # Wait a heartbeat before sending commands
        self.master.wait_heartbeat()

        print("Set up done!")

    def set_rc_channel_pwm(self, id, pwm=1500):
        """
        Set RC channel pwm value
        id (int): Channel ID
        pwm (int, optional): Channel pwm value 1100-1900

        Channel	Meaning
            1   Pitch
            2   Roll
            3   Up/Down
            4   Yaw
            5   Forward
            6   Lateral
        """

        if id < 1 or id > 8:
            print("Channel does not exist.")
            return

        # We only have 8 channels
        # http://mavlink.org/messages/common#RC_CHANNELS_OVERRIDE
        if id < 8:
            rc_channel_values = [65535 for _ in range(8)]
            rc_channel_values[id - 1] = pwm
            self.master.mav.rc_channels_override_send(
                self.master.target_system,                # target_system
                self.master.target_component,             # target_component
                *rc_channel_values)                  # RC channel list, in microseconds.
