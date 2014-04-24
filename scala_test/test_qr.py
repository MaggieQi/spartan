import numpy as np
from numpy import linalg
from scipy.sparse.linalg import svds
from scipy.linalg import svd, qr as sqr

import time
import math
import spartan
from spartan import expr
from spartan.examples.ssvd import solve
from spartan.examples.ssvd import qr
from spartan import util
from numpy import absolute as abs

M = 320 
N = 20 
k = 100 

ctx = spartan.initialize()

def fake_svd(A):
  omega = np.random.randn(A.shape[1], A.shape[1])
  Y = np.dot(A, omega)
  Q, R = linalg.qr(Y)
  B = np.dot(Q.T, A)
  BBT = np.dot(B, B.T) 
  D, U_ = linalg.eig(BBT) 

  D = np.sqrt(D)
  si = np.argsort(D)[::-1]

  U_ = U_[:, si]
  D  = D[si]
  U = np.dot(Q, U_)
  V = np.dot(np.dot(B.T, U_), np.diag(np.ones(D.shape[0]) / D))
  return U, D, V.T

try:
  A = expr.rand(M, N).force()
  U, S, V = np.linalg.svd(A.glom(), full_matrices=0)

  U2, S2, V2 = solve(A, A.shape[1])
  

  assert np.allclose(abs(U), abs(U2.glom()))
  assert np.allclose(abs(V), abs(V2))
  assert np.allclose(abs(S), abs(S2))

finally:
  ctx.shutdown()

