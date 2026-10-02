---
title: JavaScript Functions
source: javascript_functions.md
category: programming
verification_status: VERIFIED
---

## JavaScript Functions

Functions are reusable blocks of code.

Example:

```javascript
function greet(name) {
  return `Hello, ${name}!`;
}

console.log(greet('Alice')); // Hello, Alice!
```

### Arrow functions

```javascript
const add = (a, b) => a + b;
console.log(add(3, 4)); // 7
```

### Function arguments

- `arguments` contains all passed values.
- Default parameters:

```javascript
function multiply(a, b = 1) {
  return a * b;
}
```
