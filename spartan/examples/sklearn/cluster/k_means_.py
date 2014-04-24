import numpy as np
import spartan
from spartan import expr, util
import parakeet
from spartan.array import distarray, extent
import time
import socket
from sys import stderr

@util.synchronized
@parakeet.jit
def _find_closest(pts, centers):
  idxs = np.zeros(pts.shape[0], np.int)
  for i in range(pts.shape[0]):
    min_dist = 1e9
    min_idx = 0
    p = pts[i]

    for j in xrange(centers.shape[0]):
      c = centers[j]
      dist = np.sum((p - c) ** 2)
      if dist < min_dist:
        min_dist = dist
        min_idx = j
    
    idxs[i] = min_idx
  return idxs

def _find_cluster_mapper(inputs, ex, d_pts, old_centers, 
                         new_centers, new_counts, labels):
  st = time.time()
  centers = old_centers
  pts = d_pts.fetch(ex)
  closest = _find_closest(pts, centers)
  
  l_counts = np.zeros((centers.shape[0], 1), dtype=np.int)
  l_centers = np.zeros_like(centers)
  
  for i in range(centers.shape[0]):
    matching = (closest == i)
    l_counts[i] = matching.sum()
    l_centers[i] = pts[matching].sum(axis=0) 
  
  # update centroid positions
  new_centers.update(extent.from_shape(new_centers.shape), l_centers)
  new_counts.update(extent.from_shape(new_counts.shape), l_counts)
  labels.update(extent.create(ex.ul, (ex.lr[0], 1), labels.shape), 
                closest.reshape(pts.shape[0], 1))
  return []


class KMeans(object):
  def __init__(self, n_clusters = 8,  n_iter=10):
    """K-Means clustering
    Parameters
    ----------

    n_clusters : int, optional, default: 8
        The number of clusters to form as well as the number of
        centroids to generate.

    n_iter : int, optional, default: 10
        Number of iterations of the k-means algorithm for a
        single run.
    """
    self.n_clusters = n_clusters
    self.n_iter = n_iter

  def fit(self, X, centers = None):
    """Compute k-means clustering.

    Parameters
    ----------
    X : spartan matrix, shape=(n_samples, n_features). It should be tiled by rows.
    centers : numpy.ndarray. The initial centers. If None, it will be randomly generated.
    """
    X = expr.force(X)
    num_dim = X.shape[1]
    labels = expr.zeros((X.shape[0],1), dtype=np.int, tile_hint=X.tile_shape()).force()
  
    if centers is None:
      centers = np.random.rand(self.n_clusters, num_dim)
    
    for i in range(self.n_iter):
      # Reset them to zero.
      new_centers = expr.ndarray((self.n_clusters, num_dim), reduce_fn=lambda a, b: a + b)
      new_counts = expr.ndarray((self.n_clusters, 1), dtype=np.int, reduce_fn=lambda a, b: a + b)
      
      _ = expr.shuffle(X,
                        _find_cluster_mapper,
                        kw={'d_pts' : X,
                            'old_centers' : centers,
                            'new_centers' : new_centers,
                            'new_counts' : new_counts,
                            'labels': labels
                            })
      _.force()

      new_counts = new_counts.glom()
      new_centers = new_centers.glom()
      
      # If any centroids don't have any points assigined to them.
      zcount_indices = (new_counts == 0).reshape(self.n_clusters)
      
      if np.any(zcount_indices):
        # One or more centroids may not have any points assigned to them,
        # which results in their position being the zero-vector.  We reseed these
        # centroids with new random values.
        n_points = np.count_nonzero(zcount_indices)
        # In order to get rid of dividing by zero.
        new_counts[zcount_indices] = 1
        new_centers[zcount_indices, :] = np.random.randn(n_points, num_dim)

      new_centers = new_centers / new_counts
      centers = new_centers
 
    return centers, labels#.glom().reshape(X.shape[0])
