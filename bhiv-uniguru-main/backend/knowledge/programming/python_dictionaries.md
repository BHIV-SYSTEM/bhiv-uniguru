---
title: Python Dictionaries
source: python_dictionaries.md
category: programming
verification_status: VERIFIED
---

## Python Dictionaries

A dictionary in Python stores key-value pairs and is defined using curly braces `{}`.

Example:

```python
person = {"name": "Alice", "age": 30}
print(person["name"])  # Alice
```

### Common dictionary operations

- `person["name"]`: access value by key.
- `person["city"] = "Delhi"`: set a new key.
- `del person["age"]`: delete a key.
- `len(person)`: number of items.
- `person.keys()`, `person.values()`, `person.items()`: iterate keys, values, or key-value pairs.

### Dictionary methods

- `get(key, default=None)`: safely retrieve a value.
- `pop(key)`: remove and return value.
- `update(other_dict)`: merge another dictionary.
- `clear()`: remove all items.
