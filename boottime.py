#!/usr/bin/python

import os
import re
import threading
import time

# prefix for benchmark
test_id = "zboot_time_bench"

# num_instances
nr_instances = 20

is_same_image = False
is_volume = True

# nova boot command
# when use different images put %d at the end of imagename
boot_cmd = "nova boot --flavor m1.small --image ubuntu%d --nic net-id=fceb1bee-5e9d-4847-9bfb-9b8e13d86b87 --security-group default --key-name dcslab_testkey"
volume_boot_cmd = "nova boot --flavor m1.small --block-device source=image,id=%s,dest=volume,size=10,shutdown=preserve,bootindex=0 --nic net-id=fceb1bee-5e9d-4847-9bfb-9b8e13d86b87 --security-group default --key-name dcslab_testkey"

volume_ids = [
"607e11b3-6962-4e3c-aa82-94fac1fc423a",
"1ee19ca6-1e1c-4e86-8e4e-4906f901f333",
"f1ec96ce-f638-46b3-b8f9-132f45cd2019",
"65e4860f-9f18-4888-922e-c95aa615bc80",
"c4f73188-3aa9-417d-a9cb-00cf87ab4a2f",
"3fb395f6-3ed2-4856-a7e3-c961f4cccfa4",
"351f330a-d3f8-4a25-a5c8-ebab28f45172",
"0c483779-5c2a-4851-9a7a-cd818f8e4bdd",
"7d622b70-eeed-4e04-84b7-3e1f0b1589f5",
"055b6ea0-12b8-4b29-b5d7-277f28511deb",
"bcc478d3-3ce5-4a36-bc8a-61a75c28d611",
"7cc06c23-b4d3-4791-9d92-3886f5d673f1",
"b9683a7f-0618-4272-a8e2-b8985e905bea",
"71931f3c-a381-4251-80ed-389da87ca548",
"780d9597-8883-4b0b-a394-e0d3f0441ded",
"28e04288-d7e7-419f-a72d-fdb01ca6c19f",
"fdfe082e-fa15-49c5-a0bf-c8fe66808afe",
"a9291d36-c915-4b03-a643-2615d4f4e060",
"23acf85f-807b-4a55-80b6-1e16fd5d42c3",
"3ac8ebb7-898a-4bc1-8326-001c55aa0c59"]

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

def delete_test_volumes():
  os.popen("cinder delete $(cinder list | awk '!/ID/ {print $2}')")
  time.sleep(5)

# delete instances before test
delete_test_vms()

# launch instances
if is_same_image:
  if is_volume:
    tmp_cmd = volume_boot_cmd % volume_ids[0]
  else:
    tmp_cmd = boot_cmd % 0
  if nr_instances > 1:
    tmp_cmd += " --num-instances=" + str(nr_instances)
  tmp_cmd += " " + test_id
  print "Create instances with command : " + tmp_cmd
  os.popen(tmp_cmd)
else:
  for i in range(nr_instances):
    if is_volume:
      tmp_cmd = volume_boot_cmd % volume_ids[i]
    else:
      tmp_cmd = boot_cmd % i
    tmp_cmd += " " + test_id + str(i)
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
        os.popen("ssh-keygen -f /root/.ssh/known_hosts -R %s"%self.ip).read()
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

if is_volume:
  delete_test_volumes()
