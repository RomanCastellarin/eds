import requests
import time
import sys
import os
from threading import Timer
import json
from websocket import create_connection
import sys
import unittest
import xmlrunner

class AssertVariables():
  datavalues = {'test1':{'sensor1': None, 'sensor2': None}}
variables = AssertVariables()

class TestSensorBehaviour(unittest.TestCase):
  def test_sensor_range(self):
    for value in variables.datavalues.values():
        if value is None:
            continue
        in_range = 10 <= value and value <= 30
        self.assertTrue(in_range, "Sensor values out of range")

sensorBehaviourSuite = unittest.TestLoader().loadTestsFromTestCase(TestSensorBehaviour)

class MonitoringTest():
  def __init__(self):
    self.condition = True
    self.ems = os.environ["ET_EMS_LSBEATS_HOST"]
    self.headers = {'content-type': 'text/plain'}
    self.stampers = ""
    self.monMachines = ""
    
    print("before sending requests")

    # get the stampers from file
    with open(os.environ['PWD'] + "/" + "stampers.txt") as f:
      self.stampers = f.read()

    # send stampers to EMS
    url = "http://" + self.ems + ":8888/stamper/tag0.1"
    response = requests.post(url, headers=self.headers, data=self.stampers)
    print(response.content)

    # get the monitoring machines from the file
    with open(os.environ['PWD'] + "/" + "monitoring_machines.txt") as f:
      self.monMachines = f.read()

    # send the monitoring machines to EMS
    url = "http://" + self.ems + ":8888/MonitoringMachine/signals0.1"
    response = requests.post(url, headers=self.headers, data=self.monMachines)
    print(response.content)

    print("after sending requests")
    print("entering loop function")
    self.start_test()
    print("exiting loop function")

  def start_test(self):
    url = "ws://" + self.ems + ":3232"
    ws = create_connection(url)
    print "entering loop"
    self.condition = True
    while(self.condition):
      result = ws.recv()
      result = json.loads(result)
      print result
      if "#terminate" in result["channels"]:
        print result
        print "test result found"
        self.condition = False
        break

      if "#test1sensor" in result["channels"]:
        print result
        sensor = result['id']
        variables.datavalues['test1']['sensor' + str(sensor)] = result['value']
        xmlrunner.XMLTestRunner(verbosity=2, output='/tmp/test-reports').run(sensorBehaviourSuite)
        print "sensor has triggered"

if __name__ == "__main__":
  print("Starting the test")
  edstest = MonitoringTest()
  print("Ending the test")

