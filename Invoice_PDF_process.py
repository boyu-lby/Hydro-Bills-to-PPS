import Global_variables
from VendorInvoicesExtraction.Get_invoice_extraction import get_invoice_extraction_function
from scan_helper import copy_as_pdf_in_original_and_destination


def invoice_pdf_scan_and_rename(pdf_file_path: str, vendor_name):
    # Use right invoice scanning method
    scanning_method = get_invoice_extraction_function(vendor_name)

    # Extract data from invoice PDF
    results = scanning_method(pdf_file_path)

    # Create a named copy in to_do invoices folder
    copy_as_pdf_in_original_and_destination(pdf_file_path, Global_variables.todo_invoices_dir_path, results['suggested_file_name'])

    # TODO capture error when file or dir not found

