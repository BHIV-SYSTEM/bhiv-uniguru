---
title: Machine Learning Foundations, Algorithms, and Evaluation Metrics
domain: ai_ml
subject: Machine Learning
authority_score: 0.99
source_name: scikit-learn User Guide & Stanford CS229
source_url: https://scikit-learn.org/stable/user_guide.html
license: BSD-3-Clause / Open Educational Access
verification_status: VERIFIED
last_verified: 2026-10-02
---

# Machine Learning Foundations, Algorithms, and Evaluation Metrics

## 1. Machine Learning Paradigm & The Bias-Variance Tradeoff
Machine learning models infer functional relationships $y = f(\mathbf{x}) + \epsilon$ from empirical training data without explicit programmatic rule encoding:
- **Supervised Learning**: Models learn mapping from input features $\mathbf{x}$ to ground-truth labels $y$ (Regression for continuous variables, Classification for discrete classes).
- **Unsupervised Learning**: Models identify intrinsic structures, groupings, or representations without target labels (Clustering: K-Means, DBSCAN; Dimensionality Reduction: PCA, t-SNE).
- **The Bias-Variance Decomposition**:
  $$\text{Expected Test Error} = \text{Bias}^2 + \text{Variance} + \sigma^2 (\text{Irreducible Error})$$
  - **High Bias (Underfitting)**: Model is overly simplistic and fails to capture underlying patterns. Solution: Increase model complexity, add polynomial/interaction features.
  - **High Variance (Overfitting)**: Model fits training noise and generalizes poorly to unseen data. Solution: Regularization (L1 Lasso, L2 Ridge), dropout, cross-validation, more training data.

## 2. Supervised Learning Algorithms
- **Linear & Logistic Regression**:
  - Linear: $\hat{y} = \mathbf{w}^T \mathbf{x} + b$, optimized via Mean Squared Error (MSE).
  - Logistic: Maps continuous inputs to probabilities via the sigmoid function $\sigma(z) = \frac{1}{1 + e^{-z}}$, optimized using Binary Cross-Entropy Loss.
- **Tree-Based Ensembles**:
  - **Decision Trees**: Partition feature space using splitting criteria (Gini Impurity, Information Gain / Shannon Entropy).
  - **Random Forest**: Bagging (Bootstrap Aggregating) ensemble of unpruned decision trees trained on random feature subsets. Reduces variance significantly.
  - **Gradient Boosted Decision Trees (XGBoost / LightGBM)**: Boosting ensemble where each sequential tree fits the pseudo-residuals (negative gradient of loss) of previous iterations.

## 3. Model Evaluation Metrics & Validation
- **Classification Metrics**:
  - **Accuracy**: $\frac{TP + TN}{TP + TN + FP + FN}$ (Misleading on class-imbalanced datasets).
  - **Precision**: $\frac{TP}{TP + FP}$ (Fraction of predicted positives that are true).
  - **Recall (Sensitivity)**: $\frac{TP}{TP + FN}$ (Fraction of actual positives detected).
  - **F1-Score**: Harmonic mean of Precision and Recall: $\frac{2 \cdot \text{Precision} \cdot \text{Recall}}{\text{Precision} + \text{Recall}}$.
  - **ROC-AUC**: Area Under the Receiver Operating Characteristic curve plotting True Positive Rate vs False Positive Rate across all classification thresholds.
- **K-Fold Cross-Validation**:
  Splits dataset into $K$ equal subsets (folds); trains on $K-1$ folds and evaluates on the remaining fold across $K$ rotations to estimate true generalization error reliably.
