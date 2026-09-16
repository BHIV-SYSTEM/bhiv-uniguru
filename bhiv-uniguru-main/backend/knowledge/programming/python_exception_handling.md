---
title: Python Exception Handling
source: python_exception_handling.md
category: programming
verification_status: VERIFIED
---

## Python Exception Handling

Use `try` / `except` blocks to catch and handle runtime errors.

Example:

```python
try:
    value = int(input("Enter a number: "))
    print(10 / value)
except ValueError:
    print("Please enter a valid integer.")
except ZeroDivisionError:
    print("Cannot divide by zero.")
finally:
    print("Execution complete.")
```

### Common exception handling patterns

- `except Exception as e`: catch any exception and inspect `e`.
- `else:` runs when no exception occurs.
- `raise`: re-raise an exception.
