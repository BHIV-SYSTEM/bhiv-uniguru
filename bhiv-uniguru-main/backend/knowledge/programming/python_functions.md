---
title: Python Functions
source: python_functions.md
category: programming
verification_status: VERIFIED
---

## Python Functions

A function in Python is defined using the `def` keyword.

Example:

```python
def greet(name):
    return f"Hello, {name}!"

message = greet("Alice")
print(message)  # Hello, Alice!
```

### Function arguments

- Positional arguments: passed by position.
- Keyword arguments: passed by name.
- Default values:

```python
def power(base, exponent=2):
    return base ** exponent

print(power(3))    # 9
print(power(3, 3)) # 27
```

### Variable arguments

- `*args` collects extra positional arguments.
- `**kwargs` collects extra keyword arguments.

```python
def summarize(*args, **kwargs):
    print(args)
    print(kwargs)

summarize(1, 2, 3, name="Alice")
```
