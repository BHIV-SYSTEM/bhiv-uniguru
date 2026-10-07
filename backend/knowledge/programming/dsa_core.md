---
domain: programming
subdomain: algorithms
topic: dsa_searching_sorting_recursion
language: en
source: uniguru_algorithms_reference
source_type: verified_handbook
difficulty: intermediate
document_id: PROG_DSA_001
chunk_id: CHUNK_DSA_FOUNDATIONS
version: 1.0.0
created_at: 2026-10-02T11:43:00Z
---

# Data Structures & Algorithms Foundations

## 1. Binary Search
An efficient search algorithm on sorted arrays operating in logarithmic time $\mathcal{O}(\log n)$.
- **Time Complexity**: Best $\mathcal{O}(1)$, Average/Worst $\mathcal{O}(\log n)$.
- **Space Complexity**: Iterative $\mathcal{O}(1)$, Recursive $\mathcal{O}(\log n)$ stack depth.

```cpp
// C++ Implementation
#include <vector>

int binarySearch(const std::vector<int>& arr, int target) {
    int low = 0, high = arr.size() - 1;
    while (low <= high) {
        int mid = low + (high - low) / 2;
        if (arr[mid] == target) return mid;
        if (arr[mid] < target) low = mid + 1;
        else high = mid - 1;
    }
    return -1;
}
```

```python
# Python Implementation
def binary_search(arr: list[int], target: int) -> int:
    low, high = 0, len(arr) - 1
    while low <= high:
        mid = (low + high) // 2
        if arr[mid] == target:
            return mid
        elif arr[mid] < target:
            low = mid + 1
        else:
            high = mid - 1
    return -1
```

## 2. Recursion
A programming technique where a function solves a problem by calling itself with smaller sub-problems.
- **Base Case**: The termination condition preventing infinite recursion and `RecursionError` / stack overflow.
- **Recursive Step**: Progresses toward the base case.
- **Call Stack**: Each invocation pushes a new stack frame storing local variables and return address.

```python
def factorial(n: int) -> int:
    if n <= 1:
        return 1
    return n * factorial(n - 1)
```

## 3. Dynamic Programming (DP)
Solves problems by breaking them down into overlapping subproblems and optimal substructure.
- **Memoization (Top-Down)**: Recursive with cache.
- **Tabulation (Bottom-Up)**: Iterative filling of table.
