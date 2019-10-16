from openmtc_app.onem2m import XAE
from openmtc_onem2m.model import Container
import gevent
import uuid
import os
import signal
import requests
from functools import partial

class TestApplication(XAE):

    def __init__(self, *args, **kw):
        super(TestApplication, self).__init__(*args, **kw)

        self.orch_path = 'onem2m/EDSOrch/edsorch/'
        self.sensor_temp_path = 'onem2m/TemperatureSensor/'
        self.actuator_simple_path = 'onem2m/SimpleActuator/'

        self.requests_ID = {}
        self.sensors = {}
        self.actuators = {}
        self.app_ID = "testapplication"
        self.requests = []
        self.setup = False

        self.app_name = "TestApplication"
        self.ems = os.environ["ET_EMS_LSBEATS_HOST"]
        self.hostport = 'http://' + self.ems + ":8181"


    def _on_register(self):

        # subscribe to the EDS orch response
        response_path = self.orch_path + 'response'
        self.add_container_subscription(response_path, self.handle_orch_response)

        # subscribe to temperature sensor response
        response_path = self.sensor_temp_path + 'response'
        self.add_container_subscription(response_path, self.handle_temp_response)

        # subscribe to the simple actuator response
        response_path = self.actuator_simple_path + 'response'
        self.add_container_subscription(response_path, self.handle_simple_response)

        gevent.sleep(0)
        gevent.spawn_later(5,self.send_requests)

        self.run_forever()

    def _on_shutdown(self):
        # deregister the application - 4
        request_ID = (uuid.uuid4().hex)[:12]
        request_ID = str('deregister_'+ request_ID)
        request = [{'deregister':{'application':{'app_ID':self.app_ID, 'request_ID':
            request_ID}}}]
        request_path = self.orch_path + 'request'
        self.requests.append(request_ID)
        self.push_content(request_path, request)

    def send_requests(self):
        # register the application - 0
        request_ID = (uuid.uuid4().hex)[:12]
        # append the request to requests
        request_ID = str('app_' + request_ID)
        request = [{'register':{'application':{'app_ID':self.app_ID,
            'request_ID':request_ID}}}]
        request_path = self.orch_path + 'request'
        self.push_content(request_path, request)
        self.requests.append(request_ID)
        self.logger.info('sent request to register application')
        gevent.sleep(3)

        # register the sensor - 1
        request_ID = (uuid.uuid4().hex)[:12]
        request_ID = str('sensor_temp_' + request_ID)
        request = [{'register':{'sensor':{'app_ID':self.app_ID,
            'request_ID':request_ID, 'sensor_type':'temperature'}}}]
        self.push_content(request_path, request)
        self.requests.append(request_ID)
        self.logger.info('sent request to register sensor')
        gevent.sleep(3)

        # register the actuator - 2
        request_ID = (uuid.uuid4().hex)[:12]
        request_ID = str('actuator_simple_' + request_ID)
        request = [{'register':{'actuator':{'app_ID':self.app_ID,
            'request_ID':request_ID, 'actuator_type':'simple'}}}]
        self.push_content(request_path, request)
        self.requests.append(request_ID)
        self.logger.info('sent request to register actuator')
        gevent.sleep(3)

        # switch on the temperature sensor - 3
        request_ID = (uuid.uuid4().hex)[:12]
        request_ID = str('modify_' + request_ID)
        sensor_name = self.requests_ID[self.requests[1]]['conf']['name']
        self.requests.append(request_ID)
        request = [{'modify':{'app_ID':self.app_ID, 'request_ID':
            request_ID, 'name' : sensor_name, 'conf':{'onoff':'ON', 'period':5}}}]
        request_path = self.sensor_temp_path + 'request'
        self.push_content(request_path, request)

        request_ID = (uuid.uuid4().hex)[:12]
        request_ID = str('modify_' + request_ID)
        actuator_name = self.requests_ID[self.requests[2]]['conf']['name']
        self.requests.append(request_ID)
        request = [{'modify':{'app_ID':self.app_ID, 'request_ID':
            request_ID, 'name' : actuator_name, 'conf':{'delay':3}}}]
        request_path = self.actuator_simple_path + 'request'
        self.push_content(request_path, request)

        # run a polling loop to check if the system is established
        # if established we will connect the sensor application
        self.logger.info('waiting for system to be established...')
        gevent.sleep(5)
        sensor_request = self.requests[1]
        self.add_container_subscription(self.requests_ID[sensor_request]['conf']['path'],
                partial(self.handle_temperature_sensor, id=517))

        actuator_request = self.requests[2]
        self.add_container_subscription(self.requests_ID[actuator_request]['conf']['out_path'],
               self.handle_actuator_out)

        #stop the tjob after 2 minutes
        gevent.sleep(0)
        gevent.spawn_later(120, self.app_shutdown)

    def app_shutdown(self):
        json_message = {'ourmessage':'STOP_TEST'}
        r = requests.post(self.hostport, json=json_message)
        os.kill(os.getpid(), signal.SIGTERM)

    def handle_actuator_out(self, cnt, con):
        self.logger.info(':actuator:' + con)
        self.logger.info(cnt)
        json_message = {'appname':'test1', 'type':'actuator', 'svalue':{'actual':1, 'threshold':20}}
        r = requests.post(self.hostport, json=json_message)

    def handle_temperature_sensor(self, cnt, con, id=0):
        # actual logic is placed here
        actuator_request = self.requests[2]
        self.logger.info('handling temp sensor %d' % id)
        self.logger.info(':sensor:'+ con)
        self.logger.info(cnt)
        json_message = {'appname':'test1', 'type':'sensor', 'svalue':{'actual':int(float(con)), 'threshold':20}}
        r = requests.post(self.hostport, json=json_message)
        if float(con) > 20:
            self.push_content(self.requests_ID[actuator_request]['conf']['in_path'],
                    con)
            json_message = {'appname':'test1', 'type':'logic', 'svalue':{'actual':1, 'threshold':20}}
            r = requests.post(self.hostport, json=json_message)

    def handle_orch_response(self, cnt, con):
        reply = con
        # check if reply is for this application
        if 'app_ID' in reply and reply['app_ID'] == self.app_ID:
            # check the result in the reply
            if 'result' in reply and reply['result'] == 'SUCCESS':
                # the reply contains, everything went well
                request_ID = reply['request_ID']
                self.requests_ID[request_ID] = reply
                self.logger.info(request_ID + ' was a success')

            else:
                request_ID = reply['request_ID']
                error = reply['error_string']
                self.logger.info(request_ID + ' did not succeed')
                self.logger.info('error ' + error_string)

        else:
            self.logger.info('received message not for this app')

    def handle_temp_response(self, cnt, con):
        reply = con
        if 'app_ID' in reply and reply['app_ID'] == self.app_ID:
            if 'result' in reply and reply['result'] == 'SUCCESS':
                request_ID = reply['request_ID']
                self.logger.info(request_ID + ' was a success')

            else:
                request_ID = reply['request_ID']
                error = reply['error_string']
                self.logger.info(request_ID + ' did not succeed')
        else:
            self.logger.info('received message not for this app')

    def handle_simple_response(self, cnt, con):
        reply = con
        if 'app_ID' in reply and reply['app_ID'] == self.app_ID:
            if 'result' in reply and reply['result'] == 'SUCCESS':
                request_ID = reply['request_ID']
                self.logger.info(request_ID + ' was a success')

            else:
                request_ID = reply['request_ID']
                error = reply['error_string']
                self.logger.info(request_ID + ' did not succeed')
        else:
            self.logger.info('received message not for this app')


