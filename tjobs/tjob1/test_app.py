import requests
import time
import sys
import os
from threading import Timer
import json
from websocket import create_connection
import sys

class MonitoringTest():
  def __init__(self):
    self.condition = True
    self.ems = os.environ["ET_EMS_LSBEATS_HOST"]
    self.headers = {'content-type': 'text/plain'}
    self.stampers = ""
    self.monMachines = ""
    try:
      self.duration = os.environ['EDS_TEST_DURATION']
    except KeyError:
      self.duration = 180
    # self.t = Timer(self.duration, self.terminate)
    print("before sending requests")

    # get the stampers from file
    with open(os.environ['PWD'] + "/" + "stampers.txt") as f:
      self.stampers = f.read()
      f.close()

    # send stampers to EMS
    url = "http://" + self.ems + ":8888/stamper/tag0.1"
    response = requests.post(url, headers=self.headers, data=self.stampers)
    print(response.content)

    # get the monitoring machines from the file
    with open(os.environ['PWD'] + "/" + "monitoring_machines.txt") as f:
      self.monMachines = f.read()
      f.close()

    # send the monitoring machines to EMS
    url = "http://" + self.ems + ":8888/MonitoringMachine/signals0.1"
    response = requests.post(url, headers=self.headers, data=self.monMachines)
    print(response.content)

    print("after sending requests")
    print("starting timer")
    # self.t.start()
    print("entering loop function")
    self.start_test()
    print("exiting loop function")

  def terminate(self):
    self.condition = False
    print("STOP_TEST")

  def start_test(self):
    url = "ws://" + self.ems + ":3232"
    ws = create_connection(url)
    print "entering loop"
    while(True):
      result = ws.recv()
      result = json.loads(result)
      if "#terminate" in result["channels"]:
        print result
        print "test result found"
        self.condition = False
        break

if __name__ == "__main__":
  print("Starting the test")
  edstest = MonitoringTest()
  print("Ending the test")

