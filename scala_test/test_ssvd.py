import numpy as np
from numpy import linalg
from scipy.sparse.linalg import svds
from scipy.linalg import svd, qr as sqr

import time
import math
import spartan
from spartan import expr
from spartan.examples.ssvd import svd
from spartan.examples.ssvd import qr
from spartan import util
from numpy import absolute as abs

M = 32000 

ctx = spartan.initialize()
M = int(3200 * ctx.num_workers)
N = 2000 
k = 500 

try:
  A = expr.rand(M, N, tile_hint=(M/ctx.num_workers, N)).force()
  print M
  #U, S, V = np.linalg.svd(A.glom(), full_matrices=0)
  st =time.time()
  U2, S2, V2 = svd(A, k)
  print "time : ", time.time() - st 

  #assert np.allclose(abs(U), abs(U2.glom()))
  #assert np.allclose(abs(V), abs(V2))
  #assert np.allclose(abs(S), abs(S2))
finally:
  ctx.shutdown()

