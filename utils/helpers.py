# C:/.../comphone_integrated/utils/helpers.py

import random
import string
from datetime import datetime

def generate_receipt_number():
    """
    Generates a unique receipt number based on the current timestamp.
    Example: R-20250715-1701-A3B4
    """
    now = datetime.now()
    date_part = now.strftime("%Y%m%d-%H%M")
    random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    return f"R-{date_part}-{random_part}"

def format_currency(amount, currency_symbol='฿'):
    """
    Formats a number as currency.
    Example: 1234.5 -> ฿1,234.50
    """
    if amount is None:
        return f"{currency_symbol}0.00"
    return f"{currency_symbol}{float(amount):,.2f}"

def generate_random_string(length=8):
    """
    Generates a random string of a given length.
    """
    letters = string.ascii_lowercase + string.digits
    return ''.join(random.choice(letters) for i in range(length))