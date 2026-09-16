---
title: Python Looping
source: python_looping.md
category: programming
verification_status: VERIFIED
---

## Python Looping

Python supports iteration with `for` and `while` loops.

### `for` loop

```python
for i in range(5):
    print(i)
```

Example with a list:

```python
fruits = ["apple", "banana", "cherry"]
for fruit in fruits:
    print(fruit)
```

### `while` loop

```python
count = 0
while count < 5:
    print(count)
    count += 1
```

### Loop control statements

- `break` exits the loop immediately.
- `continue` skips to the next iteration.
- `else` on a loop runs when the loop completes without `break`.
