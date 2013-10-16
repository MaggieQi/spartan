#!/usr/bin/env python

'''Helper module for importing SWIG bindings.

Sets PYTHONPATH when running from the build directory,
and imports all symbols from the SWIG generated code.
''' 

from os.path import abspath
import sys
sys.path += [abspath('../build/.libs'), 
             abspath('../build/python/spartan/wrap'), 
             abspath('.')]

from spartan.config import flags
from spartan_wrap import set_log_level, TableContext
import atexit
import cPickle
import cProfile
import os
import pstats
import spartan_wrap
import threading
import traceback


log_mutex = threading.RLock()
def _log(msg, *args, **kw):
  level = kw.get('level', spartan_wrap.INFO)
  with log_mutex:
    caller = sys._getframe(2)
    filename = caller.f_code.co_filename
    lineno = caller.f_lineno
    if 'exc_info' in kw:
      exc = ''.join(traceback.format_exc())
    else:
      exc = None

    if isinstance(msg, str):
      msg = msg % args
    else:
      msg = repr(msg)
   
    msg = str(msg) 
    spartan_wrap.log(level, filename, lineno, msg)
    if exc is not None:
      spartan_wrap.log(level, filename, lineno, exc)

def log_info(msg, *args, **kw):
  kw['level'] = spartan_wrap.INFO
  return _log(msg, *args, **kw)

def log_debug(msg, *args, **kw):
  kw['level'] = spartan_wrap.DEBUG
  return _log(msg, *args, **kw)

def log_error(msg, *args, **kw):
  kw['level'] = spartan_wrap.ERROR
  return _log(msg, *args, **kw)

def log_warn(msg, *args, **kw):
  kw['level'] = spartan_wrap.WARN
  return _log(msg, *args, **kw)

class Sharder(object):
  def __call__(self, k, num_shards):
    assert False

class ModSharder(Sharder):
  def __call__(self, k, num_shards):
    return hash(k) % num_shards

def replace_accum(key, cur, update):
  return update

def sum_accum(key, cur, update):
  return cur + update

class Iter(object):
  def __init__(self, table, shard):
    self._table = table
    if shard == -1:
      wrap_iter = self._table.get_iterator()
    else:
      wrap_iter = self._table.get_iterator(shard)
      
    self._iter = wrap_iter
    self._val = None
    
    if not self._iter.done():
      self._val = (self._iter.shard(), self._iter.key(), self._iter.value())
    
  def __iter__(self):
    return self
  
  def next(self):
    if self._val is None:
      raise StopIteration
    
    result = self._val
    self._val = None
    
    self._iter.next()
    if not self._iter.done():
      self._val = (self._iter.shard(), self._iter.key(), self._iter.value())
    
    return result 

  
def key_mapper(k, v):
  yield k, 1
  
def keys(src):
  return map_items(src, key_mapper)

class Table(spartan_wrap.Table):
  def __init__(self, id, destroy_on_del=False):
    #print 'Creating table: %d, destroy? %d' % (id, destroy_on_del)
    spartan_wrap.Table.__init__(self, id)
    self.thisown = False
    self.destroy_on_del = destroy_on_del
      
  def __del__(self):
    if self.destroy_on_del:
      get_master().destroy_table(self)
          
  def __reduce__(self):
    return (Table, (self.id(), False))
  
  def iter(self, shard=-1):
    return Iter(self, shard)
  
  def __iter__(self):
    return self.iter()
    
  def keys(self):
    # Don't create an iterator directly; this would have us 
    # copy all the values locally.  Instead construct a key-only table
    return keys(self)
  
  def values(self):
    for _, v in iter(self):
      yield v

class Kernel(object):
  def __init__(self, handle):
    self._kernel = spartan_wrap.cast_to_kernel(handle)
  
  def table(self, id):
    return Table(id)
  
  def args(self):
    return self._kernel.args()
  
  def current_table(self):
    return int(self.args()['table'])
  
  def current_shard(self):
    return int(self.args()['shard'])
    
KERNEL_PROF = None

def _bootstrap_kernel(handle):
  kernel= Kernel(handle)
  fn, args = cPickle.loads(kernel.args()['map_args'])
 
  if not flags.profile_kernels:
    return fn(kernel, args)
  
  p = cProfile.Profile()
  p.enable() 
   
  result = fn(kernel, args)
  
  p.disable()
  stats = pstats.Stats(p)
  global KERNEL_PROF
  if KERNEL_PROF is None:
    KERNEL_PROF = stats
  else:
    KERNEL_PROF.add(stats)
  
  return result

class Master(object):
  def __init__(self, master, shutdown_on_del=False):
    self.shutdown_on_del = shutdown_on_del
    self._master = master
    
  def __getattr__(self, k):
    return getattr(self._master, k)
     
  def __del__(self):
    if self.shutdown_on_del:
      log_info('Shutting down master.')
      self._master.shutdown()
  
  def create_table(self, sharder, combiner, reducer, selector):
    t = self._master.create_table(sharder, combiner, reducer, selector)
    return Table(t.id(), destroy_on_del=True)
   
  def foreach_shard(self, table, kernel, args):
    return self._master.foreach_shard(table, _bootstrap_kernel, (kernel, args))

  def foreach_worklist(self, worklist, mapper):
    mod_wl = []
    for args, locality in worklist:
      mod_wl.append(((mapper, args), locality))
      
    return self._master.foreach_worklist(mod_wl, _bootstrap_kernel)


def has_kw_args(fn):
  return fn.__code__.co_flags & 0x08

def mapper_kernel(kernel, args):
  src_id, dst_id, fn, kw = args
  
  src = kernel.table(src_id)
  dst = kernel.table(dst_id)
  
  assert not 'kernel' in kw
  kw['kernel'] = kernel
  
#   log('MAPPING: Function: %s, args: %s', fn, fn_args)
  
  shard = kernel.current_shard()
  
  for _, sk, sv in src.iter(kernel.current_shard()):
    if has_kw_args(fn):
      result = fn(sk, sv, **kw)
    else:
      assert len(kw) == 1, 'Arguments passed but function does not support **kw'
      result = fn(sk, sv)
      
    if result is not None:
      for k, v in result:
        dst.update(shard, k, v)
        #dst.update(-1, k, v)


def foreach_kernel(kernel, args):
  src_id, fn, kw = args
  assert not 'kernel' in kw
  kw['kernel'] = kernel
  
  src = kernel.table(src_id)
  for _, sk, sv in src.iter(kernel.current_shard()):
    if has_kw_args(fn):
      fn(sk, sv, **kw)
    else:
      assert len(kw) == 1, 'Arguments passed but function does not support **kw'
      fn(sk, sv)


def map_items(table, mapper_fn, combine_fn=None, reduce_fn=None, **kw):
  src = table
  master = get_master()
  
  dst = master.create_table(table.sharder(),
                            combine_fn,
                            reduce_fn,
                            table.selector())
  
  master.foreach_shard(table, mapper_kernel, 
                       (src.id(), dst.id(), mapper_fn, kw))
  return dst


def map_inplace(table, fn, **kw):
  src = table
  dst = src
  master = get_master()
  master.foreach_shard(table, mapper_kernel, 
                       (src.id(), dst.id(), fn, kw))
  return dst


def foreach(table, fn, **kw):
  src = table
  master = get_master()
  master.foreach_shard(table, foreach_kernel, 
                       (src.id(), fn, kw))


def fetch(table):
  out = []
  for s, k, v in table:
    out.append((k, v))
  return out


def get_master():
  return Master(spartan_wrap.cast_to_master(spartan_wrap.TableContext.get_context()),
                shutdown_on_del = False)
  
def start_master(*args):
  m = spartan_wrap.start_master(*args)
  return Master(m, 
                shutdown_on_del=True)

def start_worker(*args):
  return spartan_wrap.start_worker(*args)

