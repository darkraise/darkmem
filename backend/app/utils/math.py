import numpy as np


def pca_2d(vectors: list[list[float]]) -> list[list[float]]:
    mat = np.array(vectors, dtype=np.float32)
    mat -= mat.mean(axis=0)
    cov = np.cov(mat, rowvar=False)
    eigenvalues, eigenvectors = np.linalg.eigh(cov)
    idx = np.argsort(eigenvalues)[::-1][:2]
    projection = mat @ eigenvectors[:, idx]
    pmax = np.abs(projection).max(axis=0, keepdims=True)
    pmax[pmax == 0] = 1
    projection = projection / pmax
    return projection.tolist()
