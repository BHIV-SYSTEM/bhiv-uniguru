---
title: Systems Programming in Go, Rust, and Bash Shell Scripting
domain: programming
subject: Go, Rust & Bash
authority_score: 0.99
source_name: Rust Foundation Documentation & Go Language Specification
source_url: https://www.rust-lang.org/
license: MIT / Apache 2.0 Open Source
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Systems Programming in Go, Rust, and Bash Shell Scripting

## 1. Rust: Ownership, Borrowing, and Memory Safety
Rust achieves compile-time memory safety without a garbage collector through its **Ownership System**:
- **Ownership Rules**:
  1. Each value in Rust has an owner variable.
  2. There can only be one owner at a time.
  3. When the owner goes out of scope, the value is dropped (freed from memory via `drop`).
- **Borrowing & Lifetimes**:
  - References can be borrowed: either **any number of immutable references** (`&T`) OR **exactly one mutable reference** (`&mut T`) at any given scope, preventing data races at compile time.
  ```rust
  fn main() {
      let mut s = String::from("UniGuru");
      modify_string(&mut s);
      println!("Result: {}", s);
  }

  fn modify_string(text: &mut String) {
      text.push_str(" Systems Engine");
  }
  ```

## 2. Go (Golang): Goroutines, Channels, and Concurrency
Go provides lightweight concurrency primitives built into the runtime:
- **Goroutines**: Lightweight threads managed by the Go runtime scheduler (M:N scheduling model) with minimal 2 KB initial stack sizes.
- **Channels**: Typed conduits for thread-safe message passing (*"Do not communicate by sharing memory; instead, share memory by communicating"*):
  ```go
  package main

  import (
      "fmt"
      "time"
  )

  func worker(id int, ch chan string) {
      time.Sleep(50 * time.Millisecond)
      ch <- fmt.Sprintf("Worker %d completed", id)
  }

  func main() {
      ch := make(chan string, 2)
      go worker(1, ch)
      go worker(2, ch)

      fmt.Println(<-ch)
      fmt.Println(<-ch)
  }
  ```

## 3. Bash Shell Scripting & POSIX Automation
- **Piping & Redirection**:
  - `stdout` redirection: `cmd > file.txt` (overwrite), `cmd >> file.txt` (append).
  - `stderr` redirection: `cmd 2> error.log`, combined: `cmd > output.log 2>&1`.
  - Unix Pipes: `grep "ERROR" system.log | awk '{print $4}' | sort | uniq -c`.
- **Defensive Bash Practices**:
  ```bash
  #!/usr/bin/env bash
  set -euo pipefail # -e: exit on error, -u: treat unset vars as error, -o pipefail: pipeline fails on first failure
  IFS=$'\n\t'       # Safer word splitting

  echo "Executing automated deployment..."
  ```
