# utils.py
"""Utility functions for the Quant platform.

Currently provides:
- format_number(value, decimals=2): Return a string with thousand separators and fixed decimal places.
"""

def format_number(value, decimals=2):
    """Format a numeric value with commas and a given number of decimal places.
    Args:
        value (int|float): The number to format.
        decimals (int): Number of digits after the decimal point.
    Returns:
        str: Formatted string, e.g., 1234567.891 -> "1,234,567.89".
    """
    try:
        return f"{float(value):,.{decimals}f}"
    except Exception:
        # Fallback to string conversion if formatting fails
        return str(value)
