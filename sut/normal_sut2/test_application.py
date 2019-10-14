from openmtc_app.onem2m import XAE
from openmtc_onem2m.model import Container
import gevent
import uuid
import os
import signal
import requests

class TestApplication(XAE):

    def __init__(self, *args, **kw):
        super(TestApplication, self).__init__(*args, **kw)

        self.orch_path = 'onem2m/EDSOrch/edsorch/'
        self.sensor_temp_path = 'onem2m/TemperatureSensor/'

        self.requests_ID = {}
        self.sensors = {}
        self.app_ID = "testapplication"
        self.requests = {}

        self.app_name = "TestApplication"
        self.ems = os.environ["ET_EMS_LSBEATS_HOST"]
        self.hostport = 'http://' + self.ems + ":8181"

    def __gen_ID(self):
        return uuid.uuid4().hex[:12] 

    def _on_register(self):

        # subscribe to the EDS orch response
        response_path = self.orch_path + 'response'
        self.add_container_subscription(response_path, self.handle_orch_response)

        # subscribe to temperature sensor response
        response_path = self.sensor_temp_path + 'response'
        self.add_container_subscription(response_path, self.handle_temp_response)

        gevent.sleep(0)
        gevent.spawn_later(4, self.send_requests)

        self.run_forever()

    def _on_shutdown(self):
        # deregister the application - 5
        request_ID = str('deregister_' + self.__gen_ID())
        request = [{'deregister': {'application': {'app_ID': self.app_ID, 'request_ID': request_ID}}}]
        request_path = self.orch_path + 'request'
        self.requests['deregister'] = request_ID
        self.push_content(request_path, request)

    def send_requests(self):
        # register the application - 0
        # append the request to requests
        request_ID = str('app_' + self.__gen_ID()) 
        request = [{'register': {'application': {'app_ID': self.app_ID, 'request_ID': request_ID}}}]
        request_path = self.orch_path + 'request'
        self.push_content(request_path, request)
        self.requests['app'] = request_ID
        self.logger.info('sent request to register application')
        gevent.sleep(2)

        # register the sensor1 - 1
        request_ID = str('sensor_temp_' + self.__gen_ID())
        request = [{'register': {'sensor': {'app_ID': self.app_ID, 'request_ID': request_ID, 'sensor_type': 'temperature'}}}]
        self.push_content(request_path, request)
        self.requests['sensor1'] = request_ID
        self.logger.info('sent request to register sensor1')
        gevent.sleep(2)
        
        # register the sensor2 - 2
        request_ID = str('sensor_temp_' + self.__gen_ID())
        request = [{'register': {'sensor': {'app_ID': self.app_ID, 'request_ID': request_ID, 'sensor_type': 'temperature'}}}]
        self.push_content(request_path, request)
        self.requests['sensor2'] = request_ID
        self.logger.info('sent request to register sensor2')
        gevent.sleep(2)

        # switch on the temperature sensor1 - 3
        request_ID = str('modify_' + self.__gen_ID())
        sensor_name = self.requests_ID[self.requests['sensor1']]['conf']['name']
        self.requests['sensor1_mod'] = request_ID
        request = [{'modify': {'app_ID': self.app_ID, 'request_ID': request_ID, 'name': sensor_name, 'conf': {'onoff': 'ON', 'period': 3}}}]
        request_path = self.sensor_temp_path + 'request'
        self.push_content(request_path, request)
        
        # switch on the temperature sensor2 - 4
        request_ID = str('modify_' + self.__gen_ID())
        sensor_name = self.requests_ID[self.requests['sensor2']]['conf']['name']
        self.requests['sensor2_mod'] = request_ID
        request = [{'modify': {'app_ID': self.app_ID, 'request_ID': request_ID, 'name': sensor_name, 'conf': {'onoff': 'ON', 'period': 3}}}]
        request_path = self.sensor_temp_path + 'request'
        self.push_content(request_path, request)

        # wait a little and hope the system be established
        # if established we will connect the sensor application
        self.logger.info('waiting for system to be established...')
        gevent.sleep(5)

        sensor_request = self.requests['sensor1']
        self.add_container_subscription(self.requests_ID[sensor_request]['conf']['path'], self.handle_temperature_sensor)

        sensor_request = self.requests['sensor2']
        self.add_container_subscription(self.requests_ID[sensor_request]['conf']['path'], self.handle_temperature_sensor2)

        #stop the tjob after 2 minutes
        gevent.sleep(0)
        gevent.spawn_later(120, self.app_shutdown)

    def app_shutdown(self):
        json_message = {'ourmessage': 'STOP_TEST'}
        r = requests.post(self.hostport, json=json_message)
        os.kill(os.getpid(), signal.SIGTERM)

    def handle_temperature_sensor(self, cnt, con):
        # actual logic is placed here
        self.logger.info(':sensor1:'+ con)
        self.logger.info(cnt)
        json_message = {'appname': 'test1', 'type': 'sensor', 'id': 1, 'value': int(float(con)) }
        r = requests.post(self.hostport, json=json_message)

    def handle_temperature_sensor2(self, cnt, con):
        # actual logic is placed here
        self.logger.info(':sensor2:'+ con)
        self.logger.info(cnt)
        json_message = {'appname': 'test1', 'type': 'sensor', 'id': 2, 'value': int(float(con)) }
        r = requests.post(self.hostport, json=json_message)

    def handle_orch_response(self, cnt, con):
        reply = con
        # check if reply is for this application
        if reply.get('app_ID') == self.app_ID:
            # check the result in the reply
            if reply.get('result') == 'SUCCESS':
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
        if reply.get('app_ID') == self.app_ID:
            if reply.get('result') == 'SUCCESS':
                request_ID = reply['request_ID']
                self.logger.info(request_ID + ' was a success')
            else:
                request_ID = reply['request_ID']
                error = reply['error_string']
                self.logger.info(request_ID + ' did not succeed')
        else:
            self.logger.info('received message not for this app')



