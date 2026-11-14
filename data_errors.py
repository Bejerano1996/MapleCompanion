"""Concise, actionable background errors; full details remain local."""
import re


def data_error_status(message):
    text = str(message)
    code = re.search(r"HTTP\s*(?:Error\s*)?[:=]?\s*(403|404|429|5\d\d)\b", text, re.I)
    if code:
        value = int(code.group(1))
        if value == 403:
            return "Source rejected request (HTTP 403)"
        if value == 404:
            return "Source page or image unavailable (HTTP 404)"
        if value == 429:
            return "Source rate limit (HTTP 429) · retry later"
        return f"Source temporarily unavailable (HTTP {value})"
    lower = text.casefold()
    if 'certificate' in lower or 'ssl' in lower:
        return "HTTPS verification failed · see details"
    if 'timed out' in lower or 'timeout' in lower:
        return "Connection timed out · retry later"
    if 'getaddrinfo' in lower or 'name resolution' in lower:
        return "Cannot reach data source · check connection"
    return "Background task failed · hover for details"
