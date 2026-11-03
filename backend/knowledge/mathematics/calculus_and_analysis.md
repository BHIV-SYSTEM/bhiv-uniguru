---
title: Calculus, Differentiation, and Integration
domain: mathematics
subject: Calculus
authority_score: 0.98
source_name: NCERT & OpenStax Calculus
source_url: https://ncert.nic.in/textbook.php
license: Educational Open Access
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Calculus, Differentiation, and Integration

## 1. Differential Calculus Fundamentals
Differentiation represents the instantaneous rate of change of a function with respect to one of its variables.
Formally defined as the limit of a difference quotient:
$$f'(x) = \lim_{h \to 0} \frac{f(x + h) - f(x)}{h}$$

### Essential Differentiation Rules:
- **Power Rule**: $\frac{d}{dx}[x^n] = n x^{n-1}$
- **Constant Multiple Rule**: $\frac{d}{dx}[c \cdot f(x)] = c \cdot f'(x)$
- **Sum & Difference Rule**: $\frac{d}{dx}[f(x) \pm g(x)] = f'(x) \pm g'(x)$
- **Product Rule**: $\frac{d}{dx}[u \cdot v] = u \frac{dv}{dx} + v \frac{du}{dx}$
- **Quotient Rule**: $\frac{d}{dx}\left[\frac{u}{v}\right] = \frac{v \frac{du}{dx} - u \frac{dv}{dx}}{v^2}$
- **Chain Rule**: $\frac{d}{dx}[f(g(x))] = f'(g(x)) \cdot g'(x)$

### Derivatives of Standard Functions:
- $\frac{d}{dx}[\sin(x)] = \cos(x)$
- $\frac{d}{dx}[\cos(x)] = -\sin(x)$
- $\frac{d}{dx}[e^x] = e^x$
- $\frac{d}{dx}[\ln(x)] = \frac{1}{x} \quad (x > 0)$

## 2. Integral Calculus Fundamentals
Integration is the inverse operation of differentiation (antiderivative) and geometrically calculates the area under a curve.
By the Fundamental Theorem of Calculus:
$$\int_a^b f(x) \, dx = F(b) - F(a) \quad \text{where } F'(x) = f(x)$$

### Essential Integration Rules:
- **Power Rule for Integrals**: $\int x^n \, dx = \frac{x^{n+1}}{n+1} + C \quad (n \neq -1)$
- **Logarithmic Form**: $\int \frac{1}{x} \, dx = \ln|x| + C$
- **Exponential Integral**: $\int e^{kx} \, dx = \frac{1}{k}e^{kx} + C$
- **Trigonometric Integrals**:
  $$\int \cos(x) \, dx = \sin(x) + C$$
  $$\int \sin(x) \, dx = -\cos(x) + C$$
  $$\int \sec^2(x) \, dx = \tan(x) + C$$

### Integration by Substitution:
Used when an integrand contains a function and its derivative:
$$\int f(g(x)) g'(x) \, dx = \int f(u) \, du \quad \text{where } u = g(x)$$

### Integration by Parts:
Derived from the product rule of differentiation:
$$\int u \, dv = u v - \int v \, du$$
Choose $u$ using the **ILATE** priority mnemonic:
1. **I**nverse Trigonometric
2. **L**ogarithmic
3. **A**lgebraic
4. **T**rigonometric
5. **E**xponential

## 3. Ordinary Differential Equations (ODEs)
A differential equation relates a function with one or more of its derivatives.
- **First-Order Separable Equations**: $\frac{dy}{dx} = g(x)h(y) \implies \int \frac{1}{h(y)} \, dy = \int g(x) \, dx$
- **First-Order Linear Equations**: $\frac{dy}{dx} + P(x)y = Q(x)$
  Solved using the Integrating Factor $I(x) = e^{\int P(x) \, dx}$:
  $$y \cdot I(x) = \int Q(x) I(x) \, dx + C$$
