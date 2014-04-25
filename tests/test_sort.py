from spartan import expr, util
import test_common
from test_common import millis
import numpy as np
from datetime import datetime

#@test_common.with_ctx
#def test_pr(ctx):
def benchmark_sort(ctx, timer):
  print "#worker:", ctx.num_workers
  SIZE = 10000000 * ctx.num_workers
  A = expr.rand(SIZE, tile_hint=(SIZE/ctx.num_workers,)).force()
  t1 = datetime.now()
  T = expr.sort(A)
  t2 = datetime.now()
  print "time cost:", millis(t1, t2)
  #print np.all(np.equal(T.glom(), np.sort(A.glom(), axis=None)))
  
if __name__ == '__main__':
  test_common.run(__file__)
