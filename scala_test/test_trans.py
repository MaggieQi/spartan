import numpy as np
import spartan
from spartan.examples import svd
from spartan import expr
from numpy import linalg
from spartan import blob_ctx
from scipy.sparse.linalg import eigs, svds
import time
from spartan.examples import lanczos

D = 18 

ctx = spartan.initialize()

try:
  n_workers = blob_ctx.get().num_workers 
  SIZE = int(10000 * np.sqrt(n_workers))
  DIM = (SIZE, SIZE)

  A = expr.randn(*DIM, tile_hint=(DIM[0] / n_workers, DIM[1]), dtype=np.float32).force() 
  AT = expr.transpose(A).force()

  v = np.random.randn(AT.shape[1], 1) 

  print "----------------------begin dot--------------------"
  res = expr.dot(AT, v).force()


  #res2 = np.dot(AT.glom(), v) 
  #assert np.allclose(res.glom(), res2) 
finally:
  ctx.shutdown()






