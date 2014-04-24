import numpy as np
from numpy import linalg
import time
import scipy
from scipy.linalg import qr
import spartan
from spartan import expr

ctx = spartan.initialize()

def cqr(a):
  st = time.time()
  at = expr.dot(expr.transpose(a), a, tile_hint=(a.shape[1]/ctx.num_workers, a.shape[1])).force()
  print "matmul1", time.time() - st
   
  print at.tile_shape()

  st = time.time()
  at = at.glom()
  print "glom()", time.time() - st

  st = time.time()
  r = linalg.cholesky(at).T
  print "colesky", time.time() - st

  st = time.time()
  invr = np.linalg.inv(r)
  print "inv", time.time() - st
  
  st = time.time()
  invr = expr.from_numpy(invr, tile_hint=(invr.shape[0]/ctx.num_workers, invr.shape[1]))
  print "from numpy", time.time() - st

  st = time.time()
  q = expr.dot(a, invr).force()
  print "matmaul2", time.time() - st
  return q, r



n_per_worker = 5000

try:
  a = expr.randn(ctx.num_workers * n_per_worker, 1000, tile_hint=(n_per_worker, 1000)).force()
  st = time.time()
  q2, r2 = cqr(a)
  print "cqr : ", time.time() - st
finally:
  ctx.shutdown()

