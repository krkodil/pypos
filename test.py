from ecr import DatecsFiscalDevice
from protocol import DatecsProtocol
from connector import (EthernetConnector, SerialConnector)
from datetime import datetime


if __name__ == '__main__':
    fd = DatecsFiscalDevice(EthernetConnector('192.168.0.36', 4999), DatecsProtocol.X)
    if fd.connect():
        try:
            dt = datetime.now()
            if fd.set_date_time(dt):
                print('Set DateTime to:', dt)
            print('ECR DateTime is:', fd.get_date_time())

            fd.cash_in_out(20.123)
            print('Cash availability:', fd.get_cash_availability())
        finally:
            fd.disconnect()

    fd = DatecsFiscalDevice(SerialConnector('COM1', 115200), DatecsProtocol.OLD)
    if fd.connect():
        try:
            dt = datetime.now()
            if fd.set_date_time(dt):
                print('Set DateTime to:', dt)
            print('ECR DateTime is:', fd.get_date_time())

            print('Cash availability:', fd.get_cash_availability())
        finally:
            fd.disconnect()
