from datetime import datetime

from protocol import DatecsProtocol
from errors import DatecsErrors
from connector import NakException
from response import FiscalResponse

NAK = 0x15
SYN = 0x16
TRM = 0x03

CMD_GET_DATE_TIME = 0x3e        # Read date and time
CMD_SET_DATE_TIME = 0x3d        # Set date and time

CMD_OPEN_FISCAL_RECEIPT = 0x30  # Open fiscal receipt
CMD_FISCAL_SALE = 0x31          # Registration of sale
CMD_TOTAL = 0x35                # Payments and calculation of the total sum (TOTAL)
CMD_FISCAL_CLOSE = 0x38         # Close fiscal receipt
CMD_FISCAL_CANCEL = 0x3C        # Cancel fiscal receipt
CMD_LAST_FISCAL_RECORD = 0x56   # Date of the last fiscal record
CMD_CASH_IN_OUT = 0x46          # Cash in and Cash out operations

CMD_GET_DIAGNOSTIC_INFO = 0x5a  # Diagnostic information
CMD_PROGRAMMING = 0xff          # Programming (X devices only)


class DatecsError(Exception):
    def __init__(self, function, code, message):
        self.function = function
        self.code = code
        self.message = message
        super().__init__(function + ': ' + str(code) + ': ' + message)


class DatecsFiscalDevice:

    def __init__(self, connector, protocol):
        self.connector = connector
        self.protocol = protocol
        self.error_list = DatecsErrors()
        self.last_packet = None
        self.last_slip = None
        self.last_slip_timestamp = None
        self.connected = False

    def connect(self):
        self.connector.connect()
        self.connected = True
        return True

    def disconnect(self):
        self.connector.disconnect()
        self.connected = False

    def send_last_packet(self):
        self.connector.write_data(self.last_packet)

    def wait_response(self):
        response = bytearray()
        terminated = False
        while not terminated:
            rec = self.connector.read_data()
            for b in rec:
                if b == SYN:
                    continue
                if b == NAK:
                    raise NakException
                if b == TRM:
                    terminated = True

                response.append(b)

        return response

    def execute(self, cmd, data=b''):
        if not self.connected:
            raise Exception('Not connected')

        self.last_packet = self.protocol.format_packet(cmd, data)

        self.send_last_packet()  # send cmd
        try:
            response_data = self.wait_response()
        except NakException:  # NAK from ECR
            self.send_last_packet()  # repeat last cmd (with same seq)
            response_data = self.wait_response()

        return FiscalResponse(response_data, self.protocol)

    def get_date_time(self):
        fr = self.execute(CMD_GET_DATE_TIME)
        if self.protocol == DatecsProtocol.X:
            err_index = 0
        else:
            err_index = -1
        if fr.no_errors(err_index, self.error_list):
            if self.protocol == DatecsProtocol.X:
                return datetime.strptime(fr.values[1], '%d-%m-%y %H:%M:%S DST')  # 02-10-19 21:29:42 DST
            elif self.protocol == DatecsProtocol.OLD:
                return datetime.strptime(fr.values[0], '%d-%m-%y %H:%M:%S')  # 02-10-19 21:29:42
        else:
            raise DatecsError('GET_DATE_TIME', fr.error_code, fr.error_message)

    def set_date_time(self, date_time):
        # OLD: DD-MM-YY HH:MM[:SS];
        # X: DD-MM-YY hh:mm:ss DST<SEP>
        if self.protocol == DatecsProtocol.X:
            data = date_time.strftime('%d-%m-%y %H:%M:%S DST') + self.protocol.SEP
            err_index = 0
        else:
            data = date_time.strftime('%d-%m-%y %H:%M:%S')
            err_index = -1

        fr = self.execute(CMD_SET_DATE_TIME, bytearray(data, 'ascii'))

        if fr.no_errors(err_index, self.error_list):
            return fr.ok
        else:
            raise DatecsError('SET_DATE_TIME', fr.error_code, fr.error_message)

    def get_cash_availability(self):
        # X:
        #   Data: {Type}<SEP>{Amount}<SEP>  ('0'-cash in, '1'-cash out)
        #   Answer: {ErrorCode}<SEP>{CashSum}<SEP>{CashIn}<SEP>{CashOut}<SEP>
        # OLD:
        #   Data: [<Amount>]
        #   Answer: ExitCode,CashSum,ServIn,ServOut

        if self.protocol == DatecsProtocol.X:
            data = '0' + self.protocol.SEP + '0.00' + self.protocol.SEP
        else:
            data = '0.00'

        fr = self.execute(CMD_CASH_IN_OUT, bytearray(data, 'ascii'))
        if fr.no_errors(0, self.error_list):
            if self.protocol == DatecsProtocol.X:
                return {'CashSum': float(fr.values[1]),
                        'ServIn': float(fr.values[2]),
                        'ServOut': float(fr.values[3])}
            else:
                return {'CashSum': float(fr.values[1])/100.00,
                        'ServIn': float(fr.values[2])/100.00,
                        'ServOut': float(fr.values[3])/100.00}
        else:
            raise DatecsError('CASH_AVAILABILITY', fr.error_code, fr.error_message)

    def cash_in_out(self, amount):
        # X:
        #   Data: {Type}<SEP>{Amount}<SEP>  ('0'-cash in, '1'-cash out)
        #   Answer: {ErrorCode}<SEP>{CashSum}<SEP>{CashIn}<SEP>{CashOut}<SEP>
        # OLD:
        #   Data: [<Amount>]
        #   Answer: ExitCode,CashSum,ServIn,ServOut

        if self.protocol == DatecsProtocol.X:
            data = '0' if amount > 0 else '-1'
            data += self.protocol.SEP + "{0:.2f}".format(abs(amount)) + self.protocol.SEP
        else:
            data = "{0:.2f}".format(amount)

        fr = self.execute(CMD_CASH_IN_OUT, bytearray(data, 'ascii'))
        if fr.no_errors(0, self.error_list):
            return fr.ok
        else:
            raise DatecsError('CASH_IN_OUT', fr.error_code, fr.error_message)

    def open_fiscal_receipt(self, operator, password, work_place, n_sale):
        # Syntax 1: {OpCode}<SEP>{OpPwd}<SEP>{TillNmb}<SEP>{Invoice}<SEP>
        # Syntax 2: {OpCode}<SEP>{OpPwd}<SEP>{NSale}<SEP>{TillNmb}<SEP>{Invoice}<SEP>
        data = str(operator) + self.protocol.SEP + str(password) + self.protocol.SEP
        if n_sale is not None:
            data += n_sale + self.protocol.SEP
        data += str(work_place) + self.protocol.SEP + self.protocol.SEP

        fr = self.execute(CMD_OPEN_FISCAL_RECEIPT, bytearray(data, 'ascii'))
        if fr.no_errors(0, self.error_list):
            return fr.ok
        else:
            raise DatecsError('OPEN_FISCAL_RECEIPT', fr.error_code, fr.error_message)

    def fiscal_sale(self, plu_name, tax_cd, price, quantity=0, unit=''):
        # OLD: [<L1>][<LF><L2>]<Tab><TaxCd><[Sign]Price>[*<Qwan>][,Perc|;Abs]
        # X:   {PluName}<SEP>{TaxCd}<SEP>{Price}<SEP>{Quantity}<SEP>
        #      {DiscountType}<SEP>{DiscountValue}<SEP>{Department}<SEP>{Unit}<SEP>
        data = str(plu_name) + self.protocol.SEP
        data += str(tax_cd) + self.protocol.SEP
        data += "{0:.2f}".format(price) + self.protocol.SEP
        if quantity > 0:
            data += "{0:.3f}".format(quantity)
        data += 3 * self.protocol.SEP
        data += '0' + self.protocol.SEP     # '0' - without department
        data += unit + self.protocol.SEP

        fr = self.execute(CMD_FISCAL_SALE, bytearray(data, 'ascii'))
        if fr.no_errors(0, self.error_list):
            return fr.ok
        else:
            raise DatecsError('FISCAL_SALE', fr.error_code, fr.error_message)

    def total(self, pay_mode, amount):
        # OLD: [<Line1>][<LF><Line2>]<Tab>[[<PaidMode>]<[Sign]Amount>][*<Type>]
        # X:   {PaidMode}<SEP>{Amount}<SEP>{Type}<SEP>
        data = str(pay_mode) + self.protocol.SEP
        data += "{0:.2f}".format(amount) + 2 * self.protocol.SEP
        fr = self.execute(CMD_TOTAL, bytearray(data, 'ascii'))
        if fr.no_errors(0, self.error_list):
            return fr.ok
        else:
            raise DatecsError('TOTAL', fr.error_code, fr.error_message)

    def open_storno_document(self):
        # Syntax: {OpCode}<SEP>{OpPwd}<SEP>{TillNmb}<SEP>{Storno}<SEP>{DocNum}<SEP>{DateTime}<SEP>
        #         {FMNumber}<SEP>{Invoice}<SEP>{ToInvoice}<SEP>{Reason}<SEP>{NSale}<SEP>
        pass    # todo ...

    def close_bon(self):
        fr = self.execute(CMD_FISCAL_CLOSE)
        if fr.no_errors(0, self.error_list):
            self.last_slip = fr.values[1]       # Current slip number (1...9999999);
            return fr.ok
        else:
            raise DatecsError('FISCAL_CANCEL', fr.error_code, fr.error_message)

    def cancel_bon(self):
        fr = self.execute(CMD_FISCAL_CANCEL)
        if fr.no_errors(0, self.error_list):
            return fr.ok
        else:
            raise DatecsError('FISCAL_CANCEL', fr.error_code, fr.error_message)

    def read_bon_timestamp(self):
        fr = self.execute(CMD_LAST_FISCAL_RECORD)
        if fr.no_errors(0, self.error_list):
            self.last_slip_timestamp = fr.values
            return fr.ok
        else:
            raise DatecsError('LAST_FISCAL_RECORD', fr.error_code, fr.error_message)

    def print(self, bon):
        if bon.storno_reason is None:
            self.open_fiscal_receipt(bon.operator, bon.password, bon.work_place, bon.n_sale)
        else:
            self.open_storno_document()

        try:
            for p in bon.products:
                self.fiscal_sale(p.name, p.tax_cd, p.price, p.quantity, p.unit)
            self.total(bon.pay_mode, bon.payed)
            self.close_bon()
        except Exception:
            self.cancel_bon()
            raise
