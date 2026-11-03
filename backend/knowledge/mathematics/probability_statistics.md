---
title: Probability, Statistics, and Discrete Mathematics
domain: mathematics
subject: Probability & Discrete Math
authority_score: 0.97
source_name: NCERT & Harvard Stat 110 Open Courseware
source_url: https://projects.iq.harvard.edu/stat110
license: Educational Open Access
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Probability, Statistics, and Discrete Mathematics

## 1. Probability Theory and Bayes' Theorem
Probability quantifies the likelihood of an event $E$ occurring within a sample space $S$:
$$P(E) = \frac{|E|}{|S|} \quad \text{for equally likely outcomes, with } 0 \le P(E) \le 1$$

### Conditional Probability:
The probability of event $A$ given that event $B$ has occurred ($P(B) > 0$):
$$P(A|B) = \frac{P(A \cap B)}{P(B)}$$

### Bayes' Theorem:
Enables reversing conditional probabilities, fundamental to Bayesian reasoning and machine learning:
$$P(A|B) = \frac{P(B|A) P(A)}{P(B)}$$
where:
- $P(A)$ is the **Prior** probability.
- $P(B|A)$ is the **Likelihood**.
- $P(B)$ is the **Marginal** probability ($P(B) = \sum_i P(B|A_i)P(A_i)$).
- $P(A|B)$ is the **Posterior** probability.

## 2. Descriptive and Inferential Statistics
### Measures of Central Tendency:
- **Mean** ($\mu$ or $\bar{x}$): $\bar{x} = \frac{1}{n} \sum_{i=1}^n x_i$
- **Median**: The middle value separating the higher half from the lower half of a sorted dataset.
- **Mode**: The most frequently occurring value in the dataset.

### Measures of Dispersion:
- **Variance** ($\sigma^2$):
  $$\sigma^2 = \frac{1}{N} \sum_{i=1}^N (x_i - \mu)^2 \quad (\text{Sample Variance } s^2 = \frac{1}{n-1} \sum_{i=1}^n (x_i - \bar{x})^2)$$
- **Standard Deviation** ($\sigma$): $\sigma = \sqrt{\sigma^2}$

### Normal (Gaussian) Distribution:
Probability density function with mean $\mu$ and standard deviation $\sigma$:
$$f(x) = \frac{1}{\sigma \sqrt{2\pi}} \exp\left(-\frac{(x - \mu)^2}{2\sigma^2}\right)$$
- 68.27% of observations fall within $\mu \pm 1\sigma$.
- 95.45% of observations fall within $\mu \pm 2\sigma$.
- 99.73% of observations fall within $\mu \pm 3\sigma$.

## 3. Discrete Mathematics: Logic, Sets, and Graph Theory
### Set Operations:
- Union: $A \cup B = \{x \mid x \in A \text{ or } x \in B\}$
- Intersection: $A \cap B = \{x \mid x \in A \text{ and } x \in B\}$
- De Morgan's Laws:
  $$(A \cup B)' = A' \cap B'$$
  $$(A \cap B)' = A' \cup B'$$

### Graph Theory Core Definitions:
- A **Graph** $G = (V, E)$ consists of vertices $V$ and edges $E$.
- **Handshaking Lemma**: $\sum_{v \in V} \deg(v) = 2|E|$ (The sum of degrees of all vertices is always even).
- **Eulerian Path**: A trail in a finite graph that visits every edge exactly once, existing if and only if exactly zero or two vertices have odd degree.
