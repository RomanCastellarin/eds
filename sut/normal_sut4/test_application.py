from openmtc_app.onem2m import XAE
from openmtc_onem2m.model import Container
import gevent
import uuid
import os
import signal
import requests
import json
from functools import partial

class TestApplication(XAE):

    def __init__(self, *args, **kw):
        super(TestApplication, self).__init__(*args, **kw)

        self.orch_path = 'onem2m/EDSOrch/edsorch/'
        self.sensor_temp_path = 'onem2m/TemperatureSensor/'
        self.actuator_simple_path = 'onem2m/SimpleActuator/'

        self.NUM_PAIRS = 3
        self.MAX_ROOMS = 10
        self.next_pair_index = 0
        self.stored_reply = {}
        self.sensor_requests = [None] * self.MAX_ROOMS
        self.actuator_requests = [None] * self.MAX_ROOMS
        self.app_ID = "testapplication"

        self.app_name = "TestApplication"
        self.ems = os.environ["ET_EMS_LSBEATS_HOST"]
        self.hostport = 'http://' + self.ems + ":8181"

        self.status = {
            'current' : 'off',
            'request' : None
        }

    def __gen_ID(self):
        return uuid.uuid4().hex[:12]

    def __publish(self, message):
        print json.dumps(message)

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

        self.status['current'] = 'started'
        gevent.sleep(0)
        gevent.spawn_later(2,self.send_requests)

        self.run_forever()

    def _on_shutdown(self):
        # deregister the application - 4
        request_ID = str('deregister_'+ self.__gen_ID())
        request = [{'deregister': {'application': {'app_ID': self.app_ID, 'request_ID': request_ID}}}]
        request_path = self.orch_path + 'request'
        self.push_content(request_path, request)

    def send_requests(self):
        
        # World creation

        # Register the application
        request_ID = str('app_' + self.__gen_ID())
        request = [{'register': {'application': {'app_ID': self.app_ID, 'request_ID': request_ID}}}]
        request_path = self.orch_path + 'request'
        self.push_content(request_path, request)
        self.logger.info('sent request to register application')

        #while( self.status['current'] == 'started' )
        gevent.sleep(3)

        self.logger.info('no pairs %d' % self.NUM_PAIRS) 
        # register NUM_PAIRS pairs of temp sensors - actuators
        for _ in range(self.NUM_PAIRS):
            self.logger.info('new pair')
            index = self.next_pair_index % self.MAX_ROOMS
            # sensor
            request_ID = str('sensor_temp_' + self.__gen_ID())
            request = [{'register': {'sensor': {'app_ID': self.app_ID, 'request_ID': request_ID, 'sensor_type': 'temperature'}}}]
            self.push_content(request_path, request)
            self.sensor_requests[index] = request_ID
            self.logger.info('sent request to register sensor')
            gevent.sleep(0.1)
            # actuator
            request_ID = str('actuator_simple_' + self.__gen_ID())
            request = [{'register': {'actuator': {'app_ID': self.app_ID, 'request_ID': request_ID, 'actuator_type': 'simple'}}}]
            self.push_content(request_path, request)
            self.actuator_requests[index] = request_ID
            self.logger.info('sent request to register actuator')
            gevent.sleep(0.1)
            # increment pair counter
            self.next_pair_index += 1

        #while( faltan contestaciones) wait

        gevent.sleep(3)


        # Set up pairs
        for pair_index in range(self.next_pair_index-self.NUM_PAIRS, self.next_pair_index):
            index = pair_index % self.MAX_ROOMS
            # switch on sensor
            request_ID = str('modify_' + self.__gen_ID())
            sensor_name = self.stored_reply[self.sensor_requests[index]]['conf']['name']
            request = [{'modify': {'app_ID': self.app_ID, 'request_ID': request_ID, 'name': sensor_name, 'conf': {'onoff':'ON', 'period':5, 'min':10, 'max':30}}}]
            request_path = self.sensor_temp_path + 'request'
            self.push_content(request_path, request)
            # config actuator
            request_ID = str('modify_' + self.__gen_ID())
            actuator_name = self.stored_reply[self.actuator_requests[index]]['conf']['name']
            request = [{'modify':{'app_ID':self.app_ID, 'request_ID': request_ID, 'name' : actuator_name, 'conf':{'delay':3}}}]
            request_path = self.actuator_simple_path + 'request'
            self.push_content(request_path, request)

        # wait 10s and hope the system be established
        # if established we will connect the sensor application
        self.logger.info('waiting for system to be established...')
        gevent.sleep(10)

        for pair_index in range(self.next_pair_index-self.NUM_PAIRS, self.next_pair_index):
            index = pair_index % self.MAX_ROOMS
            sensor_request = self.sensor_requests[index] 
            self.add_container_subscription(self.stored_reply[sensor_request]['conf']['path'],
                partial(self.handle_temperature_sensor, index=pair_index ))
            actuator_request = self.actuator_requests[index]
            self.add_container_subscription(self.stored_reply[actuator_request]['conf']['out_path'],
               partial(self.handle_actuator_out, index=pair_index))

        #stop the tjob after 1 minute
        gevent.sleep(0)
        gevent.spawn_later(60, self.app_shutdown)

    def app_shutdown(self):
        json_message = {'ourmessage':'STOP_TEST'}
        #self.__publish(json_message)
        r = requests.post(self.hostport, json=json_message)
        os.kill(os.getpid(), signal.SIGTERM)

    def handle_actuator_out(self, cnt, con, index):
        self.logger.info('handling actuator out n. %d' % index)
        self.logger.info(':actuator:' + con)
        self.logger.info(cnt)
        json_message = {'appname':'test1', 'type':'actuator', 'id':index }
        r = requests.post(self.hostport, json=json_message)

    def handle_temperature_sensor(self, cnt, con, index):
        # actual logic is placed here
        actuator_request = self.actuator_requests[index % self.MAX_ROOMS] 
        self.logger.info('handling temp sensor n. %d' % index)
        self.logger.info(':sensor:'+ con)
        self.logger.info(cnt)
        json_message = {'appname':'test1', 'type':'sensor', 'id':index, 'svalue':{'actual':int(float(con)), 'threshold':20}}
        r = requests.post(self.hostport, json=json_message)
        if int(float(con)) > 20:
            self.push_content(self.stored_reply[actuator_request]['conf']['in_path'], con)
            json_message = {'appname':'test1', 'type':'logic', 'id':index} 
            r = requests.post(self.hostport, json=json_message)

    def handle_orch_response(self, cnt, con):
        reply = con
        self.logger.info('orch handler')
        #self.logger.info(str(reply))
        # check if reply is for this application
        if reply.get('app_ID') == self.app_ID:
            # check the result in the reply
            if reply.get('result') == 'SUCCESS':
                # the reply contains, everything went well
                request_ID = reply['request_ID']
                self.stored_reply[request_ID] = reply
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
        self.logger.info('sensor handler')
        self.logger.info(str(reply))
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
        self.logger.info('actuator handler')
        self.logger.info(str(reply))
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


