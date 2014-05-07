'''
Dot expr.
'''

import numpy as np
import scipy.sparse as sp
from .. import sparse, rpc
from .base import Expr, lazify
from .. import blob_ctx, util
from ..util import is_iterable, Assert
from ..array import extent, tile, distarray
from .shuffle import target_mapper, notarget_mapper
from ..core import LocalKernelResult
from traits.api import PythonValue, HasTraits

def _dot_mapper(inputs, ex, av, bv, local_reduction=None):
  # read current tile of array 'a'
  ex_a = ex
  # fetch all column tiles of b that correspond to tile a's rows, i.e.
  # rows = ex_a.cols (should be ex_a.rows?)
  # cols = *
  ex_b = extent.create((ex_a.ul[1], 0),
                       (ex_a.lr[1], bv.shape[1]),
                       bv.shape)

  time_a, a = util.timeit(lambda: av.fetch(ex_a))
  #util.log_info('Fetched...%s in %s', ex_a, time_a)
  time_b, b = util.timeit(lambda: bv.fetch(ex_b))
  util.log_debug('Fetched...ax:%s in %s, bx:%s in %s', ex_a, time_a, ex_b, time_b)

  #util.log_info('%s %s %s', type(a), a.shape, a.dtype)
  #util.log_info('%s %s %s', type(b), b.shape, b.dtype)
  #util.log_info('%s %s', bv.shape, len(bv.tiles))

  #util.log_info('%s %s', type(a), type(b))

  #if not sp.issparse(a):
  #  a = sp.csr_matrix(a)
  #if not sp.issparse(b):
  #  b = sp.csr_matrix(b)

  #result = a.dot(b)
  if isinstance(a, sp.coo_matrix) and b.shape[1] == 1:
    if local_reduction is None:
      result = sparse.dot_coo_dense_unordered_map_old(a, b)
    else:
      result = sparse.dot_coo_dense_unordered_map(a, b, local_reduction)
  else:
    result = a.dot(b)

  
  target_shape = (av.shape[0], bv.shape[1])
  ul = np.asarray([ex_a.ul[0], 0])
  lr = ul + target_shape
  target_ex = extent.create(ul, lr, target_shape)

  # util.log_info('A: %s', a.dtype)
  # util.log_info('B: %s', b.dtype)
  # util.log_info('R: %s', result.dtype)
  # util.log_info('T: %s', target_ex)

  # util.log_info('%s %s %s', a.shape, b.shape, result.shape)
  # util.log_info('%s %s %s', ul, lr, target_shape)
  yield target_ex, result


def _dot_numpy(array, ex, numpy_data=None):
  l = array.fetch(ex)
  r = numpy_data[ex.ul[1]:ex.lr[1]]

  yield (extent.create((ex.ul[0], 0), (ex.lr[0], r.shape[1]), (array.shape[0], r.shape[1])), l.dot(r))

class DotExpr(Expr):
  matrix_a = PythonValue(None, desc="np.ndarray or Expr")
  matrix_b = PythonValue(None, desc="np.ndarray or Expr")
  tile_hint = PythonValue(None, desc="Tuple or None")

  def __str__(self):
    return 'Dot[%s, %s]' % (self.matrix_a, self.matrix_b)

  def compute_shape(self):
    # May raise NotShapeable
    return (self.matrix_a.shape[0], self.matrix_b.shape[1])

  def _evaluate(self, ctx, deps):
    av = deps['matrix_a']
    bv = deps['matrix_b']

    Assert.eq(av.shape[1], bv.shape[0])

    if isinstance(bv, np.ndarray):
      if len(bv.shape) < 2:
        bv = bv.reshape((bv.shape[0], 1))
        
      if self.tile_hint is None:
        tile_hint = (av.tile_shape()[0], bv.shape[1])
      else:
        tile_hint = self.tile_hint
        
      target = distarray.create((av.shape[0], bv.shape[1]), dtype=av.dtype,
                                tile_hint=tile_hint, reducer=np.add)

      fn_kw = dict(numpy_data = bv)
      av.foreach_tile(mapper_fn = target_mapper,
                      kw = dict(source=av, 
                                map_fn=_dot_numpy,
                                target=target,
                                fn_kw=fn_kw))
    else:
      if self.tile_hint is None:
        tile_hint = np.maximum(av.tile_shape(), bv.tile_shape())
      else:
        tile_hint = self.tile_hint
      sparse=(av.sparse and bv.sparse)
      target = distarray.create((av.shape[0], bv.shape[1]), dtype=av.dtype,
                                tile_hint=tile_hint, reducer=np.add,
                                sparse=sparse)
      #fn_kw = dict(av = av, bv = bv)
      fn_kw = dict(av = av, bv = bv, local_reduction=True)
      av.foreach_tile(mapper_fn = target_mapper,
                      kw = dict(map_fn=_dot_mapper,
                                source=av,
                                target=target,
                                fn_kw=fn_kw))
    return target

def dot(a, b, tile_hint=None):
  '''
  Compute the dot product (matrix multiplication) of 2 arrays.

  :param a: `Expr` or `numpy.ndarray`
  :param b: `Expr` or `numpy.ndarray`
  :rtype: `Expr`
  '''
  return DotExpr(matrix_a = a, matrix_b = b, tile_hint=tile_hint)

