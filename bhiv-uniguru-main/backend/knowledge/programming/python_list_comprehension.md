---
title: Python List Comprehension
source: python_list_comprehension.md
category: programming
verification_status: VERIFIED
---

## Python List Comprehension

List comprehensions provide a concise syntax for creating lists.

Example:

```python
squares = [x * x for x in range(10)]
print(squares)  # [0, 1, 4, 9, 16, 25, 36, 49, 64, 81]
```

With a condition:

```python
even_squares = [x * x for x in range(10) if x % 2 == 0]
print(even_squares)  # [0, 4, 16, 36, 64]
```

### Equivalent loop

```python
squares = []
for x in range(10):
    squares.append(x * x)
```
