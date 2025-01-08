import pdfplumber
import re
import fitz

def draw_red_box_on_pdf(
    input_pdf_path,
    output_pdf_path,
    page_number=0,
    x0=100,
    y0=100,
    x1=200,
    y1=200
):
    """
    Draws a red rectangle on a page in the PDF, between coordinates (x0, y0) and (x1, y1).

    :param input_pdf_path: Path to the input PDF file.
    :param output_pdf_path: Path where the output PDF will be saved.
    :param page_number: The page index (0-based) on which to draw the rectangle.
    :param x0: The left X coordinate of the rectangle.
    :param y0: The top Y coordinate of the rectangle.
    :param x1: The right X coordinate of the rectangle.
    :param y1: The bottom Y coordinate of the rectangle.
    """
    # Open the PDF
    doc = fitz.open(input_pdf_path)

    # Ensure the page_number is valid
    if page_number < 0 or page_number >= len(doc):
        raise ValueError(f"Invalid page_number: {page_number}. PDF has {len(doc)} pages.")

    # Select the page
    page = doc[page_number]

    # Create a new "Shape" to draw on
    shape = page.new_shape()

    shape.draw_rect(fitz.Rect(x0, y0, x1, y1))
    shape.finish(color=(1, 0, 0), fill=None, width=2)
    shape.commit()
    doc.save(output_pdf_path)
    doc.close()

def parse_hydro_bill(pdf_path):
    """
    Parse the hydro bill PDF and extract key fields:
    - Account Number
    - Statement Date
    - Amount Due
    - Your Total Electricity Charges
    - H.S.T.
    - Ontario Electricity Rebate
    - Balance Forward
    - Period Start Date
    - Period End Date
    """
    # Initialize a dictionary to store extracted data
    extracted_data = {
        "account_number": None,
        "statement_date": None,
        "amount_due": None,
        "total_electricity_charges": None,
        "hst": None,
        "ontario_electricity_rebate": None,
        "balance_forward": None,
        "period_start_date": None,
        "period_end_date": None
    }

    with pdfplumber.open(pdf_path) as pdf:
        # If your data is always on page 1, just reference pdf.pages[0].
        page = pdf.pages[0]
        text = ""
        text += page.extract_text() + "\n"
        # ---------------------------------------------------------------------
        # 1) ACCOUNT NUMBER BY CROPPING
        #    Suppose we know that “Account Number” text and the actual number
        #    are in a region from x=50 to x=300, y=100 to y=150.
        #    (Coordinates will differ in your PDF.)
        # ---------------------------------------------------------------------
        account_bbox = (50, 100, 300, 150)
        cropped_account = page.crop(account_bbox)

        # Extract the text in that region
        account_text = cropped_account.extract_text() or ""

        # Now parse the text. Possibly the text is something like:
        #   "Account Number\n5697020993"
        # or "5697020993\nAccount Number"
        # so we can search for a sequence of digits near the phrase “Account Number”.
        import re
        match = re.search(r'(\d{8,})', account_text)  # capture a big chunk of digits
        if match:
            extracted_data["account_number"] = match.group(1)

    # 2) Statement Date
    # Example snippet: "Statement Date Dec 11 2024"
    match = re.search(r'Statement\s*Date\s*([A-Za-z]{3}\s*\d{1,2}\s*\d{4})', text, re.IGNORECASE)
    if match:
        extracted_data["statement_date"] = match.group(1)

    # 3) Amount Due
    # Example snippet: "Amount Due $168.60"
    match = re.search(r'Amount\s*Due\s*\$?(\d+\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["amount_due"] = match.group(1)

    # 4) Your Total Electricity Charges
    # Example snippet: "Your Total Electricity Charges 82.72"
    match = re.search(r'Your\s*Total\s*Electricity\s*Charges\s*(\d+\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["total_electricity_charges"] = match.group(1)

    # 5) H.S.T.
    # Example snippet: "H.S.T. 10.75" or "H.S.T. (H.S.T. Registration 895...) 10.75"
    # We'll capture the number. You might refine this if the text includes extra info on the same line.
    match = re.search(r'H\.S\.T\.\s*\(?[^\)]*\)?\s*(\d+\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["hst"] = match.group(1)

    # 6) Ontario Electricity Rebate
    # Example snippet: "Ontario Electricity Rebate 10.84 CR"
    # The actual amount might come before "CR", so we can capture the numeric portion.
    match = re.search(r'Ontario\s*Electricity\s*Rebate\s*([\d\.]+)', text, re.IGNORECASE)
    if match:
        extracted_data["ontario_electricity_rebate"] = match.group(1)

    # 7) Balance Forward
    # Example snippet: "Balance Forward 85.97"
    match = re.search(r'Balance\s*Forward\s*(\d+\.\d{1,2})', text, re.IGNORECASE)
    if match:
        extracted_data["balance_forward"] = match.group(1)

    # 8) Period
    # Example snippet: "NOV 07 2024 TO DEC 05 2024"
    pattern = r'([A-Za-z]{3}\s*\d{1,2}\s*\d{4})\s*TO\s*([A-Za-z]{3}\s*\d{1,2}\s*\d{4})'

    match = re.search(pattern, text, re.IGNORECASE)
    if match:
        extracted_data["period_start_date"] = match.group(1)
        extracted_data["period_end_date"] = match.group(2)

    # Return or print the extracted data
    return extracted_data


if __name__ == "__main__":
    # Example usage:
    pdf_file_path = "D:\Downloads\Hydro_bill_selected.pdf"
    results = parse_hydro_bill(pdf_file_path)
    print("Extracted Data:")
    for key, value in results.items():
        print(f"{key}: {value}")

    draw_red_box_on_pdf(
        input_pdf_path="D:\Downloads\Hydro_bill.pdf",
        output_pdf_path="D:\Downloads\example_with_box.pdf",
        page_number=0,
        x0=370,
        y0=250,
        x1=500,
        y1=450
    )
    print("Red rectangle has been drawn and saved to 'example_with_box.pdf'.")

# See PyCharm help at https://www.jetbrains.com/help/pycharm/
