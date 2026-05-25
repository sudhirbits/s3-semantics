from datetime import datetime, timezone


def to_iso8601_utc(date_str: str) -> str:
    """
    Convert RFC-1123 or ISO-8601 date string to ISO-8601 UTC format.

    Examples:
      RFC-1123: "Tue, 19 May 2026 05:28:45 GMT"
      ISO-8601: "2026-05-19T05:28:45.000Z"
    """

    if not date_str:
        return "1970-01-01T00:00:00.000Z"

    # Already ISO-8601 (MinIO / S3 preferred)
    if "T" in date_str and date_str.endswith("Z"):
        return date_str

    # RFC-1123 → ISO-8601
    try:
        dt = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT")
        return dt.replace(tzinfo=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%S.000Z"
        )
    except ValueError:
        # Defensive fallback (never break listing)
        return "1970-01-01T00:00:00.000Z"
    

def to_rfc1123_utc(date_str: str) -> str:
    """
    Convert ISO-8601 or RFC-1123 date string to RFC-1123 UTC format.

    Examples:
      ISO-8601: "2026-05-19T05:28:45.000Z"
      RFC-1123: "Tue, 19 May 2026 05:28:45 GMT"
    """

    if not date_str:
        return "Thu, 01 Jan 1970 00:00:00 GMT"

    # Already RFC-1123 (HTTP / headers preferred)
    if "GMT" in date_str and "," in date_str:
        return date_str

    # ISO-8601 → RFC-1123
    try:
        # Accept both with and without milliseconds
        if "." in date_str:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        else:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")

        return dt.replace(tzinfo=timezone.utc).strftime(
            "%a, %d %b %Y %H:%M:%S GMT"
        )
    except ValueError:
        # Defensive fallback (never break responses)
        return "Thu, 01 Jan 1970 00:00:00 GMT"