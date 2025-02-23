import math
import numbers
import re

import numpy as np
import pyautogui
import pytesseract
from pytesseract import Output
from PIL import ImageGrab, Image
import cv2
from datetime import datetime
from pynput.keyboard import Controller as KeyboardController, Key
from pynput.mouse import Controller as MouseController, Button
import time

from CustomizedExceptions import OCRFindingError


def tesseract_test(image_path):
    text = pytesseract.image_to_string(Image.open(image_path))
    print(text)

def img_test():
    screenshot = ImageGrab.grab()
    img = np.array(screenshot.convert('L'))
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    cv2.imshow("Thresholded Image", thresh)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

def only_space_and_symbol(text):
    """
    Returns True if 'text' contains only spaces (whitespace)
    and symbols (non-alphanumeric chars). Otherwise, returns False.
    """
    for ch in text:
        # If the character is alphanumeric (a-z, A-Z, 0-9), fail immediately
        if ch.isalnum():
            return False
    # If we never found an alphanumeric character, it's only space or symbol
    return True


def img_to_gray(img):
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    return gray

def recognize_text(image, thresh_hold = True):
    if not thresh_hold:
        return pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    # 1 Convert PIL to NP array
    img = np.array(image.convert('L'))

    # 2 Thresh holding
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

    # 3 Convert NP array to PIL
    pil_thresh = Image.fromarray(thresh)

    # 4. Perform OCR on the image
    #    Use 'image_to_data' to get detailed info, including bounding boxes
    return pytesseract.image_to_data(pil_thresh, output_type=pytesseract.Output.DICT)

def recognize_text_by_DE(image, thresh_hold = True):
    if not thresh_hold:
        return pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)

    # 1 Convert PIL to NP array
    img = np.array(image.convert('L'))

    # 2 Thresh holding
    _, thresh = cv2.threshold(img, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (2, 1))
    dilated = cv2.dilate(thresh, kernel, iterations=1)

    # 3 Convert NP array to PIL
    pil_thresh = Image.fromarray(dilated)

    # 4. Perform OCR on the image
    #    Use 'image_to_data' to get detailed info, including bounding boxes
    return pytesseract.image_to_data(pil_thresh, output_type=pytesseract.Output.DICT)


def print_words_on_screen(thresh_hold=True, de=False):
    if de:
        ocr_data = recognize_text_by_DE(ImageGrab.grab(), thresh_hold)
    else:
        ocr_data = recognize_text(ImageGrab.grab(), thresh_hold)

    raw_text_data = []

    # 3. Iterate over the OCR results
    for i in range(len(ocr_data['text'])):
        word = ocr_data['text'][i]
        conf = int(ocr_data['conf'][i]) if isinstance(ocr_data['conf'][i], numbers.Number) else -1
        if conf != -1 and not only_space_and_symbol(word):
            raw_text_data.append(word)

    print("raw_text_data: ")
    print(raw_text_data)
    print(f"Total word count: {len(raw_text_data)}")


def find_text_position(text_to_find, confidence_threshold=80, notification=True):
    """
    Takes a screenshot of the entire screen, uses Tesseract to find text positions,
    and returns the bounding box of the first match above the confidence threshold.
    """
    # 1. recognize the text on screen
    ocr_data = recognize_text(ImageGrab.grab())

    found_positions = []

    # 3. Iterate over the OCR results
    for i in range(len(ocr_data['text'])):
        word = ocr_data['text'][i]
        conf = int(ocr_data['conf'][i]) if isinstance(ocr_data['conf'][i], numbers.Number) else -1

        # If the recognized word matches your search text
        # and the confidence is above threshold, record the bounding box
        if word.lower() == text_to_find.lower() and conf >= confidence_threshold:
            x, y = ocr_data['left'][i], ocr_data['top'][i]
            w, h = ocr_data['width'][i], ocr_data['height'][i]
            found_positions.append((x, y, w, h))

    # If we found matches, return the first bounding box
    if found_positions:
        return found_positions[0]  # (x, y, width, height)
    else:
        if notification:
            print(f"{text_to_find} Not Found")
        return None


def click_on_text(text_to_click, confidence_threshold=80):
    """
    Finds the text on the screen and simulates a mouse click on it.
    Return 0 if nothing found, return 1 if success
    """

    position = find_text_position(text_to_click, confidence_threshold)
    if position is None:
        print(f"Text '{text_to_click}' not found!")
        return 0

    x, y, w, h = position

    # Calculate a center point for the bounding box
    center_x = x + w // 2
    center_y = y + h // 2

    # 4. Move the mouse and click
    click_by_coordinate(center_x, center_y)
    print(f"Clicked on text '{text_to_click}' at ({center_x}, {center_y}).")
    return 1

def click_by_coordinate(x, y):
    pyautogui.moveTo(x, y, duration=0.2)  # Move smoothly over 0.2s
    pyautogui.click()

def press_enter():
    keyboard = KeyboardController()
    keyboard.press(Key.enter)
    keyboard.release(Key.enter)

def input_text(input_string):
    """
    Simulates keyboard input events, typing out the given string with
    a 0.05-second delay between each character.

    Args:
        input_string (str): The string to be typed.
    """
    keyboard = KeyboardController()

    for char in input_string:
        keyboard.type(char)
        time.sleep(0.05)  # Wait 0.05 seconds between typing each character
    print(f"Inputted Text: '{input_string}'")

def double_click():
    """
    Simulates a mouse double-click at the current cursor position.
    """
    mouse = MouseController()
    mouse.click(Button.left, 2)  # Perform a double click (2 clicks)

def press_backspace(times=1):
    """
    Simulates pressing the backspace key.

    Args:
        times (int): Number of times to press backspace. Default is 1.
    """
    keyboard = KeyboardController()
    for _ in range(times):
        keyboard.press(Key.backspace)
        keyboard.release(Key.backspace)

def clear_input_bar():
    double_click()
    press_backspace()


def scroll_up(clicks):
    """
    Scroll up by a certain amount (positive value).
    """

    # Positive values = scroll up, Negative values = scroll down
    pyautogui.scroll(clicks)

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


def remove_special_characters(input_string):
    return re.sub(r'[^a-zA-Z0-9]', '', input_string)

def find_button(text_to_find, order=1, threshhold = True, de=False):
    """
    Find the (order)th text_to_find on the screen.
    order=-1 means find the last one
    """

    # Split the text by space
    string_lst = text_to_find.lower().split(" ")
    if not string_lst:
        raise ValueError("No Input Text in click_button_by_text()")
    # recognize the text on screen
    if de:
        ocr_data = recognize_text_by_DE(ImageGrab.grab(), threshhold)
    else:
        ocr_data = recognize_text(ImageGrab.grab(), threshhold)

    # Record how many times the text is found
    times_of_found = 0

    # Record where the last match text occurs
    last_occur = -1

    # Iterate through the recognized texts
    check_point = 0
    for i, word in enumerate(ocr_data["text"]):
        index = 0
        while remove_special_characters(ocr_data["text"][i + index].strip().lower()) == string_lst[index]:
            index += 1
            # If reach the end of string_lst, means text is found
            if not (index < len(string_lst)):
                times_of_found += 1
                if times_of_found == order:
                    # Get coordinate
                    x, y = ocr_data["left"][i], ocr_data["top"][i]
                    w, h = ocr_data["width"][i], ocr_data["height"][i]
                    return x, y, w, h
                last_occur = i
                break
    if last_occur != -1 and order == -1:
        # Get coordinate
        x, y = ocr_data["left"][last_occur], ocr_data["top"][last_occur]
        w, h = ocr_data["width"][last_occur], ocr_data["height"][last_occur]
        return x, y, w, h

    return None

def click_button_by_text(text_to_find, order=1, threshhold = True):
    """
    Find the (order)th text_to_find on the screen.
    order=-1 means find the last one
    And click on it
    """
    position = find_button(text_to_find, order, threshhold, False)
    if position is None:
        position = find_button(text_to_find, order, threshhold, True)
    if position is None:
        raise OCRFindingError(text_to_find)
    x, y, w, h = position
    center_x = x + w // 2
    center_y = y + h // 2

    # Move mouse & click
    pyautogui.moveTo(center_x, center_y, duration=0.2)
    pyautogui.click()

    print(f"Clicked on '{text_to_find}'")
    return


def check_page_loading(iter_times = 0):
    time.sleep(0.1)
    if iter_times > 50:
        raise TimeoutError("Processing takes too long")
    position = find_text_position("Processing...", notification=False)
    time.sleep(0.1)
    if position:
        check_page_loading(iter_times + 1)
    return


def hex_to_rgb(hex_color):
    """
    Convert a hex color string like '#12ABFF' into an (R, G, B) tuple.
    """
    # Remove any leading '#' if present
    hex_color = hex_color.lstrip('#')

    # Parse the R, G, B values
    r = int(hex_color[0:2], 16)
    g = int(hex_color[2:4], 16)
    b = int(hex_color[4:6], 16)

    return (r, g, b)


def click_on_color(hex_color):
    """
    Search the entire screen for the given hex color.
    Once found, move the mouse to that pixel and click.

    Returns True if the color was found and clicked, False otherwise.
    """
    # Convert the hex color to an (R, G, B) tuple
    target_color = hex_to_rgb(hex_color)

    # Capture a screenshot of the entire screen
    screenshot = pyautogui.screenshot()

    # Get the width and height of the screenshot
    width, height = screenshot.size

    # Load pixel data (so we can read colors quickly in memory)
    pixel_data = screenshot.load()

    # Iterate over every pixel (x, y) in the screenshot
    for x in range(width):
        for y in range(height):
            if pixel_data[x, y] == target_color:
                # Found a matching pixel!
                pyautogui.moveTo(x, y)
                pyautogui.click()
                return True

    # If no matching color is found, return False
    return False

def click_on_color_bottom_first(hex_color):
    target_color = hex_to_rgb(hex_color)
    screenshot = pyautogui.screenshot()
    width, height = screenshot.size
    pixel_data = screenshot.load()

    # Iterate from bottom to top
    for y in range(height - 1, -1, -1):  # height-1 down to 0
        for x in range(width):
            if pixel_data[x, y] == target_color:
                pyautogui.moveTo(x, y)
                pyautogui.click()
                return True
    return False