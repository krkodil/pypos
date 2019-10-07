from ecr import DatecsFiscalDevice
from protocol import DatecsProtocol
from connector import EthernetConnector
from datetime import datetime


if __name__ == '__main__':
    fd = DatecsFiscalDevice(EthernetConnector('192.168.0.36', 4999), DatecsProtocol.X)
    if fd.connect():
        try:
            fd.set_date_time(datetime.now())
            print(fd.get_date_time())
        finally:
            fd.disconnect()
