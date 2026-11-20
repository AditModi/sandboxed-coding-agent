"""Format amounts in Indian rupees.

Indian grouping puts the first comma after three digits and every following comma after
two: 1,00,000 is one lakh and 1,00,00,000 is one crore.
"""


def format_inr(paise: int) -> str:
    """Format an amount given in paise, for example 12345678 -> '₹1,23,456.78'."""
    if isinstance(paise, bool) or not isinstance(paise, int):
        raise TypeError("amount must be an integer number of paise")
    sign = "-" if paise < 0 else ""
    rupees, fraction = divmod(abs(paise), 100)
    # BUG (issue #1): this is international grouping, 123,456 instead of 1,23,456.
    grouped = f"{rupees:,}"
    return f"{sign}₹{grouped}.{fraction:02d}"
