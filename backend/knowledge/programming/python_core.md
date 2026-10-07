---
domain: programming
subdomain: python
topic: python_fundamentals
language: en
source: uniguru_curriculum_2026
source_type: verified_handbook
difficulty: beginner
document_id: PROG_PY_001
chunk_id: CHUNK_PY_FUNDAMENTALS
version: 1.0.0
created_at: 2026-10-02T11:42:00Z
---

# Python Fundamentals, Core Data Structures, and Memory Model

## 1. Python Lists vs. Tuples vs. Sets vs. Dictionaries
- **List**: An ordered, mutable sequence of elements. Supports heterogeneous types, indexing, and slicing.
  ```python
  my_list = [10, "UniGuru", 3.14]
  my_list.append(42)       # O(1) amortized
  first = my_list[0]       # O(1)
  subset = my_list[1:3]    # O(k) slice copy
  ```
- **Tuple**: An ordered, immutable sequence. Used for fixed records, return values from functions, and dictionary keys.
  ```python
  point = (19.0760, 72.8777)
  ```
- **Set**: An unordered collection of unique elements based on hash tables. Constant time `O(1)` membership lookups (`x in s`).
- **Dict**: Key-value hash map preserving insertion order (since Python 3.7+).

## 2. Pass By Object Reference (Call by Assignment)
In Python, variables are not buckets containing values; they are names bound to objects in memory:
- **Immutable Objects** (`int`, `float`, `str`, `tuple`, `frozenset`): Modifications inside a function create a new object; the caller's reference remains unchanged.
- **Mutable Objects** (`list`, `dict`, `set`): In-place mutations inside a function affect the object referenced by the caller.

```python
def modify_list(lst):
    lst.append(99)  # Mutates caller's list

def reassign_list(lst):
    lst = [1, 2, 3] # Rebinds local variable; caller unaffected
```

## 3. Python Decorators and Generators
- **Decorator**: A callable that takes another function and extends its behavior without modifying its source code.
  ```python
  def timer_decorator(func):
      def wrapper(*args, **kwargs):
          import time
          t0 = time.perf_counter()
          res = func(*args, **kwargs)
          print(f"{func.__name__} took {time.perf_counter()-t0:.4f}s")
          return res
      return wrapper
  ```
- **Generator**: Uses `yield` to produce an iterable stream on demand, operating in `O(1)` memory space.
  ```python
  def fibonacci_gen(limit):
      a, b = 0, 1
      for _ in range(limit):
          yield a
          a, b = b, a + b
  ```
