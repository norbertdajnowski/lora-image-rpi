
import sys
import io
import os
from time import sleep
from SX127x.LoRa import *
from SX127x.LoRaArgumentParser import LoRaArgumentParser
from SX127x.board_config import BOARD
import math
from PIL import Image

BOARD.setup()

parser = LoRaArgumentParser("Simple LoRa image transfer")
parser.add_argument('--single', '-S', dest='single', default=False, action="store_true", help="Single transmission")
parser.add_argument('--wait', '-w', dest='wait', default=0.2, action="store", type=float, help="Waiting time between transmissions (default is 0s)")

class myLoRa(LoRa):

	
	image_buffer = []
	image_buffer = []
	buffer_size = []
	iteration = 0		
	number_packets = 0
	step = 253
	sending = 0
	resto = 0
	first_time = 1
  
 

	def __init__(self, verbose=False):
		super(LoRaBeacon, self).__init__(verbose)
		self.set_mode(MODE.SLEEP)
		self.set_dio_mapping([0] * 6)
        self.var=0
	

	def re_init(self):
		
		self.image_buffer = []
		self.buffer_size = []
		self.iteration = 0		
		self.number_packets = 0
		self.step = 253
		self.sending = 0
		self.resto  = 0
		self.first_time = 1

	def semi_re_init(self):
		self.iteration = 0
	

	def take_pic(self):
		print "Taking Pic...."

		# raspistill command for taking pictures from Raspberry Cam
		os.system("raspistill -th none -vf -w 640 -h 480 -q 10 -o currentPicture.jpg")
		os.system("convert currentPicture.jpg teste.bmp")

		# Open saved picture
		with open("currentPicture.jpg","rb") as imageFile:
			f = imageFile.read()

		self.image_buffer = bytearray(f)
		self.buffer_size = sys.getsizeof(self.image_buffer)
		self.number_packets = int( self.buffer_size / self.step)

	def send_image(self):     

		if self.sending == 1:

			# Normal packet
			if self.iteration < self.number_packets:

				# Appending packet number, 1 byte
				Z = bytearray([self.iteration,0])

				# Appending bytearray from picture, 253 bytes
				Z[1:] = self.image_buffer[self.iteration * self.step : self.iteration * self.step + self.step]                
				print "I'm on %d" % self.iteration

				# Casting to List (needed)
				E = list(Z)     
				
				# Increment Packet number
				self.iteration += 1

				# Init SPI transmission to radio
				self.write_payload(E)
				BOARD.led_on()
				self.set_mode(MODE.TX)

			# Last packet
			elif self.iteration == self.number_packets: 

				print "Sending remaining bytes....."           
				# Appending packet number, 1 byte
				Z = bytearray([self.iteration,0])
				print "Packet: %d" % self.iteration

				# Appending bytearray from picture, X remaining bytes
				Z[1:] = self.image_buffer[self.iteration * self.step:]            

				# Casting to List (needed)
				E = list(Z) 

				# Init SPI transmission do radio
				self.write_payload(E)
				BOARD.led_on()
				self.set_mode(MODE.TX)

				# Reset global variables
				if self.first_time == 0:		
					self.re_init()
					print "Waiting for new pic..."
				else:
					self.semi_re_init()
					print "Sending picture second time..."
					self.first_time = 0

	def on_tx_done(self):
		global args
		self.set_mode(MODE.STDBY)
		self.clear_irq_flags(TxDone=1)
		BOARD.led_off()
		sleep(args.wait)
		if self.sending == 1:
			self.send_image()   

    def on_cad_done(self):
        print("\non_CadDone")
        print(self.get_irq_flags())

    def on_rx_timeout(self):
        print("\non_RxTimeout")
        print(self.get_irq_flags())

    def on_valid_header(self):
        print("\non_ValidHeader")
        print(self.get_irq_flags())

    def on_payload_crc_error(self):
        print("\non_PayloadCrcError")
        print(self.get_irq_flags())

    def on_fhss_change_channel(self):
        print("\non_FhssChangeChannel")
        print(self.get_irq_flags()) 

	# Main function
	def start(self):
		global args                
		BOARD.led_on()
	
		while True:

			sleep(0.5) # Needed for some unknown reason.

			if self.sending == 0: # If not sending
				print "Starting process..."
				#sleep(4)

				self.sending = 1
								
				self.take_pic() # Take new picture
					
				print "Sending picture first time..."
				print "Picture size: %d bytes." % self.buffer_size 
				print "Full packets: %d" % self.number_packets
				print "Last packet: %d bytes." % (self.buffer_size%self.step)

				self.send_image() # Iniciate IRQ recurssion            
				

lora = myLoRa(verbose=False)
args = parser.parse_args(lora)
lora.set_pa_config(pa_select=1, max_power=21, output_power=15)
lora.set_bw(BW.BW125)
lora.set_coding_rate(CODING_RATE.CR4_8)
lora.set_spreading_factor(12)
lora.set_rx_crc(True)
#lora.set_lna_gain(GAIN.G1)
#lora.set_implicit_header_mode(False)
lora.set_low_data_rate_optim(True)

assert(lora.get_agc_auto_on() == 1)

try:
    print("START")
    lora.start()
except KeyboardInterrupt:
    sys.stdout.flush()
    print("Exit")
    sys.stderr.write("KeyboardInterrupt\n")
finally:
    sys.stdout.flush()
    print("Exit")
    lora.set_mode(MODE.SLEEP)
    BOARD.teardown()
