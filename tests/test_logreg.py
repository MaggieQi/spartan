from spartan.examples import logistic_regression
from spartan import expr, util
import test_common
import time

N_EXAMPLES = 100
N_DIM = 3
ITERATION = 5

class TestLogisticRegression(test_common.ClusterTest):
  def test_logreg(self):
    logistic_regression.run(N_EXAMPLES, N_DIM, ITERATION)

def benchmark_logreg(ctx, timer):
  print "#worker:", ctx.num_workers
  N_EXAMPLES = 40000000 * ctx.num_workers
  x = expr.eager(expr.rand(N_EXAMPLES, N_DIM, tile_hint=(N_EXAMPLES / ctx.num_workers, N_DIM)))
  y = expr.eager(expr.rand(N_EXAMPLES, 1, tile_hint=(N_EXAMPLES / ctx.num_workers, 1)))
  start = time.time()
  logistic_regression.logistic_regression(x, y, ITERATION)

  total = time.time() - start
  util.log_warn("time cost : %s s" % (total*1.0/ITERATION,))
  
if __name__ == '__main__':
  test_common.run(__file__)
