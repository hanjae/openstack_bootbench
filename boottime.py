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

volume_ids = ["69220507-409a-456e-8aa7-601e54bf74fd", "b18f899a-07ad-42d3-8a39-6401cd3e41c1", "c54a09fe-2f99-4a9c-9ef9-2e58e59dc157", "e97d3a43-482a-4927-ae6c-53e23fb95cd3", "fbe40ec7-5506-49d8-b4b6-49ae0a843a29", "1d48a3bd-a960-4885-8fee-b25ac53c47d1", "8b84bc72-4fa9-4a0d-a807-05d8e70ebc02", "89a7170a-11e4-4384-92ee-f07fd310cd78", "9044565b-308c-4435-a756-feca87a65dd0", "2e4c13c5-d0aa-4ab0-91bf-b8d1c462a48a", "728d01fe-e46f-4a25-bde7-c4f5ccaee995", "45f02fff-35bd-4225-93ff-d0e1273d0700", "c63f42d0-a76d-492f-a49a-b106ef2fffcb", "75e620c2-25ca-475c-8b0f-88f7bb1811c8", "a47fc61e-aac8-460b-a177-234285a78cc3", "d2d00c4e-3e37-4c29-a7f8-69e3fdd8a296", "0c558189-63f6-4b7d-a650-c95b1318abe3", "2431fda6-c1f0-453c-aaeb-26e5a054b163", "523817c2-ed61-4251-816a-85d49b9be5f5", "6a1fd029-1876-4243-9117-c99a7faf1416"]


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
  boot_cmd += " " + test_id
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
