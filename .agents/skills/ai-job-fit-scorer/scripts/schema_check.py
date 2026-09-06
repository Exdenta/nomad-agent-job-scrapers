"""Offline checker for the keyword subset used by the bundled Actor schemas.

Not a general JSON Schema implementation. Unsupported schema keywords fail
closed so a future schema update cannot silently weaken validation.
"""
from __future__ import annotations
import json
import math
import re
from pathlib import Path
from typing import Any

ANNOTATIONS = {'$schema', '$id', 'title', 'description', 'default', 'examples'}
KEYWORDS = {'type', 'required', 'properties', 'additionalProperties', 'const', 'enum',
            'minimum', 'maximum', 'minLength', 'pattern', 'items', 'allOf', 'if', 'then'}


def equal(a: Any, b: Any) -> bool:
    if isinstance(a, bool) != isinstance(b, bool):
        return False
    return a == b


def matches(value: Any, kind: str) -> bool:
    return {'null': value is None, 'object': isinstance(value, dict),
            'array': isinstance(value, list), 'string': isinstance(value, str),
            'boolean': type(value) is bool, 'integer': type(value) is int,
            'number': type(value) in (int, float) and math.isfinite(value)}[kind]


def check(value: Any, schema: dict, path: str = 'value') -> None:
    unsupported = set(schema) - KEYWORDS - ANNOTATIONS
    if unsupported:
        raise ValueError(f'{path}: unsupported schema keywords {sorted(unsupported)}')
    if type(value) is float and not math.isfinite(value):
        raise ValueError(f'{path}: non-finite number')
    types = schema.get('type')
    if types and not any(matches(value, t) for t in ([types] if isinstance(types, str) else types)):
        raise ValueError(f'{path}: expected {types}')
    if 'const' in schema and not equal(value, schema['const']):
        raise ValueError(f'{path}: expected constant {schema["const"]!r}')
    if 'enum' in schema and not any(equal(value, item) for item in schema['enum']):
        raise ValueError(f'{path}: unsupported value {value!r}')
    if isinstance(value, dict):
        missing = set(schema.get('required', [])) - set(value)
        if missing:
            raise ValueError(f'{path}: missing {sorted(missing)}')
        props = schema.get('properties', {})
        if schema.get('additionalProperties') is False and set(value) - set(props):
            raise ValueError(f'{path}: unexpected fields {sorted(set(value) - set(props))}')
        for key, item in value.items():
            if key in props:
                check(item, props[key], f'{path}.{key}')
    if isinstance(value, list) and 'items' in schema:
        for index, item in enumerate(value):
            check(item, schema['items'], f'{path}[{index}]')
    if isinstance(value, str):
        if len(value) < schema.get('minLength', 0):
            raise ValueError(f'{path}: string too short')
        if 'pattern' in schema and re.search(schema['pattern'], value) is None:
            raise ValueError(f'{path}: invalid pattern')
    if type(value) in (int, float):
        if value < schema.get('minimum', -math.inf) or value > schema.get('maximum', math.inf):
            raise ValueError(f'{path}: number outside allowed range')
    for constraint in schema.get('allOf', []):
        check(value, constraint, path)
    if 'if' in schema:
        try:
            check(value, schema['if'], path)
        except ValueError:
            pass
        else:
            check(value, schema.get('then', {}), path)


def validate_schema(value: Any, filename: str, path: str) -> None:
    schema = json.loads((Path(__file__).resolve().parents[1] / 'references' / filename).read_text())
    check(value, schema, path)


def read_json(path: str | None) -> Any:
    import sys
    def invalid_constant(value: str) -> None:
        raise ValueError(f'Invalid JSON number: {value}')
    if path:
        with open(path, encoding='utf-8') as stream:
            return json.load(stream, parse_constant=invalid_constant)
    return json.loads(sys.stdin.read(), parse_constant=invalid_constant)
