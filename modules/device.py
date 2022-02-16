import logging, time

try:
	import usb.core, usb.util
except Exception as e:
	raise

logger = logging.getLogger('templogger.device')

# Arexx TL-500 Device
class TL500:
	def __init__(self):
		self.logger = logging.getLogger('templogger.device.TL500')
		self.logger.debug('starting new instance')
		self.device = None
		self.interface_read = None
		self.interface_write = None
		self.connect()

	# Connect the USB Device
	def connect(self):
		# Find USB Device
		self.logger.info('trying to connect to device')	
		self.logger.debug('search for device')

		try:
			self.device = usb.core.find( idVendor=0x0451, idProduct=0x3211 )
		except Exception as e:
			self.logger.error('failed to find device')
		else:
			self.logger.debug('device found')
		
		if self.device is not None:
			# Set USB Configuration
			self.logger.debug('trying to set configuration')
			try:
				self.device.set_configuration()
			except Exception as e:
				self.logger.error('failed to set configuration')
			else:
				self.logger.debug('successfully set configuration')
			
			# Load USB Interface
			self.logger.debug('trying to load interface')
			try:
				cfg = self.device.get_active_configuration()
				self.interface_write = cfg[(0,0)][0]
				self.interface_read = cfg[(0,0)][1]
			except Exception as e:
				self.logger.error('failed to load interface')
			else:
				self.logger.debug('successfully loaded interface')
				self.logger.info('successfully connected to device')

			# Update Device Time
			if self.interface_write is not None:
				self.setDeviceTime()
			
	# Check for USB Device
	def connected(self):
		return (True if self.device else False)
	
	# Read Data
	def readData(self):
		# Build write Buffer
		buffer = bytearray(64)
		buffer[0] = 3 # Cmd for DataReadout

		self.logger.debug('trying to receive data')		
		try:
			self.interface_write.write(buffer)
			data = self.device.read(self.interface_read.bEndpointAddress,self.interface_read.wMaxPacketSize)
		except Exception as e:
			self.logger.error('failed to request data: disconnected')
			self.logger.error('templogger will exit in 5min')
			time.sleep(300)
			exit()
		else:
			# Only do stuff if the data is new
			if data[1] != 0:
				self.logger.debug('successfully requested data')
				return data
			else:
				self.logger.debug('no new data')
				return None

	# Set Device Time
	def setDeviceTime(self):
		"""
		Internal Timer counts Seconds since 01/01/2000 @ 12:00am (UTC)
		Equals UNIX Timestamp minus 946684800 Seconds
		"""
		# Encode Time to List of Bytes
		bt = bytetime(time.time() - 946684800)

		# Build write Buffer
		buffer = bytearray(64)
		buffer[0] = 4 # Cmd for TimeUpdate
		
		for i in range(4):
			buffer[i+1] = bt[i]

		# Write Buffer to Device
		try:
			self.interface_write.write(buffer)
		except Exception as e:
			self.logger.warning('failed to update system time')
		else:
			self.logger.info('successfully updated system time')

# Encode timestamp to bytetime
def bytetime(timestamp):
	n = timestamp
	bytetime = []

	while n:
		n, m = divmod(int(n), 256)
		bytetime.append(m)
	
	return bytetime