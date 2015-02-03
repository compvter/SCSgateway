#!/usr/bin/python3
import serial
import cherrypy
import threading
import time
import threading
import queue

ser = serial.Serial('/dev/ttyS0', 115200, timeout=1)

nomi = {"11":"ingresso",
"12":"ingresso laterale",
"13":"reception",
"14":"scala",
"15":"corridoio pT",
"16":"cabinati",
"17":"antibagno pT",
"18":"bagno pT",
"21":"museo 1",
"22":"museo 2",
"23":"museo 3",
"24":"sgabuzzino museo",
"33":"simulatore",
"34":"sottoscala",
"35":"rack",
"51":"corridoio p1",
"52":"sgabuzzino rack",
"53":"fablab 1",
"54":"ufficio 1",
"55":"slot car",
"56":"emeroteca",
"57":"fablab 2",
"58":"ufficio 2",
"61":"sala riunioni 2",
"62":"sala riunioni 1",
"63":"sala riunioni 3",
"64":"sala riunioni 4",
"65":"antibagno p1",
"66":"bagno p1",
"67":"sgabuzzino sala riunioni"}


def serialread():  #Continuous loop to read serial
	array = []
	trasmissione = 0
	while True:
		line=ser.readline()
		try:
			octet=line.decode('utf-8').split(" ")[1]
			if octet.startswith("SCS"):		#Only messages from the bus, no echo
				sreadqueue.put(inbox)
		except IndexError:
			octet = None

		#if trasmissione is False and octet == "A5":					#Acknowledgement TODO
			#ackqueue.put(["ACK"])

		if octet == "A8":					#Start of frame
			trasmissione = True

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
	print(key.encode())


def deduplicator():
	lastpacket = None
	while True:
		serialinput = sreadqueue.get()
		if serialinput is not None and serialinput is not lastpacket:  #If the queue returned something (i.e. a packet) and it's not a duplicate, forward along
			inpacketqueue.put(serialinput)
			lastpacket = serialinput


def printqueue():
	while True:
		serialprint(ser,swritequeue.get())


class LightAPI(object):
	@cherrypy.expose
	def action(self,id=0,status=0):
		answer = ""
		swritequeue.put([int(id,16),int(status,16)])
#		return answer

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

printThread = threading.Thread(target=printqueue)
printThread.start()

dedupThread = threading.Thread(target=deduplicator)
dedupThread.start()

cherrypy.server.socket_host = "0.0.0.0"
cherrypy.quickstart(LightAPI())


