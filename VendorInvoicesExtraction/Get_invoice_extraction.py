from VendorInvoicesExtraction.NPE import parse_NPE_bill
from VendorInvoicesExtraction.NTP import parse_NTP_bill
from VendorInvoicesExtraction.alectra_scan import parse_alectra_bill
from VendorInvoicesExtraction.burlington_hydro_scan import parse_burlington_hydro_bill
from VendorInvoicesExtraction.elexicon import parse_elexicon_bill
from VendorInvoicesExtraction.fortis_scan import parse_fortis_bill
from VendorInvoicesExtraction.grimsby import parse_grimsby_bill
from VendorInvoicesExtraction.hydro_one import parse_hydro_one_bill
from VendorInvoicesExtraction.toronto_hydro_scan import parse_toronto_hydro_bill
from VendorInvoicesExtraction.welland_scan import parse_welland_bill


def get_invoice_extraction_function(vendor_name: str):
    functions = {
        "Alectra": parse_alectra_bill,
        "Burlington": parse_burlington_hydro_bill,
        "Elexicon": parse_elexicon_bill,
        "Fortis": parse_fortis_bill,
        "Grimsby": parse_grimsby_bill,
        "Hydro One": parse_hydro_one_bill,
        "NPE": parse_NPE_bill,
        "NTP": parse_NTP_bill,
        "Toronto Hydro": parse_toronto_hydro_bill,
        "Welland": parse_welland_bill,
    }
    if vendor_name not in functions:
        return None
    return functions[vendor_name]