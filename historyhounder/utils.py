from urllib.parse import urlparse
import re
from datetime import datetime

def parse_comma_separated_values(value):
    """Parse comma-separated values, stripping whitespace and filtering empty strings."""
    if not value:
        return []
    return [item.strip() for item in value.split(',') if item.strip()]


def should_ignore(url, ignore_domains, ignore_patterns):
    parsed = urlparse(url)
    domain = parsed.netloc
    for d in ignore_domains:
        if d and d in domain:
            return True
    for pat in ignore_patterns:
        if pat and (re.search(pat, url) or pat in url):
            return True
    return False


def convert_metadata_for_chroma(metadata_dict):
    """Convert metadata values to ChromaDB-compatible types."""
    converted = {}
    for k, v in metadata_dict.items():
        if isinstance(v, datetime):
            converted[k] = v.isoformat()
        elif isinstance(v, (str, int, float, bool)) or v is None:
            converted[k] = v
        else:
            # Convert any other types to string
            converted[k] = str(v)
    return converted 