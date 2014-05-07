#!/usr/bin/env python

import collections
from spartan import util
from spartan.util import Assert
import numpy as np
cimport numpy as np

cimport cython

# Can't understand following declaration errors
# Following line makes parakeet with old cython (0.15) report error
#ctypedef unsigned int coordinate_t
# Following line makes parakeet report error
#ctypedef unsigned long long coordinate_t

ctypedef np.int64_t coordinate_t
# Hopfully, 32-dimension is enough.
cdef enum:
  MAX_DIM=32

cdef class TileExtent(object):
  '''A rectangular tile of a distributed array.
  
  These correspond (roughly) to a `slice` taken from an array
  (without any step component).
  
  Arrays are indexed from the upper-left; for an array of shape
  (sx, sy, sz): (0,0...) is the upper-left corner of an array, 
  and (sx,sy,sz...) the lower-right.
  
  Extents are represented by an upper-left corner (inclusive) and
  a lower right corner (exclusive): [ul, lr).  In addition, they
  carry the shape of the array they are a part of; this is used to
  compute global position information.
  '''
  cdef public tuple array_shape
  cdef coordinate_t _ul[MAX_DIM]
  cdef coordinate_t _lr[MAX_DIM]
  cdef unsigned int _ul_len

  def get_ul(self):
    return tuple([self._ul[i] for i in range(self._ul_len)])

  def set_ul(self, tuple ul):
    self._ul_len = len(ul)
    for i in range(self._ul_len):
      self._ul[i] = ul[i]

  def get_lr(self):
    return tuple([self._lr[i] for i in range(self._ul_len)])

  def set_lr(self, tuple lr):
    self._ul_len = len(lr)
    for i in range(self._ul_len):
      self._lr[i] = lr[i]

  ul = property(get_ul, set_ul)
  lr = property(get_lr, set_lr)

  @property
  def size(self):
    return np.prod(self.shape)
  
  @property
  def shape(self):
    result = []
    for i in range(self._ul_len):
      result.append(self._lr[i] - self._ul[i])
      result[i] = 1 if result[i] == 0 else result[i]
    return tuple(result)
  
  @property
  def ndim(self):
    return self._ul_len

  def __reduce__(self):
    return create, (self.ul, self.lr, self.array_shape)
  
  def to_slice(self):
    result = []
    for i in range(self._ul_len):
      result.append(slice(self.ul[i], self.lr[i], None))
    return tuple(result)
  
  def __repr__(self):
    return 'extent(' + ','.join('%s:%s' % (a, b) for a, b in zip(self.ul, self.lr)) + ')'

  
  def __getitem__(self, idx):
    return create((self.ul[idx],),
                  (self.lr[idx],),
                  (self.array_shape[idx],))

  def __hash__(self):
    return hash(self.ul)
    #return hash(self.ul[-2:])
    #return ravelled_pos(self.ul, self.array_shape)
    
  def __richcmp__(self, other, operation):
    if operation == 0 or operation == 4: # smaller or bigger
      smaller = True
      for i in range(len(self.ul)):
        if self.ul[i] < other.ul[i]:
           smaller = True
           break
        elif self.ul[i] > other.ul[i]:
           smaller = False
           break
      return smaller if operation == 0 else (not smaller)
    elif operation == 2: # eq
      return isinstance(other, TileExtent) and \
             self.ul == other.ul and  \
             self.lr == other.lr
    elif operation == 3: # not eq
      return not isinstance(other, TileExtent) or \
             self.ul != other.ul or \
             self.lr != other.lr
    else:
      assert False, 'Unsupported comparison operation %d' % operation

  def ravelled_pos(self):
    return ravelled_pos(self.ul, self.array_shape)
  
  def to_global(self, idx, axis):
    '''Convert ``idx`` from a local offset in this tile to a global offset.'''
    if axis is not None:
      return idx + self.ul[axis]

    local_idx = unravelled_pos(idx, self.shape)
    return ravelled_pos(np.asarray(self.ul) + local_idx, self.array_shape)

  def add_dim(self):
    #util.log_info('ul:%s lr:%s array_shape:%s', self.ul + (0,), self.lr + (1,), self.array_shape + (1,))
    return create(self.ul + (0,),
                  self.lr + (1,),
                  self.array_shape + (1,))

  def clone(self):
    return c_create(self._ul, self._lr, self.array_shape, self._ul_len)
 
#import traceback
counts = collections.defaultdict(int)

cdef _valid(TileExtent ex, coordinate_t *ul, coordinate_t *lr, array_shape):
  for idx in range(ex._ul_len):
    # If we got an unrealistic (ul, lr), return None.
    if ul[idx] >= lr[idx]:
      return None
    ex._ul[idx] = ul[idx]
    ex._lr[idx] = lr[idx]

  if array_shape is not None:
    ex.array_shape = tuple(array_shape)
  else:
    ex.array_shape = None
  return ex

cdef c_create(coordinate_t *ul, coordinate_t *lr, array_shape, unsigned int ul_len):
  cdef TileExtent ex = TileExtent()
  ex._ul_len = ul_len

  return _valid(ex, ul, lr, array_shape)
  
cpdef create(ul, lr, array_shape):
  '''
  Create a new extent with the given coordinates and array shape.
  
  :param ul: `tuple`: 
  :param lr:
  :param array_shape:
  '''
  cdef TileExtent ex = TileExtent()
  ex._ul_len = len(ul)

  # In order to reuse code, we copy twice.
  # If it is too slow, duplicate _valid code to here.
  for idx in range(ex._ul_len):
    ex._ul[idx] = ul[idx]
    ex._lr[idx] = lr[idx]

  return _valid(ex, ex._ul, ex._lr, array_shape)

def from_shape(shp):
  cdef coordinate_t ul[MAX_DIM]
  cdef coordinate_t lr[MAX_DIM]
  cdef unsigned int ul_len, i

  ul_len = len(shp)
  for i in range(ul_len):
    ul[i] = 0
    lr[i] = shp[i]
  return c_create(ul, lr, shp, ul_len)

@cython.cdivision(True)
cpdef unravelled_pos(idx, array_shape): 
  '''
  Unravel ``idx`` into an index into an array of shape ``array_shape``.
  :param idx: `int`
  :param array_shape: `tuple`
  :rtype: `tuple` indexing into ``array_shape``
  '''
  
  unravelled = []
  for dim in reversed(array_shape):
    unravelled.append(idx % dim)
    idx /= dim
  
  return tuple(reversed(unravelled))
    
cpdef ravelled_pos(idx, array_shape):
  rpos = 0
  mul = 1
  
  for i in range(len(array_shape) - 1, -1, -1):
    rpos += mul * idx[i]
    mul *= array_shape[i]
  
  return rpos

@cython.boundscheck(False)
def all_nonzero_shape(shape):
  '''
  Check if the shape is valid (all elements are biger than zero). This is equal to
  np.all(shape) but is faster because this API doesn't create a numpy array.
  '''
  cdef unsigned int i
  for i in shape:
    if i == 0:
      return False
  return True

@cython.cdivision(True)
def find_rect(ravelled_ul, ravelled_lr, shape):
  '''
  Return a new (ravellled_ul, ravelled_lr) to make a rectangle for `shape`.
  If (ravelled_ul, ravelled_lr) already forms a rectangle, just return it.

  :param ravelled_ul:
  :param ravelled_lr:
  '''
  if shape[-1] == 1 or ravelled_ul / shape[-1] == ravelled_lr / shape[-1]:
    rect_ravelled_ul = ravelled_ul
    rect_ravelled_lr = ravelled_lr
  else:
    div = 1
    for i in shape[1:]:
      div = div * i
    rect_ravelled_ul = ravelled_ul - (ravelled_ul % div)
    rect_ravelled_lr = ravelled_lr + (div - ravelled_lr % div) % div - 1

  return (rect_ravelled_ul, rect_ravelled_lr)

def find_overlapping(extents, region):
  '''
  Return the extents that overlap with ``region``.   
  
  :param extents: List of extents to search over.
  :param region: `Extent` to match.
  '''
  for ex in extents:
    overlap = intersection(ex, region)
    if overlap is not None:
      yield (ex, overlap)
      
def compute_slice(TileExtent base, idx):
  '''Return a new ``TileExtent`` representing ``base[idx]``
  
  :param base: `TileExtent`
  :param idx: int, slice, or tuple(slice,...)
  '''
  assert not np.isscalar(idx), idx
  if not isinstance(idx, tuple):
    idx = (idx,)
    
  cdef coordinate_t ul[MAX_DIM]
  cdef coordinate_t lr[MAX_DIM]
  cdef unsigned int i

  array_shape = base.array_shape
  for i in range(base._ul_len):
    if i >= len(idx):
      ul[i] = base.ul[i]
      lr[i] = base.lr[i]
    else:
      start, stop, step = idx[i].indices(base.shape[i])
      ul[i] = base.ul[i] + start
      lr[i] = base.ul[i] + stop
  
  return c_create(ul, lr, array_shape, base._ul_len)

def offset_from(TileExtent base, TileExtent other):
  '''
  :param base: `TileExtent` to use as basis
  :param other: `TileExtent` into the same array.
  :rtype: A new extent using this extent as a basis, instead of (0,0,0...) 
  '''
  cdef coordinate_t ul[MAX_DIM]
  cdef coordinate_t lr[MAX_DIM]
  cdef unsigned int i

  for i in range(base._ul_len):
    if (other._ul[i] < base.ul[i]) or (other._lr[i] > base.lr[i]):
      assert False
    ul[i] = other._ul[i] - base._ul[i]
    lr[i] = other._lr[i] - base._ul[i]

  return c_create(ul, lr, other.array_shape, base._ul_len)

cpdef offset_slice(TileExtent base, TileExtent other):
  '''
  :param base: `TileExtent` to use as basis
  :param other: `TileExtent` into the same array.
  :rtype: A slice representing the local offsets of ``other`` into this tile.
  '''
  return tuple([slice(other._ul[i] - base._ul[i],
                       other._lr[i] - base._ul[i],
                       None) for i in range(base._ul_len)])

def from_slice(idx, shape):
  '''
  Construct a `TileExtent` from a slice or tuple of slices.
  
  :param idx: int, slice, or tuple(slice...)
  :param shape: shape of the input array
  :rtype: `TileExtent` corresponding to ``idx``.
  '''
  if not isinstance(idx, tuple):
    idx = (idx,)
  
  if len(idx) < len(shape):
    idx = tuple(list(idx) + [slice(None, None, None) 
                             for _ in range(len(shape) - len(idx))])
    
  cdef coordinate_t ul[MAX_DIM]
  cdef coordinate_t lr[MAX_DIM] 
  cdef unsigned int ul_len, i
 
  ul_len = len(shape)
  for i in range(ul_len):
    dim = shape[i]
    slc = idx[i]
    
    if np.isscalar(slc):
      slc = int(slc)
      slc = slice(slc, slc + 1, None)
    
    if slc.start > 0: assert slc.start <= dim
    if slc.stop > 0: assert slc.stop <= dim
    
    indices = slc.indices(dim)
    ul[i] = indices[0]
    lr[i] = indices[1]
    
  return c_create(ul, lr, shape, ul_len)

cpdef intersection(TileExtent a, TileExtent b):
  '''
  :rtype: The intersection of the 2 extents as a `TileExtent`, 
          or None if the intersection is empty.  
  '''
  if a is None:
    return None
  
  Assert.eq(a.array_shape, b.array_shape, 'Tiles must have compatible shapes!')

  cdef coordinate_t ul[MAX_DIM]
  cdef coordinate_t lr[MAX_DIM]
  cdef unsigned int i

  for i in range(a._ul_len):
    if b._lr[i] < a._ul[i]: return None
    if a._lr[i] < b._ul[i]: return None
    ul[i] = a._ul[i] if a._ul[i] >= b._ul[i] else b._ul[i]
    lr[i] = a._lr[i] if a._lr[i] <  b._lr[i] else b._lr[i]

  return c_create(ul, lr, a.array_shape, a._ul_len)


def shape_for_reduction(input_shape, axis):
  '''
  Return the shape for the result of applying a reduction along ``axis`` to 
  an input of shape ``input_shape``.
  :param input_shape:
  :param axis:
  '''
  if axis == None: return ()
  input_shape = list(input_shape)
  del input_shape[axis]
  return input_shape


def shapes_match(offset, data):
  '''
  Return true if the shape of ``data`` matches the extent ``offset``. 
  :param offset:
  :param data:
  '''
  return np.all(offset.shape == data.shape)

def drop_axis(TileExtent ex, axis):
  if axis is None: return create((), (), ())
  if axis < 0: axis = ex._ul_len + axis
  
  cdef coordinate_t ul[MAX_DIM]
  cdef coordinate_t lr[MAX_DIM]
  cdef unsigned int i

  shape = list(ex.array_shape)
  del shape[axis]
  for i in range(axis):
    ul[i] = ex._ul[i]
    lr[i] = ex._lr[i]

  for i in range(axis + 1, ex._ul_len):
    ul[i - 1] = ex._ul[i]
    lr[i - 1] = ex._lr[i]

  return c_create(ul, lr, shape, ex._ul_len - 1)
 
def index_for_reduction(index, axis):
  return drop_axis(index, axis)
        
def find_shape(extents):
  '''
  Given a list of extents, return the shape of the array
  necessary to fit all of them.
  :param extents:
  '''
  #util.log_info('Finding shape... %s', extents)
  shape = np.max([ex.lr for ex in extents], axis=0)
  shape[shape == 0] = 1
  return tuple(shape)


def is_complete(shape, slices):
  '''
  Returns true if ``slices`` is a complete covering of shape; that is:

  ::

    array[slices] == array

  :param shape: tuple of int
  :param slices: list/tuple of `slice` objects
  :rtype: boolean
  '''
  if len(shape) != len(slices):
    return False

  for dim,slice in zip(shape, slices):
    if slice.start > 0: return False
    if slice.stop < dim: return False
  return True
