---
title: SQL Query Engineering, Indexing, and Performance Optimization
domain: programming
subject: SQL & Databases
authority_score: 0.99
source_name: PostgreSQL Documentation & ANSI SQL Standards
source_url: https://www.postgresql.org/docs/current/queries.html
license: Open Source
verification_status: VERIFIED
last_verified: 2026-10-02
---

# SQL Query Engineering, Indexing, and Performance Optimization

## 1. Advanced SQL Queries & Analytical Window Functions
Window functions calculate across a set of table rows that are related to the current row, without collapsing individual rows like `GROUP BY`:
- **`ROW_NUMBER()`, `RANK()`, `DENSE_RANK()`**:
  ```sql
  -- Finding the Nth highest salary in each department
  WITH RankedSalaries AS (
      SELECT
          department_id,
          employee_id,
          salary,
          DENSE_RANK() OVER (
              PARTITION BY department_id
              ORDER BY salary DESC
          ) AS rank_num
      FROM employees
  )
  SELECT department_id, employee_id, salary
  FROM RankedSalaries
  WHERE rank_num = 2;
  ```
- **Aggregate Window Functions**:
  ```sql
  -- Running total of sales by date
  SELECT
      order_date,
      amount,
      SUM(amount) OVER (ORDER BY order_date ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW) AS cumulative_sales
  FROM orders;
  ```

## 2. Common Table Expressions (CTEs) & Recursive Queries
- **Non-Recursive CTE**: Improves readability and modularity compared to nested subqueries.
- **Recursive CTE**: Ideal for hierarchical organizational charts and graph traversals:
  ```sql
  WITH RECURSIVE CategoryHierarchy AS (
      -- Base member (root category)
      SELECT id, name, parent_id, 1 as level
      FROM categories
      WHERE parent_id IS NULL
      UNION ALL
      -- Recursive member
      SELECT c.id, c.name, c.parent_id, ch.level + 1
      FROM categories c
      INNER JOIN CategoryHierarchy ch ON c.parent_id = ch.id
  )
  SELECT * FROM CategoryHierarchy;
  ```

## 3. Database Indexing & Query Execution Plans
- **B-Tree Indexes**: Default index structure. Balanced search tree storing sorted keys with leaf nodes pointing to physical disk blocks. Ideal for range scans (`>`, `<`), equality (`=`), and `ORDER BY`.
- **Composite Indexes & The Leftmost Prefix Rule**:
  An index on `(last_name, first_name)` accelerates queries filtering on `last_name` or `(last_name, first_name)`, but cannot be used for queries filtering solely on `first_name`.
- **Query Optimization Rules**:
  1. Avoid `SELECT *` to reduce buffer memory and network I/O.
  2. Avoid functions on indexed columns in `WHERE` clauses (e.g. `WHERE YEAR(created_at) = 2026` suppresses index usage; rewrite as `WHERE created_at >= '2026-01-01' AND created_at < '2027-01-01'`).
  3. Inspect queries via `EXPLAIN ANALYZE` to eliminate sequential scans on large tables.
