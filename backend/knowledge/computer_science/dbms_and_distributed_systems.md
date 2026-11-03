---
title: Database Management Systems, SQL, and Distributed Systems
domain: computer_science
subject: DBMS & Distributed Systems
authority_score: 0.98
source_name: ACM SIGMOD & PostgreSQL Global Development Group
source_url: https://www.postgresql.org/docs/
license: Open Source / Educational
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Database Management Systems, SQL, and Distributed Systems

## 1. Relational Database Concepts & ACID Properties
Relational databases store structured records in tables consisting of rows (tuples) and columns (attributes), enforcing integrity constraints:
- **Atomicity**: All operations in a transaction succeed completely, or all changes are rolled back on failure (all-or-nothing).
- **Consistency**: A transaction transitions the database from one valid state to another, preserving all foreign keys, unique constraints, and schema rules.
- **Isolation**: Concurrent execution of transactions yields the same state as if executed sequentially. Standard ANSI Isolation Levels:
  1. Read Uncommitted (vulnerable to dirty reads).
  2. Read Committed (prevents dirty reads; vulnerable to non-repeatable reads).
  3. Repeatable Read (prevents non-repeatable reads; utilizes MVCC).
  4. Serializable (strict serializability; highest isolation).
- **Durability**: Once a transaction is committed, its effects survive system crashes or power failures (guaranteed via Write-Ahead Logging / WAL).

## 2. Normalization (1NF through BCNF)
Normalization decomposes tables to eliminate data redundancy and prevent insertion, update, and deletion anomalies:
- **1NF (First Normal Form)**: Every column contains only atomic (indivisible) values; no repeating groups.
- **2NF (Second Normal Form)**: Must be in 1NF and have no partial functional dependencies (every non-prime attribute is fully functionally dependent on the entire composite primary key).
- **3NF (Third Normal Form)**: Must be in 2NF and have no transitive dependencies ($X \to Y$ and $Y \to Z$ where $X$ is primary key).
- **BCNF (Boyce-Codd Normal Form)**: For every functional dependency $X \to Y$, the determinant $X$ must be a superkey.

## 3. Distributed Systems: CAP Theorem & Consistency Models
- **Brewer's CAP Theorem**:
  A distributed data store can guarantee at most two out of the three properties simultaneously in the presence of network partitions:
  - **Consistency (C)**: Every read receives the most recent write or an error.
  - **Availability (A)**: Every non-failing node returns a non-error response for every request.
  - **Partition Tolerance (P)**: The system continues operating despite arbitrary message loss or network partitions.
  *Real-World Architecture*: Because network partitions ($P$) are inevitable in physical infrastructure, systems choose between **CP** (e.g., etcd, ZooKeeper, CockroachDB) and **AP** (e.g., Cassandra, DynamoDB, DNS).
- **Consensus Protocols**:
  - **Raft** & **Paxos**: Leader-based distributed consensus ensuring replicated state machine consistency across a quorum ($Q = \lfloor n/2 \rfloor + 1$) of nodes.
