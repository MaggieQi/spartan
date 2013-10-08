from . import util, wrap
from spartan.config import flags
from spartan.util import Assert
from wrap import DEBUG, INFO, WARN, ERROR, FATAL, set_log_level
import cPickle
import cProfile
import pstats
import sys
import traceback

class Sharder(object):
  def __call__(self, k, num_shards):
    assert False

class ModSharder(Sharder):
  def __call__(self, k, num_shards):
    return k.shard() % num_shards

def replace_accum(key, cur, update):
  return update

def sum_accum(key, cur, update):
  return cur + update

class Iter(object):
  def __init__(self, handle):
    self.handle = handle
    self._val = None
    
    if not wrap.iter_done(self.handle):
      self._val = (wrap.iter_key(self.handle), wrap.iter_value(self.handle)) 
    
  def __iter__(self):
    return self
    
  def next(self):
    if self._val is None:
      raise StopIteration
    
    result = self._val
    self._val = None
    
    wrap.iter_next(self.handle)
    if not wrap.iter_done(self.handle):
      self._val = (wrap.iter_key(self.handle), 
                   wrap.iter_value(self.handle))
    return result 

  
def key_mapper(k, v):
  yield k, 1
  
def keys(src):
  key_table = map_items(src, key_mapper)
  result = [k for k, _ in key_table]
  return result
        

class Table(object):
  def __init__(self, master, ptr_or_id):
    if master is not None:
      self.ctx = master
      self.destroy_on_del = True
    else:
      self.destroy_on_del = False
      self.ctx = wrap.get_context()
    
    if isinstance(ptr_or_id, int):
      self.handle = wrap.get_table(self.ctx, ptr_or_id)
    else:
      self.handle = ptr_or_id
      
  def __del__(self):
    if self.destroy_on_del:
      self.destroy()
          
  def __reduce__(self):
    return (Table, (None, self.id()))
    
  def id(self):
    return wrap.get_id(self.handle)
    
  def __getitem__(self, key):
    return wrap.get(self.handle, key)
  
  def __setitem__(self, key, value):
    return wrap.update(self.handle, key, value)
  
  def destroy(self):
    Assert.isinstance(self.ctx, Master) 
    return self.ctx.destroy_table(self.handle)
  
  def keys(self):
    # Don't create an iterator directly; this would have us 
    # copy all the values locally.  First construct a key-only
    # table
    return keys(self)
  
  def values(self):
    for _, v in iter(self):
      yield v
  
  def get(self, key):
    return wrap.get(self.handle, key)
  
  def update(self, key, value):
    return wrap.update(self.handle, key, value)
  
  def num_shards(self):
    return wrap.num_shards(self.handle)
  
  def flush(self):
    return wrap.flush(self.handle)
  
  def __iter__(self):
    return self.iter(-1)
  
  def iter(self, shard):
    return Iter(wrap.get_iterator(self.handle, shard))
  
  def sharder(self):
    return wrap.get_sharder(self.handle)
  
  def combiner(self):
    return wrap.get_combiner(self.handle)

  def reducer(self):
    return wrap.get_reducer(self.handle)
  
  def selector(self):
    return wrap.get_selector(self.handle)
  
  def shard_for_key(self, k):
    return wrap.shard_for_key(self.handle, k)

class Kernel(object):
  def __init__(self, kernel_id):
    self.handle = wrap.cast_to_kernel(kernel_id)
  
  def table(self, table_id):
    return Table(None, 
                 wrap.get_table(self.handle, table_id))
  
  def args(self):
    return wrap.kernel_args(self.handle)
  
  def current_shard(self):
    return int(self.args()['shard'])
  
  def current_table(self):
    return int(self.args()['table'])


class Worker(object):
  def __init__(self, handle):
    self.handle = handle
     
  def wait_for_shutdown(self):
    wrap.wait_for_shutdown(self.handle)
    

PROF = None

def _bootstrap_kernel(handle):
  kernel = Kernel(handle)
  fn, args = cPickle.loads(kernel.args()['map_args'])
 
  if not flags.profile_kernels:
    return fn(kernel, args)
  
  p = cProfile.Profile()
  p.enable()  
  result = fn(kernel, args)
  p.disable()
  stats = pstats.Stats(p)
  global PROF
  if PROF is None:
    PROF = stats
  else:
    PROF.add(stats)
  
  return result

class Master(object):
  def __init__(self, handle, shutdown_on_del=False):
    self.handle = handle
    self.shutdown_on_del = shutdown_on_del
     
  def __del__(self):
    if self.shutdown_on_del:
      util.log('Shutting down master.')
      wrap.shutdown(self.handle)
      
  def num_workers(self):
    return wrap.num_workers(self.handle)
    
  def destroy_table(self, table_handle):
    wrap.destroy_table(self.handle, table_handle)
    
  def create_table(self, 
                   sharder=ModSharder(), 
                   combiner=None,
                   reducer=replace_accum,
                   selector=None):
    
    Assert.isinstance(sharder, Sharder)
    #util.log('Creating table with sharder %s', sharder)
    return Table(self, 
                 wrap.create_table(self.handle, sharder, combiner, reducer, selector))
  
  def foreach_shard(self, table, kernel, args):
    return wrap.foreach_shard(
                          self.handle, table.handle, 
                          _bootstrap_kernel, (kernel, args))

  def foreach_worklist(self, worklist, mapper):
    mod_wl = []
    for args, locality in worklist:
      mod_wl.append(((mapper, args), locality))
      
    return wrap.foreach_worklist(self.handle, 
                                 mod_wl,
                                 _bootstrap_kernel)


def has_kw_args(fn):
  return fn.__code__.co_flags & 0x08

def mapper_kernel(kernel, args):
  src_id, dst_id, fn, kw = args
  
  src = kernel.table(src_id)
  dst = kernel.table(dst_id)
  
  assert not 'kernel' in kw
  kw['kernel'] = kernel
  
#   util.log('MAPPING: Function: %s, args: %s', fn, fn_args)
  
  for sk, sv in src.iter(kernel.current_shard()):
    if has_kw_args(fn):
      result = fn(sk, sv, **kw)
    else:
      assert len(kw) == 1, 'Arguments passed but function does not support **kw'
      result = fn(sk, sv)
      
    if result is not None:
      for k, v in result:
        dst.update(k, v)


def foreach_kernel(kernel, args):
  src_id, fn, kw = args
  assert not 'kernel' in kw
  kw['kernel'] = kernel
  
  src = kernel.table(src_id)
  for sk, sv in src.iter(kernel.current_shard()):
    if has_kw_args(fn):
      fn(sk, sv, **kw)
    else:
      assert len(kw) == 1, 'Arguments passed but function does not support **kw'
      fn(sk, sv)


def map_items(table, fn, **kw):
  src = table
  master = src.ctx
  
  dst = master.create_table(table.sharder(), 
                            table.combiner(), 
                            table.reducer(),
                            table.selector())
  master.foreach_shard(table, mapper_kernel, 
                       (src.id(), dst.id(), fn, kw))
  return dst


def map_inplace(table, fn, **kw):
  src = table
  dst = src
  table.ctx.foreach_shard(table, mapper_kernel, 
                          (src.id(), dst.id(), fn, kw))
  return dst


def foreach(table, fn, **kw):
  src = table
  master = src.ctx
  master.foreach_shard(table, foreach_kernel, 
                       (src.id(), fn, kw))


def fetch(table):
  out = []
  for k, v in table:
    out.append((k, v))
  return out


def get_master():
  return Master(wrap.cast_to_master(wrap.get_context()),
                shutdown_on_del = False)
  
def start_master(*args):
  return Master(wrap.start_master(*args), shutdown_on_del=True)

def start_worker(*args):
  return Worker(wrap.start_worker(*args))
