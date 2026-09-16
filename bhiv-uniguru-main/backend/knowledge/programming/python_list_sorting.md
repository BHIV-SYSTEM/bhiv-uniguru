---
title: Python List Sorting
source: python_list_sorting.md
category: programming
verification_status: VERIFIED
---

## Python List Sorting

In Python, you can sort a list using the built-in `sort()` method or the `sorted()` function.

### Using `sort()`

- `sort()` sorts the list in place and returns `None`.
- Example:

```python
numbers = [3, 1, 4, 1, 5, 9]
numbers.sort()
print(numbers)  # [1, 1, 3, 4, 5, 9]
```

- `sort()` accepts the optional `key` and `reverse` arguments:
  - `key` is a function applied to each element for comparison.
  - `reverse=True` sorts in descending order.

### Using `sorted()`

- `sorted()` returns a new sorted list and does not modify the original.
- Example:

```python
numbers = [3, 1, 4, 1, 5, 9]
sorted_numbers = sorted(numbers)
print(sorted_numbers)  # [1, 1, 3, 4, 5, 9]
print(numbers)  # [3, 1, 4, 1, 5, 9]
```

- `sorted()` works on any iterable, such as tuples, sets, or dictionaries.

### Sorting by key

```python
words = ["banana", "apple", "cherry"]
words.sort(key=len)
print(words)  # ['apple', 'banana', 'cherry']
```

### Descending order

```python
numbers.sort(reverse=True)
print(numbers)  # [9, 5, 4, 3, 1, 1]
```
