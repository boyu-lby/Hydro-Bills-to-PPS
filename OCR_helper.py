from datetime import datetime

def convert_date(date_str):
    """
    Converts a date string from 'MMM DD YYYY' to 'DD/MM/YYYY'.

    Example:
      Input:  "JAN 24 2024"
      Output: "24/01/2024"
    """
    # Parse the date string using strptime with the format '%b %d %Y'
    dt = datetime.strptime(date_str, "%b %d %Y")

    # Return a string in 'DD/MM/YYYY' format using strftime
    return dt.strftime("%d/%m/%Y")

def get_today_date():
    """
    Returns today's date in 'DD/MM/YYYY' format.

    Example:
      If today is January 24, 2024,
      the function returns "24/01/2024".
    """
    return datetime.now().strftime("%d/%m/%Y")


def convert_month_abbr(three_letter_month):
    """
    Converts a three-letter month abbreviation to a unique two-letter code
    using a predefined lookup table.
    """
    month_map = {
        "Jan": "Ja",
        "Feb": "Fe",
        # Decide how you want to handle March vs. May:
        "Mar": "Mr",  # Example: "Mar" => "Mr"
        "Apr": "Ap",
        "May": "My",  # Example: "May" => "My"
        # Decide how you want to handle June vs. July:
        "Jun": "Jn",  # Example: "Jun" => "Jn"
        "Jul": "Jl",  # Example: "Jul" => "Jl"
        "Aug": "Au",
        "Sep": "Se",
        "Oct": "Oc",
        "Nov": "No",
        "Dec": "De"
    }

    # Normalize input to the form "Xxx" (e.g., 'jan' -> 'Jan') to match dictionary keys
    standardized = three_letter_month.capitalize()

    return month_map.get(standardized, "??").upper()  # "??" for unrecognized abbreviations
