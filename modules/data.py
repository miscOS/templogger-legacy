import json, logging, math, os

logger = logging.getLogger('templogger.data')

class Analyzer():

	def __init__(self):
		self.logger = logging.getLogger('templogger.data.analyzer')
		self.logger.debug('starting new instance')
		self.sensorInfo = None
		self.loadSensorInfo()

	# Analyze the Data of TL500 Device
	def analyze(self, devData):
		self.logger.debug('analyzing called')
		try:
			sensorId = devData[3] * 256 + devData[2]
			# Offset for newer sensor
			i = 0
			if (sensorId & 24576) == 0:
				sensorId += devData[4] * (256**2)
				i += 2

			timestamp = devData[9+i]*(256**3) + devData[8+i]*(256**2) + devData[7+i]*256 + devData[6+i] + 946684800
			byteValue = devData[4+i] * 256 + devData[5+i]
			# rawvalue is signed
			if byteValue >= (256**2)/2:
				byteValue -= 256**2

		except Exception as e:
			self.logger.error('failed to analyze devData')
			raise Exception('AnalyzingDevDataError')
		else:
			sensor = Sensor(sensorId)
			sensor.setTime(timestamp)

			info = self.sensorInfo.get(str(sensorId), None)
			if info:
				sensor.setName(info.get('NAME', None))
				sensor.setMqtt(info.get('MQTT', None))

				scope = info.get('CALIBRATION', None)
				if scope:
					sensor.setValue(self.linearCal(self.convertValue(sensorId, byteValue), scope.get('SCALE', 1), scope.get('OFFSET', 0)))
				else:
					sensor.setValue(self.convertValue(sensorId, byteValue))
			else:
				sensor.setValue(self.convertValue(sensorId, byteValue))

			return sensor

	# Convert byteValue to actualValue
	def convertValue(self, sensorId, byteValue):
		
		if (sensorId & 24577) == 8192 or (sensorId & 196609) == 131072:
			(value, unit) = self.convertTL_3TSN(byteValue)
		elif (sensorId & 61441) == 16384 or (sensorId & 196609) == 196608:
			(value, unit) = self.convertTSN_TH70E_TEMP(byteValue)
		elif (sensorId & 61441) == 16385 or (sensorId & 196609) == 196609:
			(value, unit) = self.convertTSN_TH70E_HUMIDITY(byteValue)
		else:
			self.logger.error('unknown sensorType: sensorId({0!s})'.format(sensorId))
			raise Exception("UnknownSensorException")
		
		return (value, unit)

	def convertTL_3TSN(self, byteValue):
		"""
		TL-3TSN and TSN-50E use the same function
		"""
		self.logger.debug('sensorType=TL-3TSN/TSN-50E')
		value = 0.0078125 * byteValue 
		unit = "degC"
		return (value, unit)

	def convertTSN_TH70E_TEMP(self, byteValue):
		self.logger.debug('sensorType=TSN-TH70E-TEMP')
		value = 0.01 * byteValue - 39.6 
		unit = "degC"
		return (value, unit)

	def convertTSN_TH70E_HUMIDITY(self, byteValue):

		self.logger.debug('sensorType=TSN-TH70E-HUMIDITY')
		value =  -4
		value += 0.0405 * byteValue
		value -= 0.0000028 * math.pow(byteValue, 2)
		unit = "RH%"
		return (value, unit)

	# Linear calibration
	def linearCal(self, data, scale, offset):
		return (scale * data[0] + offset, data[1])

	# Load aditional sensor info
	def loadSensorInfo(self):
		filename = os.getcwd() + '/config/sensor.json'
		with open(filename,'r') as f:
			self.sensorInfo = json.load(f)
			self.logger.info('sensorInfo location: {}'.format(filename))

class Sensor():
	def __init__(self, sensorId):
		self.logger = logging.getLogger('templogger.data.sensor')
		self.logger.debug('new instance for sensorId={}'.format(sensorId))
		self.id = sensorId
		self.name = None
		self.mqtt = []
		self.time = None
		self.value = None
		self.unit = None

	def mqttSend(self, mqttClient, mqttQOS=0):
		dict = {'id': self.getId(), 'name': self.getName(), 'time': self.getTime(), 'timestamp': self.getTimestamp(), 'value': self.getValue(), 'unit': self.getUnit()}

		for mqtt in self.mqtt:
			if 'TOPIC' not in mqtt:
				self.logger.warning('mqttSend: no TOPIC set')
				continue
			if 'PAYLOAD' not in mqtt:
				self.logger.warning('mqttSend: no PAYLOAD set')
				continue

			try:
				topic = str(mqtt['TOPIC']).format_map(dict)
				msg = str(mqtt['PAYLOAD']).format_map(dict)
				(rc, mid) = mqttClient.publish(topic,msg,mqttQOS)
			except Exception as e:
				self.logger.warning('mqttSendError: {}'.format(e))
			else:
				self.logger.info('mqttSend status: {0}; mid: {1}'.format(str(rc),str(mid)))

	def setName(self, name):
		if name:
			self.name = name
			self.logger.debug('set name={0}'.format(self.name))

	def setMqtt(self, mqtt):
		if mqtt:
			self.mqtt = mqtt
			self.logger.debug('set mqtt={0}'.format(self.mqtt))

	def setTime(self, time):
		self.time = time
		self.logger.debug('set time={0}'.format(self.time))

	def setValue(self, data):
		self.value =data[0]
		self.unit = data[1]
		self.logger.debug('set value={0}, unit={1}'.format(self.value,self.unit))

	def getId(self):
		return self.id

	def getName(self):
		return self.name

	def getMqtt(self):
		return self.mqtt
	
	def getTime(self):
		return self.time
	
	def getTimestamp(self):
		return self.time

	def getValue(self):
		return round(self.value, 2)

	def getUnit(self):
		return self.unit