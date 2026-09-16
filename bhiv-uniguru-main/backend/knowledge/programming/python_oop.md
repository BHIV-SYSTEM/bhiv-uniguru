---
title: Python Object-Oriented Programming
source: python_oop.md
category: programming
verification_status: VERIFIED
---

## Python Object-Oriented Programming

Classes define blueprints for objects.

Example:

```python
class Person:
    def __init__(self, name, age):
        self.name = name
        self.age = age

    def greet(self):
        return f"Hello, {self.name}!"

alice = Person("Alice", 30)
print(alice.greet())
```

### Inheritance

```python
class Student(Person):
    def __init__(self, name, age, student_id):
        super().__init__(name, age)
        self.student_id = student_id
```

### Encapsulation

- Use `self` to store instance attributes.
- Use methods to access and mutate attributes.
