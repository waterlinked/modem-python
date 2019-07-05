# encoding=utf-8
"""
This is an example of how to do arbitrary size transfers with a Water Linked modem.

Data is optionally compressed and framed with COBS. COBS ensures that \0 does
not occur in the data, so once we receive a \0 we have the full data.
An 8-bit CRC is appended to the frame so we can detect if a packet has been dropped.
The framed data is then split into multiple packets for transmission.
The last packet is padded to reach the full payload size.
(If there is more data to be transmitted, the start of the next frame should be
added to the last packet instead of using pad bytes)

This kind of transfer is suited for small arbitrary size data to be transferred.

This kind of transfer is not suited for larger transfers because a single dropped packet
will result in the full data being corrupted and the full frame having to be retransmitted.
Larger transfers should use a sliding window protocol to ensure the dropped packets are
retransmitted instead of having to retransmit the full data.
"""
from __future__ import division, print_function
import sys
import zlib
import copy
from cobs import cobsr as cobs
import crcmod
from wlmodem import WlModem, WlModemSimulator


crc_func = crcmod.predefined.mkPredefinedCrcFun("crc-8")
PAD_BYTE = 255  # We pad with a non-zero since the Modem-M64 will drop a packet with just zeros
FRAME_END = 0  # COBS guarantees no zeros in the payload

def frame(data, compression=False):
    """ Frame data for transmission """
    if compression:
        data = zlib.compress(data)

    crc = crc_func(data)
    framed = bytearray(data)
    framed.append(crc)
    framed = cobs.encode(framed)
    framed = bytearray(framed)
    framed.append(FRAME_END)
    return framed

def packetize(data, payload_size):
    """ Split data into packets of given payload size. Last packet is padded if needed """
    packets = list()
    buf = copy.copy(data)
    while buf:
        send = buf[:payload_size]
        buf = buf[payload_size:]
        if len(send) < payload_size:
            # Too short, need to add padding
            send = bytearray(send)
            while len(send) < payload_size:
                send.append(PAD_BYTE)

        packets.append(send)
    return packets

def unframe(buffer, compression=False):
    """ Decode frame and return data """
    # Remove terminating 0
    while buffer[-1] == 0:
        buffer.pop()

    try:
        decoded = cobs.decode(buffer)
    except cobs.DecodeError as err:
        print("Decode error {}".format(err))
        return False

    expected_crc = decoded[-1]
    data = decoded[:-1]
    data_crc = crc_func(data)
    if data_crc != expected_crc:
        print("CRC failed. Expected {} Got {}".format(expected_crc, data_crc))
        return False

    if compression:
        return zlib.decompress(data)

    return data


def setup(name, role, channel=4, sim=False):
    """ Setup modem or simulated modem if sim is True """
    if sim:
        modem = WlModemSimulator(0, 0.01, 0.01)
    else:
        modem = WlModem(name)
    if not modem.connect():
        print("Error connecting to modem 1")
        sys.exit(1)

    print("Modem[{}] Set modem role {} and channel {}: ".format(name, role, channel), end="")
    success = modem.cmd_configure(role, channel)
    if success:
        print("success")
    else:
        print("failed")
        sys.exit(1)
    return modem


def main():
    """ Main code """
    sim = True
    if sim:
        # Running on simulated modems
        m_tx = setup("sim", "a", sim=True)
        m_rx = m_tx
    else:
        # Running on actual modems
        m_tx = setup("/dev/ttyUSB0", "a")
        m_rx = setup("/dev/ttyUSB1", "b")

    data = "There is an art, it says, or rather, a knack to flying. The knack lies in learning how to throw yourself at the ground and miss."
    data = bytes(data, "utf-8")  # Need it to be binary data

    enable_compression = False  # Do we compress before transfer?
    framed = frame(data, enable_compression)
    packets = packetize(framed, m_tx.payload_size)

    print("Data size {} Framed size {} Queueing {} packets".format(len(data), len(framed), len(packets)))
    # Send packets to tx modem
    for pkt in packets:
        m_tx.cmd_queue_packet(pkt)

    # Receive packets from rx modem
    received = bytearray()
    cnt = 0
    while True:
        # If the last packet is dropped this will never return, so good idea to add a timeout
        pkt = m_rx.get_data_packet(0.5)
        if pkt:
            cnt += 1
            # Testing dropping a packet:
            # if cnt == 3:
            #    continue
            received.extend(pkt)
            print("Got packet: {}: {}".format(cnt, pkt))
            # If we get a \0 we have a the full data
            if received.find(FRAME_END) >= 0:
                print("Got full data, let's decode it")
                # Remove padding if present
                while received[-1] == PAD_BYTE:
                    received.pop()
                data = unframe(received, enable_compression)
                print("Full data: \n\n{}".format(data))
                break


if __name__ == "__main__":
    main()
