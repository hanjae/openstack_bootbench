#!/usr/bin/python

import os
import re
import threading
import time

# prefix for benchmark
test_id = "zboot_time_bench"

# num_instances
nr_instances = 40

# nova boot command
boot_cmd = "nova boot --flavor m1.small --image ubuntu --nic net-id=fde5fdd0-af64-440c-8580-433c16912f56 --security-group default --key-name dcslab_testkey"


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
if nr_instances > 1:
        boot_cmd += " --num-instances=" + str(nr_instances)
boot_cmd += " " + test_id
print "Create instances with command : " + boot_cmd
os.popen(boot_cmd)
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

                # try ssh
                while True:
                        ssh_result_str = os.popen("ssh -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=no ubuntu@%s echo ok"%self.ip).read()[0:2]
                        if ssh_result_str == "ok":
                                instance_times[self.thread_id] = curr_ms() - self.start_time
                                break
			time.sleep(0.5)

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
        print instance_times[i]

# cleanup test vms
delete_test_vms()
