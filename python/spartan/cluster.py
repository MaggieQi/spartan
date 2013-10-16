from spartan import config, util
from spartan.config import flags
import os.path
import socket
import spartan
import subprocess
import threading
import time

def start_local_worker(master, port):
  wthread = threading.Thread(target=spartan.start_worker,
                             args=(master,port,))
  wthread.daemon = True
  wthread.start()
  return wthread
  
def start_remote_worker(worker, st, ed):
  util.log_info('Starting worker %d:%d on host %s', st, ed, worker)
  
  #os.system('mkdir operf.%s' % worker)
  args = ['ssh', 
          '-oForwardX11=no',
          worker,
          'cd %s && ' % os.path.abspath(os.path.curdir),
          #'xterm', '-e',
          #'gdb', '-ex', 'run', '--args',
          #'operf -e CPU_CLK_UNHALTED:100000000', '-g', '-d', 'operf.%s' % worker,
          'python', '-m spartan.worker',
          '--master=%s:9999' % socket.gethostname(),
          '--count=%d' % (ed - st),
          '--port=%d' % (10000)]
  
  for name, value in config.flags:
    args.append('--%s=%s' % (name, value))
  
  #print args
  time.sleep(0.1)
  p = subprocess.Popen(args, executable='ssh')
  return p

def start_cluster(num_workers, local=not flags.cluster):
  master = spartan.start_master(9999, num_workers)
  spartan.set_log_level(flags.log_level)
  time.sleep(0.1)

  if local:
    for i in range(num_workers):  
      start_local_worker('%s:9999' % socket.gethostname(),  10000 + i)
    return master
  
  count = 0
  num_hosts = len(config.HOSTS)
  for worker, total_tasks in config.HOSTS:
    sz = util.divup(num_workers, num_hosts)
    #sz = total_tasks
    sz = min(sz, num_workers - count)
    start_remote_worker(worker, count, count + sz)
    count += sz
    if count == num_workers:
      break
    
  return master

