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
  print DIM
  A = expr.randn(*DIM, tile_hint=(DIM[0] / n_workers, DIM[1]), dtype=np.float32).force() 

  print "after init array"
  #expr.write(A, slice(0, D, None), generate_random_array(*DIM), slice(0, D, None)).force()

  st = time.time()
  svd.svds(A, D)
  print time.time() - st
finally:
  ctx.shutdown()






