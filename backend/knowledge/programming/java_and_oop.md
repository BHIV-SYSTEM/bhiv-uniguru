---
title: Java Programming, JVM Architecture, and OOP Design
domain: programming
subject: Java
authority_score: 0.99
source_name: Oracle Java Documentation & OpenJDK Specification
source_url: https://docs.oracle.com/en/java/
license: Oracle Open Access
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Java Programming, JVM Architecture, and OOP Design

## 1. JVM Architecture & Garbage Collection
Java bytecode (`.class`) compiles once and runs on any platform containing a Java Virtual Machine (JVM):
- **Class Loader Subsystem**: Loads, links (verifies, prepares, resolves), and initializes bytecode classes.
- **JVM Memory Areas**:
  - **Method Area**: Stores class metadata, runtime constant pool, and static variables.
  - **Heap Memory**: Shared runtime memory pool where all object instances and arrays are allocated.
  - **JVM Stack**: Stores frames containing local variables, operand stacks, and partial results per thread.
  - **PC Registers**: Tracks current instruction execution pointer per thread.
- **Garbage Collection (GC)**:
  - Generational Hypothesis: Most objects die young.
  - **Young Generation** (Eden + Survivor spaces S0/S1): Minor GC collects short-lived objects.
  - **Old (Tenured) Generation**: Long-lived objects promoted here; collected via Major / Full GC.
  - Production GC Collectors: G1GC (Garbage-First), ZGC (ultra-low pause time sub-millisecond concurrent collector).

## 2. Core OOP Principles in Java
- **Encapsulation**: Restricting direct access to object components using access modifiers (`private`, `protected`, `public`) with getter/setter abstractions.
- **Inheritance & Polymorphism**:
  - Runtime (Dynamic) Polymorphism via method overriding (`@Override`).
  - Compile-time (Static) Polymorphism via method overloading.
  ```java
  public abstract class Animal {
      protected String name;
      public Animal(String name) { this.name = name; }
      public abstract void makeSound();
  }

  public class Dog extends Animal {
      public Dog(String name) { super(name); }
      @Override
      public void makeSound() {
          System.out.println(name + " barks: Woof!");
      }
  }
  ```

## 3. Java Collections Framework & Modern Streams (Java 8+)
- **Collection Hierarchy**:
  - `List`: `ArrayList` (dynamic array), `LinkedList` (doubly-linked list).
  - `Set`: `HashSet` ($\mathcal{O}(1)$ average lookup), `TreeSet` (sorted Red-Black tree).
  - `Map`: `HashMap` (buckets with buckets converting to trees on collision threshold > 8), `ConcurrentHashMap` (thread-safe without locking whole table).
- **Stream API & Functional Interfaces**:
  ```java
  import java.util.List;
  import java.util.stream.Collectors;

  public class StreamExample {
      public static void main(String[] args) {
          List<String> names = List.of("Aarav", "Vijay", "Ananya", "Rohan");
          List<String> filtered = names.stream()
              .filter(name -> name.startsWith("A"))
              .map(String::toUpperCase)
              .collect(Collectors.toList());
          System.out.println(filtered); // [AARAV, ANANYA]
      }
  }
  ```
