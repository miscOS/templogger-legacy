#!/usr/bin/env python
"""
Requirements:
Python Version >= 3.6
PyUSB
paho-mqtt
"""
import json, logging, os, time
import paho.mqtt.client as mqtt
from modules import device
from modules import data

# Configuration
try:
	config_file = os.getcwd() + '/config/config.json'
	with open(config_file,'r') as f:
		config = json.load(f)
except Exception as e:
	raise

# Proper Logging
try:
	logSettings = config.get('LOGFILE', {})
	log_file = os.getcwd() + '/logfile/' + logSettings.get('FILENAME', 'templogger.log')
	logger = logging.getLogger('templogger')
	# LogLevel: DEBUG:10, INFO:20, WARNING:30, EERROR:40, CRITICAL:50
	logger.setLevel(10)
	fhandler = logging.FileHandler(log_file,'a')
	fhandler.setLevel(logSettings.get('FILELOGLEVEL', 20))
	shandler = logging.StreamHandler()
	shandler.setLevel(logSettings.get('STREAMLOGLEVEL', 20))
	formater = logging.Formatter('%(asctime)s %(levelname)-8s (%(name)s) %(message)s', '%Y-%m-%d %H:%M')
	fhandler.setFormatter(formater)
	shandler.setFormatter(formater)
	logger.addHandler(fhandler)
	logger.addHandler(shandler)
except Exception as e:
	raise
else:
	logger.info('starting templogger')
	logger.info('using: {}'.format(config_file))
	logger.info('logfile location: {}'.format(log_file))

# Starting MQTT Connection
def mqtt_on_connect(client, userdata, flags, rc):
	if rc == 0:
		logger.info('mqtt connection result: {}'.format(str(rc)))
	else:
		logger.error('mqtt connection result: {}'.format(str(rc)))

def mqtt_on_publish(client, userdata, mid):
	logger.info('mqtt publish mid: {}'.format(str(mid)))

try:
	mqttSettings = config.get('MQTT', {})
	mqttAddress = mqttSettings.get('BROKER_ADDRESS', 'localhost')
	mqttPort = mqttSettings.get('BROKER_PORT', 1833)
	mqttClient = mqtt.Client(mqttSettings.get('CLIENT_NAME', 'mqtt_templogger_client'))
	
	if (mqttSettings.get('AUTHENTICATION', False)):
		mqttClient.username_pw_set(mqttSettings.get("USERNAME"),mqttSettings.get("PASSWORD"))
	
	mqttClient.on_publish = mqtt_on_publish
	mqttClient.on_connect = mqtt_on_connect
	mqttClient.connect(mqttAddress,mqttPort,mqttSettings.get('KEEP_ALIVE', 60))

	mqttClient.loop_start()
except Exception as e:
	logger.error('MqttError at {0}:{1} ({2})'.format(mqttAddress, mqttPort, e))

# Loading Arexx TL-500
dev = device.TL500()

# Loading Dataanalyzer
data = data.Analyzer()

# Main Loop
while True:

	if not dev.connected():
		dev.connect()
		time.sleep(30)
	else:
		devData = dev.readData()
		if devData is not None:

			try:
				sensor = data.analyze(devData)
			except Exception as e:
				#pass
				raise
			else:
				# Only log Data with an age upto 30min/1800s
				if (time.time() - sensor.getTimestamp()) < 1800:
					# Send Data to MQTT Broker
					sensor.mqttSend(mqttClient, mqttSettings.get('QOS', 0))
					
				time.sleep(0.05)	
		else:
			time.sleep(30)