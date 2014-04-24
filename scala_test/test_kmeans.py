import numpy as np
import spartan
from spartan import expr
from numpy import linalg
from scipy.sparse.linalg import svds
import time
from spartan.examples.sklearn.cluster import KMeans 

ctx = spartan.initialize()

DIM = 32
SAMPLES = ctx.num_workers * 5000000

K = 10 

try:
  points = expr.randn(SAMPLES, DIM, tile_hint=(SAMPLES/ctx.num_workers, DIM)).force()
  print ctx.num_workers

  centers = np.random.randn(K, DIM)

  m = KMeans(n_clusters = K, n_iter=5)

  st = time.time()
  res, inds = m.fit(points, centers)
  print "cost:", time.time() - st

finally:
  ctx.shutdown()




