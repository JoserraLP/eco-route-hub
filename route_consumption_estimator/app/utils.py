import re


def to_camel_case(key: str) -> str:
    parts = re.split(r'[_\-\s]+', key)
    words = []

    for part in parts:
        subparts = re.findall(
            r'[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|'
            r'[A-Z]?[a-z]+|'
            r'[0-9]+',
            part
        )
        words.extend(subparts or [part])

    if not words:
        return key

    return words[0].lower() + ''.join(
        word[:1].upper() + word[1:].lower()
        for word in words[1:]
    )


def convert_keys(value):
    if isinstance(value, dict):
        return {
            to_camel_case(key): convert_keys(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [convert_keys(item) for item in value]

    return value
