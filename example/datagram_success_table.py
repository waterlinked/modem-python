"""
When using WlUDPSocket with Water Linked Modem-M64 any 8-byte packet lost will result in loss of the
datagram.

This program generates a table which shows the statistical chance of success for a datagram given a
data size and a given packet loss rate.

Typical output of the program:

Chance of datagram success by given data transfer size
| Datagram size          | 0.1% packetloss   | 1.0% packetloss   | 5.0% packetloss   | 10.0% packetloss   | 20.0% packetloss   |
|------------------------|-------------------|-------------------|-------------------|--------------------|--------------------|
| 5   bytes ( 1 packets) | 99.9%             | 99.0%             | 95.0%             | 90.0%              | 80.0%              |
| 13  bytes ( 2 packets) | 99.8%             | 98.0%             | 90.2%             | 81.0%              | 64.0%              |
| 21  bytes ( 3 packets) | 99.7%             | 97.0%             | 85.7%             | 72.9%              | 51.2%              |
| 29  bytes ( 4 packets) | 99.6%             | 96.1%             | 81.5%             | 65.6%              | 41.0%              |
| 37  bytes ( 5 packets) | 99.5%             | 95.1%             | 77.4%             | 59.0%              | 32.8%              |
| 45  bytes ( 6 packets) | 99.4%             | 94.1%             | 73.5%             | 53.1%              | 26.2%              |
| 53  bytes ( 7 packets) | 99.3%             | 93.2%             | 69.8%             | 47.8%              | 21.0%              |
| 61  bytes ( 8 packets) | 99.2%             | 92.3%             | 66.3%             | 43.0%              | 16.8%              |
| 69  bytes ( 9 packets) | 99.1%             | 91.4%             | 63.0%             | 38.7%              | 13.4%              |
| 77  bytes (10 packets) | 99.0%             | 90.4%             | 59.9%             | 34.9%              | 10.7%              |
| 85  bytes (11 packets) | 98.9%             | 89.5%             | 56.9%             | 31.4%              | 8.6%               |
| 93  bytes (12 packets) | 98.8%             | 88.6%             | 54.0%             | 28.2%              | 6.9%               |
| 101 bytes (13 packets) | 98.7%             | 87.8%             | 51.3%             | 25.4%              | 5.5%               |
| 109 bytes (14 packets) | 98.6%             | 86.9%             | 48.8%             | 22.9%              | 4.4%               |
| 117 bytes (15 packets) | 98.5%             | 86.0%             | 46.3%             | 20.6%              | 3.5%               |
| 125 bytes (16 packets) | 98.4%             | 85.1%             | 44.0%             | 18.5%              | 2.8%               |
| 133 bytes (17 packets) | 98.3%             | 84.3%             | 41.8%             | 16.7%              | 2.3%               |
| 141 bytes (18 packets) | 98.2%             | 83.5%             | 39.7%             | 15.0%              | 1.8%               |
| 149 bytes (19 packets) | 98.1%             | 82.6%             | 37.7%             | 13.5%              | 1.4%               |
| 157 bytes (20 packets) | 98.0%             | 81.8%             | 35.8%             | 12.2%              | 1.2%               |
| 165 bytes (21 packets) | 97.9%             | 81.0%             | 34.1%             | 10.9%              | 0.9%               |
| 173 bytes (22 packets) | 97.8%             | 80.2%             | 32.4%             | 9.8%               | 0.7%               |
| 181 bytes (23 packets) | 97.7%             | 79.4%             | 30.7%             | 8.9%               | 0.6%               |
| 189 bytes (24 packets) | 97.6%             | 78.6%             | 29.2%             | 8.0%               | 0.5%               |
| 197 bytes (25 packets) | 97.5%             | 77.8%             | 27.7%             | 7.2%               | 0.4%               |
| 205 bytes (26 packets) | 97.4%             | 77.0%             | 26.4%             | 6.5%               | 0.3%               |
| 213 bytes (27 packets) | 97.3%             | 76.2%             | 25.0%             | 5.8%               | 0.2%               |
| 221 bytes (28 packets) | 97.2%             | 75.5%             | 23.8%             | 5.2%               | 0.2%               |
| 229 bytes (29 packets) | 97.1%             | 74.7%             | 22.6%             | 4.7%               | 0.2%               |
| 237 bytes (30 packets) | 97.0%             | 74.0%             | 21.5%             | 4.2%               | 0.1%               |
| 245 bytes (31 packets) | 96.9%             | 73.2%             | 20.4%             | 3.8%               | 0.1%               |
| 253 bytes (32 packets) | 96.8%             | 72.5%             | 19.4%             | 3.4%               | 0.1%               |

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
