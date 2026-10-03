"""Thai date and numeral helpers."""
from datetime import date, datetime

MONTHS = ["มกราคม", "กุมภาพันธ์", "มีนาคม", "เมษายน", "พฤษภาคม", "มิถุนายน",
          "กรกฎาคม", "สิงหาคม", "กันยายน", "ตุลาคม", "พฤศจิกายน", "ธันวาคม"]
_DIGITS = str.maketrans("0123456789", "๐๑๒๓๔๕๖๗๘๙")


def thai_digits(text: str) -> str:
    return str(text).translate(_DIGITS)


def thai_date(d: date | datetime | str | None = None, digits: bool = False) -> str:
    """'2026-10-03' -> '3 ตุลาคม 2569'. Unparseable strings are returned unchanged."""
    if d is None:
        d = date.today()
    if isinstance(d, str):
        try:
            d = datetime.strptime(d[:10], "%Y-%m-%d").date()
        except ValueError:
            return d
    out = f"{d.day} {MONTHS[d.month - 1]} {d.year + 543}"
    return thai_digits(out) if digits else out


def file_date(d: date | None = None) -> str:
    """Date as used in company file names, e.g. 03-Oct-26."""
    return (d or date.today()).strftime("%d-%b-%y")
