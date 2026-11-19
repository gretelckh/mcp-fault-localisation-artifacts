import re

signals = [
    re.compile(r"Traceback \(most recent call last\):|(?:^|\b)(?:[A-Z]\w*(?:Error|Exception)|ExceptionGroup)\s*:", re.M),
    re.compile(r"^\s*#{1,6}\s*(?:actual(?: behavior| behaviour| result| output)?|observed(?: behavior| behaviour| result| output)?|error(?: message| output| log)?|stack trace|traceback)\b", re.I | re.M),
    re.compile(r"\bHTTP(?:/\d(?:\.\d)?)?\s+[45]\d\d\b|\b(?:connection refused|timed out|permission denied|internal server error)\b", re.I),
]

def excerpt(body):
    """Return an issue-body slice around the first match in priority order."""
    for pattern in signals:
        hit = pattern.search(body)
        if hit:
            start = body.rfind("\n", 0, max(0, hit.start() - 250)) + 1
            return body[start:start + 2000].strip()
    return ""
