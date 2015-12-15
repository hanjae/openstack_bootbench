#!/usr/bin/python

import os
import re
import threading
import time

# prefix for benchmark
test_id = "zboot_time_bench"

# num_instances
nr_instances = 4

is_same_image = True

# nova boot command
# when use different images put %d at the end of imagename
boot_cmd = "nova boot --flavor m1.small --image ubuntu%d --nic net-id=fceb1bee-5e9d-4847-9bfb-9b8e13d86b87 --security-group default --key-name dcslab_testkey"

#boot_cmd = "nova boot --flavor m1.small --block-device source=image,id=c564612a-3977-4d1c-bd4b-5c21a85a5794,dest=volume,size=10,shutdown=preserve,bootindex=0 --nic net-id=fceb1bee-5e9d-4847-9bfb-9b8e13d86b87 --security-group default --key-name dcslab_testkey"

def curr_ms():
  return int(round(time.time() * 1000))

def delete_test_vms():
  #last one is empty
  instances = os.popen("nova list | grep " + test_id).read().split("\n")[:-1]

  instance_names = []
  for str in instances:
    instance_names.append(re.search(test_id + "[\w-]*", str).group())
  for name in instance_names:
    print("delete vm %s"%name)
    os.popen("nova delete %s"%name)
  time.sleep(5)

# delete instances before test
delete_test_vms()

# launch instances
if is_same_image:
  if nr_instances > 1:
    boot_cmd += " --num-instances=" + str(nr_instances)
  boot_cmd += " " + test_id
  print "Create instances with command : " + boot_cmd
  os.popen(boot_cmd)
else:
  for i in range(nr_instances):
    tmp_cmd = boot_cmd%i
    tmp_cmd += " " + test_id + i
    os.popen(tmp_cmd)
    print "Create instances with command : " + tmp_cmd
vm_start_time = curr_ms()

#last one is empty
instances = os.popen("nova list | grep " + test_id).read().split("\n")[:-1]

instance_names = []
instance_ips = []
for str in instances:
  instance_names.append(re.search(test_id + "[\w-]*", str).group())

class instanceTimerThread(threading.Thread):
  def __init__(self, thread_id, name, start_time):
    threading.Thread.__init__(self)
    self.thread_id = thread_id
    self.name = name
    self.start_time = start_time
    self.ip = None
    print "thread %d init"%thread_id
  def run(self):
    # find ip
    while self.ip is None:
      status_str = os.popen("nova list | grep " + self.name).read()
      ip_search_result = re.search("(?:[0-9]{1,3}\.){3}[0-9]{1,3}", status_str)
      if ip_search_result != None:
        self.ip = ip_search_result.group()
      print "ip not found"
      time.sleep(5)

    print "ip found " + self.ip

    time.sleep(10)

    # try ssh
    while True:
      ssh_result_str = os.popen("ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no -i dcslab_testkey ubuntu@%s echo ok"%self.ip).read()[0:2]
      if ssh_result_str == "ok":
        instance_times[self.thread_id] = curr_ms() - self.start_time
        break
      time.sleep(1)

instance_times = [None] * len(instance_names)
threads = []
for i in range(len(instance_names)):
  theThread = instanceTimerThread(i, instance_names[i], vm_start_time)
  threads.append(theThread)
for theThread in threads:
  theThread.start()
for theThread in threads:
  theThread.join()

for i in range(len(instance_times)):
  print instance_times[i] / 1000.00

# cleanup test vms
delete_test_vms()
