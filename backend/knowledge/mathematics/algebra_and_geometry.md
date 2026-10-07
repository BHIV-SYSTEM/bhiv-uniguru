---
title: Algebra, Linear Algebra, and Analytical Geometry
domain: mathematics
subject: Algebra & Geometry
authority_score: 0.98
source_name: NCERT Mathematics & MIT OpenCourseWare 18.06
source_url: https://ocw.mit.edu/courses/18-06-linear-algebra-spring-2010/
license: Creative Commons BY-NC-SA
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Algebra, Linear Algebra, and Analytical Geometry

## 1. Polynomials and Quadratic Equations
A quadratic equation is a second-order polynomial equation in a single variable $x$:
$$a x^2 + b x + c = 0 \quad (a \neq 0)$$

### Quadratic Formula:
$$x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$$
The discriminant $\Delta = b^2 - 4ac$ determines the nature of the roots:
- $\Delta > 0$: Two distinct real roots.
- $\Delta = 0$: One repeated real root ($x = -\frac{b}{2a}$).
- $\Delta < 0$: Two complex conjugate roots ($x = -\frac{b}{2a} \pm i \frac{\sqrt{4ac - b^2}}{2a}$).

### Vieta's Formulas for Quadratics:
For roots $\alpha$ and $\beta$:
$$\alpha + \beta = -\frac{b}{a}, \quad \alpha \beta = \frac{c}{a}$$

## 2. Linear Algebra: Matrices, Determinants, and Vector Spaces
A system of $m$ linear equations in $n$ variables can be expressed compactly as:
$$A \mathbf{x} = \mathbf{b}$$

### Determinant of a $2 \times 2$ Matrix:
$$\det \begin{pmatrix} a & b \\ c & d \end{pmatrix} = ad - bc$$
A square matrix $A$ is invertible (non-singular) if and only if $\det(A) \neq 0$.

### Matrix Inversion:
$$A^{-1} = \frac{1}{\det(A)} \text{adj}(A)$$
where $\text{adj}(A)$ is the transpose of the cofactor matrix.

### Eigenvalues and Eigenvectors:
For a linear operator represented by matrix $A$, a non-zero vector $\mathbf{v}$ is an eigenvector with eigenvalue $\lambda$ if:
$$A \mathbf{v} = \lambda \mathbf{v} \implies (A - \lambda I)\mathbf{v} = \mathbf{0}$$
The eigenvalues are the roots of the **Characteristic Polynomial**:
$$\det(A - \lambda I) = 0$$

## 3. Analytical Geometry and Trigonometry
### Pythagorean Trigonometric Identities:
$$\sin^2(\theta) + \cos^2(\theta) = 1$$
$$1 + \tan^2(\theta) = \sec^2(\theta)$$
$$1 + \cot^2(\theta) = \csc^2(\theta)$$

### Double-Angle Formulas:
$$\sin(2\theta) = 2 \sin(\theta) \cos(\theta)$$
$$\cos(2\theta) = \cos^2(\theta) - \sin^2(\theta) = 2\cos^2(\theta) - 1 = 1 - 2\sin^2(\theta)$$
$$\tan(2\theta) = \frac{2\tan(\theta)}{1 - \tan^2(\theta)}$$

### Conic Sections Standard Equations:
- **Circle** (center $(h,k)$, radius $r$): $(x - h)^2 + (y - k)^2 = r^2$
- **Parabola** (vertex at origin, opening right): $y^2 = 4ax$
- **Ellipse** (major axis horizontal): $\frac{x^2}{a^2} + \frac{y^2}{b^2} = 1 \quad (a > b)$
- **Hyperbola**: $\frac{x^2}{a^2} - \frac{y^2}{b^2} = 1$
