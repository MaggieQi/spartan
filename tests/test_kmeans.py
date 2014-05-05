import test_common
import spartan
from spartan.examples.sklearn.cluster import KMeans
from spartan.examples.sklearn.cluster.kmeans import kmeans
from spartan import expr
from spartan.util import divup
import time
N_PTS = 10*10
N_CENTERS = 10
N_DIM = 5
ITER = 3

class TestKmeans(test_common.ClusterTest):
  def test_kmeans_expr(self):
    ctx = spartan.blob_ctx.get()
    pts = expr.rand(N_PTS, N_DIM,
                  tile_hint=(divup(N_PTS, ctx.num_workers), N_DIM)).force()

    t1 = time.time()    
    k = KMeans(N_CENTERS, ITER)
    k.fit(pts).force()
    print 'orig kmean:', time.time() - t1

    t2 = time.time()
    l = kmeans(pts, N_CENTERS, ITER).force()
    print 'new kmean:', time.time() - t2

def benchmark_kmeans(ctx, timer):
  N_PTS = 1000 * ctx.num_workers
  pts = expr.rand(N_PTS, N_DIM,
                  tile_hint=(divup(N_PTS, ctx.num_workers), N_DIM)).force()

  t1 = time.time()    
  k = KMeans(N_CENTERS, ITER)
  k.fit(pts).force()
  print 'orig kmean:', time.time() - t1

  t2 = time.time()
  l = kmeans(pts, N_CENTERS, ITER).force()
  print 'new kmean:', time.time() - t2

if __name__ == '__main__':
  test_common.run(__file__)
