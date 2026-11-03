---
title: Modern C++ and C Core Programming, Memory Management, and STL
domain: programming
subject: C & C++
authority_score: 0.99
source_name: ISO C++ Standard & CppReference
source_url: https://en.cppreference.com/
license: Creative Commons Attribution-Sharealike
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Modern C++ and C Core Programming, Memory Management, and STL

## 1. Memory Management & Pointers in C
- **Stack vs. Heap Memory**:
  - **Stack**: Fast, automatic allocation and deallocation upon function entry and exit. Local variables.
  - **Heap**: Dynamic memory manually allocated by the programmer (`malloc()`, `calloc()`, `free()`). Unfreed memory causes memory leaks.
- **Pointers and References**:
  ```c
  int val = 42;
  int* ptr = &val; // Pointer holds memory address
  *ptr = 100;      // Dereferencing mutates value to 100
  ```

## 2. Modern C++ (C++11 through C++20): RAII and Smart Pointers
- **RAII (Resource Acquisition Is Initialization)**:
  Binds the lifecycle of resources (heap memory, file descriptors, database connections, mutex locks) to the lifetime of stack objects. When the object leaves scope, its destructor is automatically called, preventing resource leaks.
- **Smart Pointers (`<memory>`)**:
  - `std::unique_ptr<T>`: Exclusive ownership. Cannot be copied, only moved (`std::move`). Zero overhead compared to raw pointer.
  - `std::shared_ptr<T>`: Shared reference-counted ownership. Resource is freed when the internal reference count drops to 0.
  - `std::weak_ptr<T>`: Non-owning reference to an object managed by `std::shared_ptr`; breaks circular reference cycles.
  ```cpp
  #include <memory>
  #include <iostream>

  struct Node {
      int id;
      Node(int i) : id(i) { std::cout << "Node created\n"; }
      ~Node() { std::cout << "Node destroyed\n"; }
  };

  void demo() {
      auto ptr = std::make_unique<Node>(10); // Automatically destroyed at function exit
  }
  ```

## 3. Standard Template Library (STL) Containers & Algorithms
- **Vector (`std::vector<T>`)**: Dynamic contiguous array. Fast $\mathcal{O}(1)$ random access, amortized $\mathcal{O}(1)$ push_back.
- **Map (`std::map<K, V>`) vs. Unordered Map (`std::unordered_map<K, V>`)**:
  - `std::map`: Self-balancing Red-Black Tree. Keys are ordered. Lookup, insertion, and deletion are $\mathcal{O}(\log n)$.
  - `std::unordered_map`: Hash table. Keys are unordered. Average $\mathcal{O}(1)$ lookup, worst-case $\mathcal{O}(n)$.
- **Iterators & Algorithms (`<algorithm>`)**:
  - Binary search algorithm on sorted vectors:
  ```cpp
  #include <vector>
  #include <algorithm>
  #include <iostream>

  int binarySearch(const std::vector<int>& arr, int target) {
      int low = 0, high = arr.size() - 1;
      while (low <= high) {
          int mid = low + (high - low) / 2; // Prevents integer overflow
          if (arr[mid] == target) return mid;
          if (arr[mid] < target) low = mid + 1;
          else high = mid - 1;
      }
      return -1;
  }
  ```
