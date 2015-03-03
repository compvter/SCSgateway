#!/usr/bin/python3
import serial
import cherrypy
import threading
import time
import threading
import queue
import json

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

nomi = {"11":[False,False,"ingresso"],
"12":[False,False,"ingresso laterale"],
"13":[False,False,"reception"],
"14":[False,False,"scala"],
"15":[False,False,"corridoio pT"],
"16":[False,False,"cabinati"],
"17":[False,False,"antibagno pT"],
"18":[False,False,"bagno pT"],
"21":[False,False,"museo 1"],
"22":[False,False,"museo 2"],
"23":[False,False,"museo 3"],
"24":[False,False,"sgabuzzino museo"],
"33":[False,False,"simulatore"],
"34":[False,False,"sottoscala"],
"35":[False,False,"rack"],
"51":[False,False,"corridoio p1"],
"52":[False,False,"sgabuzzino rack"],
"53":[False,False,"fablab 1"],
"54":[False,False,"ufficio 1"],
"55":[False,False,"slot car"],
"56":[False,False,"emeroteca"],
"57":[False,False,"fablab 2"],
"58":[False,False,"ufficio 2"],
"61":[False,False,"sala riunioni 2"],
"62":[False,False,"sala riunioni 1"],
"63":[False,False,"sala riunioni 3"],
"64":[False,False,"sala riunioni 4"],
"65":[False,False,"antibagno p1"],
"66":[False,False,"bagno p1"],
"67":[False,False,"sgabuzzino sala riunioni"]}


ser.write("@MA".encode())
ser.write("@l".encode())


def serialread():  #Continuous loop to read serial
	array = []
	trasmissione = 0
	while True:
		line=ser.readline()
		octet=line.decode('utf-8').split()
		if len(octet) == 2:		#Only messages from the bus, no echo
			octet=octet[1]
		else:
			octet=None

		if octet == "A8":					#Start of frame
			trasmissione = True

		#if trasmissione is False and octet == "A5":					#Acknowledgement TODO
			#ackqueue.put(["ACK"])

		if trasmissione is True:
			array.append(octet)

		if len(array) >= 7: 				#Reached max MTU
			if octet == "A3":				#End of frame
				trasmissione = False
				checksum = int(array[1],16)^int(array[2],16)^int(array[3],16)^int(array[4],16)
				if checksum == int(array[5],16):
					sreadqueue.put(array)
			else:	 #The packet did not terminate with A3. This is an error. Drop everything.
				trasmissione = False
				array = []


def serialprint(serial,message):
	xor = message[0]^0x50^0x12^message[1]
	key = "@W7A8"+hex(message[0])[2:4]+"50120"+hex(message[1])[2:4]+str(hex(xor)[2:4])+"A3"
	serial.write(key.encode())

def deduplicator():
	lastpacket = ['inizio'] #Dummy packet
	while True:
		serialinput = sreadqueue.get()
		if (set(serialinput) != set(lastpacket)):  #If the queue returned something (i.e. a packet) and it's not a duplicate, forward along
			inpacketqueue.put(serialinput)
			lastpacket = serialinput[0:7]
			print(lastpacket)

def logger(packet):
	if int(packet[4]) == 4:
		nomi[str(packet[2])][1] = False
	elif int(packet[4]) == 8:
		nomi[str(packet[2])][1] = True

def switch():
	while True:
		time.sleep(0.01)
		if not swritequeue.empty():
			serialprint(ser,swritequeue.get())
		if not inpacketqueue.empty():
			logger(inpacketqueue.get())

class LightAPI(object):
	@cherrypy.expose
	def action(self,id=0,status=0):
		answer = ""
		swritequeue.put([int(id,16),int(status,16)])
#		return answer

	def status(self):
		return json.dumps(nomi,sort_keys=True)
	status.exposed = True

	def index(self):
		body = """<html><title>comPVter Lighting system</title><body>"""
		for i in nomi:
			name = nomi[i]
			body = ''.join([body,name," <a href=\"/action?id=",i,"&status=8\">ON</a>  <a href=\"/action?id=",i,"&status=4\">OFF</a><br>"])
		body = ''.join([body,"<a href=/action?id=ff&status=4>OFF GENERALE</a>"])
		return body
	index.exposed = True

sreadqueue 		= queue.Queue()	#Queue for packets coming from the serial
inpacketqueue 	= queue.Queue()	#Queue of deduplicated packets
swritequeue 	= queue.Queue()	#Queue of commands to write

serialreadThread = threading.Thread(target=serialread)
serialreadThread.start()

switchThread = threading.Thread(target=switch)
switchThread.start()

dedupThread = threading.Thread(target=deduplicator)
dedupThread.start()

cherrypy.server.socket_host = "0.0.0.0"
cherrypy.quickstart(LightAPI())
