"""
When using WlUDPSocket with Water Linked Modem-M64 any 8-byte packet lost will result in loss of the
datagram.

This program generates a table which shows the statistical chance of success for a datagram given a
data size and a given packet loss rate.

"""
import sys
try:
    import tabulate
except ImportError:
    print("Error: tabulate package is needed to show table. Try:")
    print("python3 -m pip install tabulate")
    sys.exit(1)

def main():
    packet_loss_rates = [0.1, 1, 5, 10, 20]

    data = []
    for num_packets in range(1, 33):
        datagram_size = num_packets * 8 - 3  # 3 byte overhead pr packet
        row = ["{:<3} bytes ({:2} packets)".format(datagram_size, num_packets)]
        for drop_rate in packet_loss_rates:
            success = (1.0 - (drop_rate/100.0)) ** num_packets * 100
            row.append("{:5.1f}%".format(success))

        data.append(row)

    header = ["Datagram size"]
    header.extend(["{:.1f}% packetloss".format(x) for x in packet_loss_rates])
    print("Chance of datagram success by given data transfer size")
    print(tabulate.tabulate(data, headers=header, tablefmt="github"))

if __name__ == "__main__":
    main()
