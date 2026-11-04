"""utils.py - small helper functions used by several files."""
import re

_NUMWORDS = {"half": 0.5, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
             "eight": 8, "nine": 9, "ten": 10, "fifteen": 15, "twenty": 20, "thirty": 30,
             "forty": 40, "fifty": 50, "sixty": 60, "ninety": 90}


def squash(text: str) -> str:
    """Lower-case and keep only letters, digits and %, so line breaks / spacing never break a match."""
    return re.sub(r"[^a-z0-9%]", "", (text or "").lower())


def numbers_in_text(text: str):
    """All numbers that appear in a text, including words like 'five' and the symbol 1/2."""
    text = (text or "").lower().replace("½", " 0.5 ").replace("1/2", " 0.5 ")
    nums = [float(x) for x in re.findall(r"\d+(?:\.\d+)?", text)]
    for w, v in _NUMWORDS.items():
        if re.search(rf"\b{w}\b", text):
            nums.append(float(v))
    return nums


def to_per_week(value, unit):
    """Convert a delay-damages rate to '% per week' so rates can be compared fairly."""
    if value is None:
        return None
    u = (unit or "").lower()
    if "day" in u:
        return value * 7
    if "month" in u:
        return value * 12 / 52
    return value  # assume it is already per week


def days_to_calendar(days, day_type):
    """Working days -> approximate calendar days (5 working days = 7 calendar days)."""
    if days is None:
        return None
    return days * 7 / 5 if (day_type or "").lower().startswith("work") else days
