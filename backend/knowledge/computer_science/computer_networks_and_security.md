---
title: Computer Networks, TCP/IP, and Cybersecurity Fundamentals
domain: computer_science
subject: Networks & Cybersecurity
authority_score: 0.98
source_name: IETF RFC Standards & OWASP Foundation
source_url: https://www.ietf.org/
license: Open Internet Standards
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Computer Networks, TCP/IP, and Cybersecurity Fundamentals

## 1. Network Layer Models (OSI 7-Layer vs. TCP/IP 4-Layer)
- **OSI 7-Layer Architecture**:
  1. **Physical Layer**: Bit transmission over physical medium (cables, radio waves, optical fiber).
  2. **Data Link Layer**: Frame formatting, MAC addressing, error detection (Ethernet, Wi-Fi 802.11).
  3. **Network Layer**: Packet routing across heterogeneous networks, logical IP addressing (IPv4, IPv6, ICMP, BGP, OSPF).
  4. **Transport Layer**: End-to-end process-to-process delivery, segmentation, flow/congestion control (TCP, UDP).
  5. **Session Layer**: Establishing, managing, and terminating presentation sessions.
  6. **Presentation Layer**: Data formatting, character encoding (ASCII, UTF-8), compression, encryption (TLS).
  7. **Application Layer**: User-facing application protocols (HTTP/HTTPS, DNS, SSH, SMTP).

## 2. Transport Layer: TCP vs. UDP
- **Transmission Control Protocol (TCP)**:
  - Connection-oriented protocol providing reliable, ordered, byte-stream delivery.
  - **Three-Way Handshake**: `SYN` $\to$ `SYN-ACK` $\to$ `ACK`.
  - **Reliability Mechanisms**: Sequence numbers, acknowledgments, retransmission timers, sliding-window flow control.
  - **Congestion Control**: Slow Start, Congestion Avoidance, Fast Retransmit, Fast Recovery (AIMD).
- **User Datagram Protocol (UDP)**:
  - Connectionless, lightweight, unreliable datagram transmission without retransmissions or flow control.
  - Preferred for low-latency, real-time traffic (DNS queries, live audio/video streaming, gaming, WebRTC).

## 3. Cryptography & Cybersecurity Fundamentals
- **Symmetric vs. Asymmetric Encryption**:
  - **Symmetric Encryption**: Single shared key for encryption and decryption (AES-256, ChaCha20). Fast and computationally efficient for bulk data.
  - **Asymmetric (Public-Key) Encryption**: Mathematical key pair; public key encrypts, private key decrypts (RSA, Elliptic Curve Cryptography ECDSA/Ed25519, Diffie-Hellman key exchange).
- **Cryptographic Hashing**:
  - One-way, collision-resistant deterministic mapping (SHA-256, SHA-3, BLAKE3).
  - Used for integrity verification, digital signatures, and secure password hashing (with salt and slow algorithms: Argon2id, bcrypt, PBKDF2).
- **Transport Layer Security (TLS 1.3)**:
  - Encrypts Application Layer communications (HTTPS) over TCP port 443.
  - Key exchange using ephemeral Elliptic-Curve Diffie-Hellman (ECDHE) guarantees **Perfect Forward Secrecy (PFS)**.
- **OWASP Top 10 Web Vulnerabilities**:
  - **SQL Injection (SQLi)**: Untrusted user input altering SQL syntax; prevented via parameterized queries / prepared statements.
  - **Cross-Site Scripting (XSS)**: Execution of malicious scripts in victims' browsers; prevented by output escaping and Content Security Policy (CSP).
  - **Broken Authentication & Authorization**: Exploitation of misconfigured JWTs, lack of rate limiting, or IDOR (Insecure Direct Object References).
