"""
Utility functions for data formatting and string transformations.

Provides helper utilities for transforming database DAO keys (PascalCase/snake_case)
into standard REST API camelCase JSON representations, recursively traversing nested
data structures.
"""

import re
from typing import Any, Dict, List, Union

# Pre-compiled regular expressions for high-performance string parsing
SPLIT_PATTERN = re.compile(r'[_\-\s]+')
WORD_PATTERN = re.compile(
    r'[A-Z]+(?=[A-Z][a-z]|[0-9]|$)|'
    r'[A-Z]?[a-z]+|'
    r'[0-9]+'
)


def to_camel_case(key: Union[str, Any]) -> Union[str, Any]:
    """
    Convert a string key (PascalCase, snake_case, kebab-case, or space-separated) to camelCase.

    Non-string keys (e.g., integer dictionary keys) or empty strings are returned
    unmodified to avoid runtime exceptions.

    Args:
        key (Union[str, Any]): The input key to transform.

    Returns:
        Union[str, Any]: The key transformed to camelCase format if it is a string,
                         otherwise the original key.
    """
    if not isinstance(key, str) or not key:
        return key

    # Split string by underscores, hyphens, or whitespace
    parts = SPLIT_PATTERN.split(key)
    words: List[str] = []

    for part in parts:
        if not part:
            continue
        # Extract subparts (handles acronyms, uppercase-to-lowercase boundaries, and numbers)
        subparts = WORD_PATTERN.findall(part)
        words.extend(subparts or [part])

    if not words:
        return key

    # Lowercase the first word and capitalize subsequent words
    return words[0].lower() + ''.join(
        word[:1].upper() + word[1:].lower()
        for word in words[1:]
    )


def convert_keys(value: Any) -> Any:
    """
    Recursively transform all keys in a dictionary or list structure to camelCase.

    Primitive non-collection values and non-dict/list types are returned unchanged.

    Args:
        value (Any): A dictionary, list, or primitive data structure whose keys
            need camelCase transformation.

    Returns:
        Any: A new dictionary or list with all nested keys converted to camelCase,
             or the original primitive value.
    """
    if isinstance(value, dict):
        return {
            to_camel_case(key): convert_keys(val)
            for key, val in value.items()
        }

    if isinstance(value, list):
        return [convert_keys(item) for item in value]

    return value