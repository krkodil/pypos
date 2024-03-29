
class FiscalResponse:
    def __init__(self, packet, protocol):
        self.data = protocol.get_data(packet)
        self.values = self.data.split(protocol.SEP)
        self.status_bytes = protocol.get_status(packet)
        self.ok = not (self.general_error() or self.cover_open())
        self.error_code = 0
        self.error_message = ''

    def no_errors(self, err_index, error_list):
        if err_index >= 0:
            if self.values[err_index] == 'P':
                self.error_code = 0         # Operation successful
            else:
                if self.values[err_index] == 'F':
                    self.error_code = -20   # Command failed
                else:
                    self.error_code = int(self.values[err_index])

            self.error_message = error_list.get_message(self.error_code)
            self.ok = self.ok & self.error_code is 0
        return self.ok

    def bit_on(self, x, n):
        return self.status_bytes[x] & 1 << n-1 != 0

    def cover_open(self): return self.bit_on(0, 6)
    def general_error(self): return self.bit_on(0, 5)
    def mechanism_failure(self): return self.bit_on(0, 4)
    def rtc_not_synchronized(self): return self.bit_on(0, 2)
    def invalid_command(self): return self.bit_on(0, 1)
    def syntax_error(self): return self.bit_on(0, 0)
    def command_not_permitted(self): return self.bit_on(1, 1)
    def overflow_during_command(self): return self.bit_on(1, 0)
    def nonfiscal_receipt_open(self): return self.bit_on(2, 5)
    def fiscal_receipt_open(self): return self.bit_on(2, 3)
    def end_of_paper(self): return self.bit_on(2, 0)
