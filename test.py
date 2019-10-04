from ecr import DatecsFiscalDevice
from protocol import DatecsProtocol
from connector import EthernetConnector


if __name__ == '__main__':
    fd = DatecsFiscalDevice(EthernetConnector('192.168.0.36', 4999), DatecsProtocol.X)
    if fd.connect():
        try:
            print(fd.get_date_time())
        finally:
            fd.disconnect()
