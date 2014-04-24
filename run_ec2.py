#!/usr/bin/env python
import sys
import os
import subprocess
import time
import getopt

import threading


class ClientThread(threading.Thread):
  def __init__(self, cmd):
    super(ClientThread, self).__init__()
    self._cmd = cmd

  def run(self):
    for cmd in self._cmd:
      while True:
        result = subprocess.call(cmd, shell=True)
        if result == 0:
          break
        time.sleep(5)

class Ec2Launch(object):
  def __init__(self, *args, **kargs):
    self.workers = kargs.get('workers', 4)
    self.num_of_instances = kargs.get('num_of_instances', 2)
    self.ami = kargs.get('ami', 'ami')
    self.instance_name = kargs.get('instance_name', 'spartan')
    self.user = kargs.get('users', 'ubuntu')
    self.perm = kargs.get('pem', 'spartan.pem')
    self.instance_type = kargs.get('instance_type', 't1.micro')
    self.master = kargs.get('master', None)

    self.environ()
    
    self._get_instances()

  def _get_instances(self):
    # Init instance if found

    self.instances = {}
    check_cmd = self.ec2_path + 'ec2-describe-instances --filter=\"tag:Name=%s\"' % \
                self.instance_name
    instances_detail = subprocess.check_output(check_cmd, shell=True)
    if instances_detail.strip() == '':
      return

    while instances_detail.find('pending') != -1:
      time.sleep(5)
      instances_detail = subprocess.check_output(check_cmd, shell=True)

    instances_detail = instances_detail.split('\n')
    instance_id = ''
    for line in instances_detail:
      if line.find('INSTANCE', 0, len('INSTANCE')) != -1:
        instance_id = line.split()[1]

      if line.find('PRIVATEIPADDRESS', 0, len('PRIVATEIPADDRESS')) != -1:
        address = line.split()
        assert instance_id != ''
        self.instances[instance_id] = (address[-1], address[-3])

  def environ(self):
    os.environ['AWS_ACCESS_KEY'] = 'AKIAIZK6BQUOPLLFGK4Q'
    os.environ['AWS_SECRET_KEY'] = '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'
    os.environ['EC2_URL'] = 'ec2.us-east-1.amazonaws.com'

    self.ec2_path = str(os.environ['EC2_HOME']) + '/bin/'

  def run(self):
    if len(self.instances) != 0:
      print 'Some instances have the same Name.'
      print 'You should terminate them and launch new instances'
      print 'You can also start them instead of launching new ones'
      return

    run_cmd = self.ec2_path + 'ec2-run-instances %s -n %d -g NYU -g Home -g VPC -t %s' \
              % (self.ami, self.num_of_instances, self.instance_type)
    result = subprocess.check_output(run_cmd, shell=True).split('\n')
    
    instance_ids = []
    for line in result:
      if line.find('INSTANCE', 0, len('INSTANCE')) != -1:
        instance_ids.append(line.split()[1])
    time.sleep(5)
    for instance_id in instance_ids:
      tag_cmd = self.ec2_path + 'ec2-create-tags %s --tag \"Name=%s\"' \
                % (instance_id, self.instance_name)
      subprocess.call(tag_cmd, shell=True)

    self._get_instances()
    self.after_launch()

  def start(self):
    if len(self.instances) == 0:
      print 'No instances are named %s.' % self.instance_name
      print 'You should launch new instances.'
      return

    for instance_id in self.instances.iterkeys():
      start_cmd = self.ec2_path + 'ec2-start-instances %s' % instance_id
      subprocess.call(start_cmd, shell=True)

    time.sleep(5)
    self._get_instances()
    self.after_launch()

  def setup(self):
    self._get_instances()
    self.after_launch()

  def stop(self):
    if len(self.instances) == 0:
      print 'No instances are named %s.' % self.instance_name
      return

    for instance_id in self.instances.iterkeys():
      stop_cmd = self.ec2_path + 'ec2-stop-instances %s' % instance_id
      subprocess.call(stop_cmd, shell=True)
    time.sleep(5)

  def terminate(self):
    if len(self.instances) == 0:
      print 'No instances are named %s.' % self.instance_name
      return

    for instance_id in self.instances.iterkeys():
      stop_cmd = self.ec2_path + 'ec2-terminate-instances %s' % instance_id
      subprocess.call(stop_cmd, shell=True)
    time.sleep(5)

  def after_launch(self):
    with open('_spartan.ini', 'w+') as fp:
      with open('_machines', 'w+') as fp2:
        fp.write('[flags]\n')
        fp.write('cluster=1\n')
        fp.write('num_workers=%d\n' % int(self.workers * (self.num_of_instances - 1)))
        fp.write('default_rpc_timeout=3600\n') 
        fp.write('worker_failed_heartbeat_threshold=3600\n')
        fp.write('heartbeat_interval=3600\n')
        fp.write('assign_mode=BY_CORE\n')
        fp.write('hosts=')

        if self.master != None:
          for instance_id, ips in self.instances.iteritems():
            if ips[1] == self.master:
              master = instance_id
              master_ip = ips[0]
              master_privateip = ips[1]
              break
        else:
          master = list(self.instances.iterkeys())[0]
          master_ip = self.instances[master][0]
          master_privateip = self.instances[master][1]

        print (master, master_ip, master_privateip)
        first = True
        threads = []
        for instance_id, ips in self.instances.iteritems():
          if master != instance_id:
            if not first:
              fp.write(',')
            first = False
            fp.write('%s:%d' % (ips[1], self.workers))
            fp2.write('%s\n' % ips[1])
            
            cmds = []
            client_cmd = 'ssh -i %s %s@%s \"sudo mount -t nfs %s:/home/ubuntu /home/ubuntu\"' \
                         % (self.perm, self.user, ips[0], master_privateip)
            cmds.append(client_cmd)
            client_cmd = 'ssh -i %s %s@%s \"sudo chmod 777 /mnt\"' \
                         % (self.perm, self.user, ips[0])
            cmds.append(client_cmd)
            thread = ClientThread(cmds)
            thread.start()
            threads.append(thread)

        for thread in threads:
          thread.join()
            #client_cmd = 'ssh -i %s %s@%s \"sudo mount -t nfs %s:/home/ubuntu /home/ubuntu\"' \
                         #% (self.perm, self.user, ips[0], master_privateip)
            #while True:
              #result = subprocess.call(client_cmd, shell=True)
              #if result == 0:
                #break
              #time.sleep(5)

            #client_cmd = 'ssh -i %s %s@%s \"sudo chmod 777 /mnt\"' \
                         #% (self.perm, self.user, ips[0])
            #while True:
              #result = subprocess.call(client_cmd, shell=True)
              #if result == 0:
                #break
              #time.sleep(5)

    while True:
      cmd = 'scp -i %s _spartan.ini %s@%s:/home/%s/.config/spartan/spartan.ini' % \
            (self.perm, self.user, master_ip, self.user)
      result = subprocess.call(cmd, shell=True)
      if result == 0:
        break
      time.sleep(5)
    while True:
      cmd = 'ssh -i %s %s@%s \"sudo chmod 777 /mnt\"' % (self.perm, self.user, master_ip)
      result = subprocess.call(cmd, shell=True)
      if result == 0:
        break
      time.sleep(5)

    while True:
      cmd = 'scp -i %s _machines %s@%s:/home/%s/machines' % \
            (self.perm, self.user, master_ip, self.user)
      result = subprocess.call(cmd, shell=True)
      if result == 0:
        break
      time.sleep(5)

    print 'Master\'s id is %s, ip address is %s' % (master, master_ip)

def main(argv):
  try:
    opts, args = getopt.getopt(argv, 'l:n:i:w:p:u:a:y:m:')
  except:
    print 'argv error %s' % str(argv)

  kargs = {}
  action = ''
  for o, a in opts:
    if o == '-l':
      action = a
    elif o == '-n':
      kargs['instance_name'] = a
    elif o == '-i':
      kargs['num_of_instances'] = int(a)
    elif o == '-w':
      kargs['workers'] = int(a)
    elif o == '-p':
      kargs['perm'] = a
    elif o == '-u':
      kargs['users'] = a
    elif o == '-a':
      kargs['ami'] = a
    elif o == '-y':
      kargs['instance_type'] = a
    elif o == '-m':
      kargs['master'] = a
  
  assert action != '' and kargs.get('instance_name', None) != None
  ec2 = Ec2Launch(**kargs)
  print action
  if action == 'LAUNCH':
    ec2.run()
  elif action == 'START':
    ec2.start()
  elif action == 'STOP':
    ec2.stop()
  elif action == 'SETUP':
    ec2.setup()
  elif action == 'TERMINATE':
    ec2.terminate()

if __name__ == '__main__':
  main(sys.argv[1:])
