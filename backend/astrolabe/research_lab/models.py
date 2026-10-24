"""E001 models: B0 no-change, B1/B1h OLS through origin, B2/B3 ridge (numpy closed form)."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

LAMBDA_GRID = (0.1, 1.0, 10.0, 100.0, 1000.0)


def fit_origin_ols(x: np.ndarray, y: np.ndarray) -> float:
    """Slope of OLS through the origin: sum(xy)/sum(xx) (0 if x is all zero)."""
    d = float(np.dot(x, x))
    return float(np.dot(x, y) / d) if d > 0 else 0.0


@dataclass
class Ridge:
    """Ridge with train-only standardisation and an unpenalised intercept.

    beta = (Z'Z + lambda I)^-1 Z'(y - ybar), Z = (X - mu) / sd fitted on the training data only.
    """

    lam: float
    mu: np.ndarray | None = None
    sd: np.ndarray | None = None
    ybar: float = 0.0
    beta: np.ndarray | None = None

    def fit(self, X: np.ndarray, y: np.ndarray) -> Ridge:
        self.mu = X.mean(axis=0)
        sd = X.std(axis=0)
        self.sd = np.where(sd > 0, sd, 1.0)
        Z = (X - self.mu) / self.sd
        self.ybar = float(y.mean())
        A = Z.T @ Z + self.lam * np.eye(Z.shape[1])
        self.beta = np.linalg.solve(A, Z.T @ (y - self.ybar))
        return self

    def predict(self, X: np.ndarray) -> np.ndarray:
        assert self.beta is not None and self.mu is not None and self.sd is not None
        return ((X - self.mu) / self.sd) @ self.beta + self.ybar


def choose_lambda(
    X_fit: np.ndarray,
    y_fit: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    grid: tuple[float, ...] = LAMBDA_GRID,
) -> float:
    """Grid value with the lowest validation SSE (first on ties). Test data never enters."""
    best, best_sse = grid[0], np.inf
    for lam in grid:
        sse = float(np.sum((y_val - Ridge(lam).fit(X_fit, y_fit).predict(X_val)) ** 2))
        if sse < best_sse:
            best, best_sse = lam, sse
    return best


def fit_predict_all(train: dict, test: dict, lam_b2: float, lam_b3: float) -> dict[str, np.ndarray]:
    """Fit B1, B1h, B2, B3 on ``train`` (y, chg_1d, chg_1h, X2, X3) and predict ``test``."""
    out = {"B0": np.zeros(len(test["y"]))}
    out["B1"] = fit_origin_ols(train["chg_1d"], train["y"]) * test["chg_1d"]
    out["B1h"] = fit_origin_ols(train["chg_1h"], train["y"]) * test["chg_1h"]
    out["B2"] = Ridge(lam_b2).fit(train["X2"], train["y"]).predict(test["X2"])
    out["B3"] = Ridge(lam_b3).fit(train["X3"], train["y"]).predict(test["X3"])
    return out
