---
title: Operating Systems, Computer Architecture, and Concurrency
domain: computer_science
subject: Operating Systems & Architecture
authority_score: 0.98
source_name: IEEE Computer Society & Silberschatz Operating System Concepts
source_url: https://www.computer.org/
license: Educational Open Access
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Operating Systems, Computer Architecture, and Concurrency

## 1. Operating Systems Core Architecture
The operating system acts as an intermediary between computer hardware and user applications, managing CPU, memory, and I/O devices:
- **Process vs. Thread**:
  - A **Process** is an executing program instance with its own private virtual address space (text, data, heap, stack), file descriptors, and security context. Process creation (`fork()`) is heavyweight.
  - A **Thread** is the smallest schedulable unit of CPU execution within a process. Threads share the parent process's memory space, open files, and global state, but maintain their own program counter, registers, and private stack.
- **CPU Scheduling Algorithms**:
  - **First-Come, First-Served (FCFS)**: Non-preemptive, suffers from the Convoy Effect.
  - **Shortest Job First (SJF)**: Minimizes average waiting time; requires predicting burst times.
  - **Round Robin (RR)**: Preemptive scheduling with a fixed time quantum $q$; prevents starvation.
  - **Multi-Level Feedback Queue (MLFQ)**: Adaptive prioritization based on observed I/O vs CPU-bound behavior.

## 2. Memory Management, Virtual Memory, and Paging
- **Virtual Memory**: Decouples the logical address space from physical memory (RAM), allowing execution of processes larger than available physical RAM.
- **Paging & TLB**:
  - Physical memory is split into fixed-size **Frames**; logical memory is split into identical-sized **Pages** (typically 4 KB).
  - The **Page Table** maps virtual page numbers (VPN) to physical frame numbers (PFN).
  - **Translation Lookaside Buffer (TLB)**: High-speed hardware cache on the CPU storing recent virtual-to-physical address translations to reduce memory access latency.
  - **Page Fault**: Hardware interrupt triggered when an accessed virtual page is not currently present in RAM, causing the OS kernel to page in the block from swap storage.

## 3. Concurrency, Synchronization, and Deadlocks
- **Race Condition**: A situation where multiple concurrent threads access shared mutable data and the final outcome depends on non-deterministic execution interleaving.
- **Mutual Exclusion Primitives**:
  - **Mutex**: A locking mechanism owned by a single thread at a time.
  - **Semaphore**: A signaling integer counter supporting atomic `wait()` (P) and `signal()` (V) operations.
- **Coffman's Four Deadlock Conditions** (All 4 must hold simultaneously):
  1. **Mutual Exclusion**: Non-shareable resource allocation.
  2. **Hold and Wait**: Process holding resources requests additional ones.
  3. **No Preemption**: Resources cannot be forcibly taken from a process.
  4. **Circular Wait**: A closed chain of processes each waiting for a resource held by the next.
- **Deadlock Resolution**: Prevent by breaking one of Coffman's conditions (e.g. strict global resource ordering to eliminate circular wait), or avoid via Dijkstra's **Banker's Algorithm**.
