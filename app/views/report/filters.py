def parse_int_or_none(value: str | None) -> int | None:
    if value is None:
        return None
    if str(value).strip() == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_report_period(value: str | None) -> tuple[int | None, int | None]:
    if not value:
        return None, None

    raw = str(value).strip()
    if "/" in raw:
        parts = raw.split("/")
        if len(parts) == 2:
            month = parse_int_or_none(parts[0])
            year = parse_int_or_none(parts[1])
            return month, year

    if "-" in raw:
        parts = raw.split("-")
        if len(parts) == 2:
            year = parse_int_or_none(parts[0])
            month = parse_int_or_none(parts[1])
            return month, year

    return None, None
