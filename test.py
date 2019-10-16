from bon import (FiscalBon, Product, PayMode)
from ecr import DatecsFiscalDevice
from protocol import DatecsProtocol
from connector import (EthernetConnector, SerialConnector)
from datetime import datetime


if __name__ == '__main__':
    fd = DatecsFiscalDevice(EthernetConnector('192.168.0.36', 4999), DatecsProtocol.X)
    if fd.connect():
        try:
            print('Connected ECR: {0:s}, SN: {1:s}'.format(fd.model, fd.serial_number))

            dt = datetime.now()
            if fd.set_date_time(dt):
                print('Set DateTime to:', dt)
            print('ECR DateTime is:', fd.get_date_time())
            
            fd.cash_in_out(20.123)
            print('Cash availability:', fd.get_cash_availability())

            n_sale = '{0:s}-{1:04d}-{2:07d}'.format(fd.serial_number, 1, 2123)

            with FiscalBon(1, 1, 1, n_sale) as bon:
                bon.add(Product('Potatoes', 2.350, 0.85, 'kg'))
                bon.add(Product('Tomatoes', 1.200, 2.50, 'kg'))
                bon.close(5.00, PayMode.CARD)
                fd.print(bon)

            print('Last slip:', fd.last_slip)

        finally:
            fd.disconnect()

    fd = DatecsFiscalDevice(SerialConnector('COM1', 115200), DatecsProtocol.OLD)
    if fd.connect():
        try:
            print('Connected ECR: {0:s}, SN: {1:s}'.format(fd.model, fd.serial_number))

            dt = datetime.now()
            if fd.set_date_time(dt):
                print('Set DateTime to:', dt)
            print('ECR DateTime is:', fd.get_date_time())

            print('Cash availability:', fd.get_cash_availability())

        finally:
            fd.disconnect()
