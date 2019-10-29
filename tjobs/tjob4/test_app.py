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
  datavalues = {'test1':{
                    'currentid': None,
                    'sensor':{},
                    'actuator':{}
                }}
variables = AssertVariables()

class TestSensorBehaviour(unittest.TestCase):
  def test_sensor_trigger_time(self):
    sensor_id = variables.datavalues['test1']['currentid']
    sensor = variables.datavalues['test1']['sensor'][sensor_id]
    sensor_trigger_time = time.time()
    trigger_time = sensor_trigger_time - sensor['lasttriggertime']
    time_behavior = trigger_time <= 6 # 1 additional second to the expected time between signals 
    self.assertTrue(time_behavior, "Sensor trigger beyond expected interval")
    time_behavior = trigger_time >= 4 # 1 second less to the expected time between signals 
    self.assertTrue(time_behavior, "Sensor trigger earlier than expected")
    
class TestActuatorSignal(unittest.TestCase):
  def test_actuator_signal(self):
    actuator_id = variables.datavalues['test1']['currentid']
    actuator = variables.datavalues['test1']['actuator'][actuator_id]
    self.assertIsNone(actuator['lastsignaled'], "Actuator %d was not triggered" % actuator_id)


class TestActuatorTrigger(unittest.TestCase):
  def test_actuator_trigger(self):
    actuator_id = variables.datavalues['test1']['currentid']
    actuator = variables.datavalues['test1']['actuator'][actuator_id]
    #print 'testing if pair %d should have triggered %s' % (actuator_id, actuator['lastsignaled'])
    self.assertIsNotNone(actuator['lastsignaled'], "Actuator %d should not have triggered" % actuator_id)
    trigger_time = time.time() - actuator['lastsignaled']
    time_behavior = trigger_time <= 4 # 1 additional second to the expected time between signals 
    self.assertTrue(time_behavior, "Sensor trigger beyond expected interval")
    time_behavior = trigger_time >= 2 # 1 second less to the expected time between signals 
    self.assertTrue(time_behavior, "Sensor trigger earlier than expected")

sensorBehaviourSuite = unittest.TestLoader().loadTestsFromTestCase(TestSensorBehaviour)
actuatorTriggerSuite = unittest.TestLoader().loadTestsFromTestCase(TestActuatorTrigger)
actuatorSignalSuite = unittest.TestLoader().loadTestsFromTestCase(TestActuatorSignal)

class MonitoringTest():
  def __init__(self):

    self.NUM_PAIRS = 10

    for pair_id in range(self.NUM_PAIRS):
        variables.datavalues['test1']['sensor'][pair_id] = {
                                                   'lasttriggertime': 0,
                                                    'firstrun': True
                                                }
        variables.datavalues['test1']['actuator'][pair_id] = {
                                                'trigger': False,
                                                'lastsignaled': None,
                                                } 

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
    print("starting timer")
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
        #print result
        print "test result found"
        self.condition = False
        break

      if "#test1sensor" in result["channels"]:
        #print result
        sensor_id = int(result["value"])
        variables.datavalues['test1']['currentid'] = sensor_id
        if variables.datavalues['test1']['sensor'][sensor_id]['firstrun']:
          variables.datavalues['test1']['sensor'][sensor_id]['lasttriggertime'] = time.time()
          variables.datavalues['test1']['sensor'][sensor_id]['firstrun'] = False
          continue
        xmlrunner.XMLTestRunner(verbosity=0, output='/tmp/test-reports').run(sensorBehaviourSuite)
        variables.datavalues['test1']['sensor'][sensor_id]['lasttriggertime'] = time.time()
        # check it no longer needs signal
        xmlrunner.XMLTestRunner(verbosity=0, output='/tmp/test-reports').run(actuatorSignalSuite)
        print "sensor has triggered"

      if "#test1actuator" in result["channels"]:
        #print result
        actuator_id = int(result["value"])
        variables.datavalues['test1']['currentid'] = actuator_id
        # check time is around 3s
        xmlrunner.XMLTestRunner(verbosity=0, output='/tmp/test-reports').run(actuatorTriggerSuite)
        variables.datavalues['test1']['actuator'][actuator_id]['lastsignaled'] = None
        print "actuator has triggered"

      if "#test1logic" in result["channels"]:
        #print result
        # this is tested in sensor1trigger
        print "logic has triggered"

      if "#test1sensortrigger" in result["channels"]:
        #print result
        actuator_id = int(result["myid"])
        variables.datavalues['test1']['actuator'][actuator_id]['lastsignaled'] = time.time()
        print "sensor has to trigger actuator %d" % actuator_id

    return True

if __name__ == "__main__":
  print("Starting the test")
  edstest = MonitoringTest()
  print("Ending the test")

