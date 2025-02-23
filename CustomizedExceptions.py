class SaveableError(Exception):
    """Payment is saved when Exception raised."""
    def __init__(self, account_number, message):
        self.account_number = account_number
        self.message = message


class UnsaveableError(Exception):
    """Payment is unsaved when Exception raised."""
    def __init__(self, account_number, message):
        self.account_number = account_number
        self.message = message


class OCRFindingError(UnsaveableError):
    """Exception raised when a text is not found."""
    def __init__(self, account_number):
        UnsaveableError.__init__(self, account_number, "OCR system error, it is developer's fault")

class PendingPaymentError(UnsaveableError):
    """Exception raised when previous invoice is pending"""
    def __init__(self, account_number):
        UnsaveableError.__init__(self, account_number, "already has a pending payment")

class AmountError(UnsaveableError):
    """Exception raised when the sum of various amount does not match the total"""
    def __init__(self, account_number):
        UnsaveableError.__init__(self, account_number, "has unmatched amount")

class InvoiceScanError(UnsaveableError):
    """Exception raised when invoice scanning failed"""
    def __init__(self, account_number):
        UnsaveableError.__init__(self, account_number, "failed on invoice scanning")

class RequestApprovalError(SaveableError):
    """Exception raised when approval request failed"""
    def __init__(self, account_number):
        SaveableError.__init__(self, account_number, "failed on requesting approval")

class AccountNumberError(UnsaveableError):
    """Exception raised when correct account number not found"""
    def __init__(self, account_number):
        UnsaveableError.__init__(self, account_number, "failed on locating account number")

class ExtractedDataUnmatchError(UnsaveableError):
    """Exception raised when amount does not match"""
    def __init__(self, account_number):
        UnsaveableError.__init__(self, account_number, "has unmatch amount")

