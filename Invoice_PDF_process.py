import Global_variables
from CustomizedExceptions import UnsaveableError
from VendorInvoicesExtraction.Get_invoice_extraction import get_invoice_extraction_function
from scan_helper import copy_as_pdf_in_original_and_destination, self_check


def invoice_pdf_scan_and_rename(pdf_file_path: str, vendor_name: str) -> (bool, str):
    """
    Scan the hydro bill in PDF format, create a copy and rename it, then save it to to_do invoices folder
    :param pdf_file_path:
    :param vendor_name:
    :return: bool (indicates success or not), str (name if success, path if fail)
    """
    # Use right invoice scanning method
    scanning_method = get_invoice_extraction_function(vendor_name)

    # Extract data from invoice PDF
    try:
        results = scanning_method(pdf_file_path)
    except Exception as e:
        return False, pdf_file_path

    if results['suggested_file_name'] is None:
        return False, pdf_file_path

    # Create a named copy in to_do invoices folder
    copy_as_pdf_in_original_and_destination(pdf_file_path, Global_variables.todo_invoices_dir_path, results['suggested_file_name'])

    return True, results['suggested_file_name']

