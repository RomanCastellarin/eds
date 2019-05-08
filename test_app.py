import requests
import time
import sys
import os
from threading import Timer
import json

print "start of the script"

def terminate():
    print "STOP TEST"

t = Timer(60.0, terminate)
t.start()

ems = os.environ["ET_EMS_LSBEATS_HOST"]
headers = {'content-type': 'text/plain'}

stampers = "when e.tag(#testresult) do #websocket\n when e.tag(#terminate) do #websocket".encode()

moms = "stream bool result := e.strmatch(message,\"STOP_TEST\")\n trigger result do emit result on #terminate".encode()

url = "http://" + ems + ":8888/stamper/tag0.1"
response = requests.post(url, headers=headers, data=stampers)
#response = requests.post(url, data=stampers)
print(response.content)

url = "http://" + ems + ":8888/MonitoringMachine/signals0.1"
response = requests.post(url, headers=headers, data=moms)
# # response = requests.post(url, data=moms)
print(response.content)

print "after sending requests"

from websocket import create_connection
url = "ws://" + ems + ":3232"
ws = create_connection(url)
i = 0

print "entering loop"

while True:
  result = ws.recv()
  result = json.loads(result)
  i += 1
#  if i==100:
#    print "STOP TEST"
#  if "#websocket" in result["channels"]:
#    print "websocket message found"
  if "#terminate" in result["channels"]:
    print result
    print "test result found"
    break

# print "STOP TEST"
