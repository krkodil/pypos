from ecr import FiscalDevice
from protocol import DatecsProtocol
from connector import EthernetConnector

fd = FiscalDevice(EthernetConnector('192.168.0.36', 4999), DatecsProtocol.X)
if fd.connect():
    try:
        print(fd.get_date_time())
    finally:
        fd.disconnect()
