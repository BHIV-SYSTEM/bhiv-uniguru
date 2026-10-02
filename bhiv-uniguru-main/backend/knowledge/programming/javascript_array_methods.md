---
title: JavaScript Array Methods
source: javascript_array_methods.md
category: programming
verification_status: VERIFIED
---

## JavaScript Array Methods

JavaScript arrays have many built-in methods for iteration and transformation.

### `map`

```javascript
const numbers = [1, 2, 3];
const squares = numbers.map(x => x * x);
console.log(squares); // [1, 4, 9]
```

### `filter`

```javascript
const evens = numbers.filter(x => x % 2 === 0);
console.log(evens); // [2]
```

### `reduce`

```javascript
const sum = numbers.reduce((acc, x) => acc + x, 0);
console.log(sum); // 6
```
