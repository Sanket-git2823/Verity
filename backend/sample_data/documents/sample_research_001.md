# Optimization Techniques in Machine Learning

## Introduction

Optimization lies at the heart of modern machine learning. Every supervised learning algorithm, from logistic regression to deep neural networks, reduces to the problem of minimizing an objective function over a parameter space. The choice of optimization algorithm profoundly affects training speed, model quality, and generalization performance. This document surveys the principal families of optimization methods used in contemporary machine learning research and practice.

## First-Order Methods

First-order methods rely exclusively on gradient information — the vector of partial derivatives of the loss function with respect to each parameter. The simplest member of this family is **batch gradient descent**, which computes the gradient over the entire training set before taking a single parameter update step. While mathematically clean, batch gradient descent is impractical for large datasets due to the cost of each full-pass gradient computation.

**Stochastic Gradient Descent (SGD)** addresses this by estimating the gradient from a single randomly sampled training example (or a small mini-batch). The resulting updates are noisy but computationally cheap, and the noise itself can help the optimizer escape shallow local minima. Mini-batch SGD, which computes gradients over batches of 32 to 512 examples, strikes a practical balance between variance reduction and throughput on modern GPU hardware.

### Adaptive Learning Rate Methods

A significant challenge with vanilla SGD is the choice of learning rate. Too large a rate causes divergence; too small a rate leads to slow convergence. **Adaptive methods** adjust the learning rate on a per-parameter basis using accumulated gradient statistics:

- **AdaGrad** scales each parameter's learning rate inversely by the square root of the sum of all past squared gradients. This works well for sparse features but can shrink the rate too aggressively over time.
- **RMSProp** fixes AdaGrad's decaying rate by using an exponentially weighted moving average of squared gradients instead of a cumulative sum.
- **Adam** combines the momentum idea (exponential moving average of gradients) with RMSProp's adaptive scaling. It maintains both the first moment (mean) and second moment (uncentered variance) of gradients, applying bias correction in early iterations. Adam is the most widely used optimizer in deep learning today.
- **AdamW** decouples weight decay from the gradient-based update, correcting a subtle flaw in Adam's original formulation and often improving generalization.

## Second-Order Methods

Second-order methods incorporate curvature information through the **Hessian matrix** — the matrix of second partial derivatives. Newton's method, the canonical second-order approach, pre-multiplies the gradient by the inverse Hessian to produce an update direction that accounts for the local curvature of the loss surface. In theory, this enables convergence in fewer iterations.

In practice, computing and inverting the full Hessian is prohibitively expensive for models with millions of parameters. **Quasi-Newton methods** such as L-BFGS approximate the inverse Hessian using a limited history of gradient differences, making them feasible for medium-scale problems. For deep learning specifically, methods like **K-FAC** approximate the Fisher information matrix block-diagonally, enabling tractable natural gradient updates.

## Learning Rate Schedules

Beyond the base optimizer, **learning rate schedules** modulate the rate over training. Common schedules include:

- **Step decay**: reduce the rate by a fixed factor every N epochs.
- **Cosine annealing**: smoothly decrease the rate following a cosine curve, optionally with warm restarts.
- **Linear warm-up**: start with a very small rate and linearly increase it over the first few thousand steps, which stabilizes training for large-batch regimes and transformer models.

## Regularization and Generalization

Optimization and regularization are deeply intertwined. Techniques like **dropout**, **weight decay** (L2 regularization), **early stopping**, and **gradient clipping** all modify the optimization trajectory to favor solutions that generalize well to unseen data. The implicit regularization properties of SGD — arising from its noise and finite step size — are an active area of theoretical research.

## Conclusion

Modern machine learning optimization is a rich landscape spanning classical convex optimization theory and empirical deep-learning heuristics. The practitioner's toolkit — SGD, Adam, learning rate schedules, and regularization — has been refined through years of large-scale experimentation. Understanding these tools is essential for training effective, efficient, and robust models.
