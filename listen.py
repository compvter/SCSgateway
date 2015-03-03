#!/usr/bin/python3
import serial
import cherrypy
import threading
import time
import threading
import queue

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

nomi = {"11":["ingresso",False,False],
"12":["ingresso laterale",False,False],
"13":["reception",False,False],
"14":["scala",False,False],
"15":["corridoio pT",False,False],
"16":["cabinati",False,False],
"17":["antibagno pT",False,False],
"18":["bagno pT",False,False],
"21":["museo 1",False,False],
"22":["museo 2",False,False],
"23":["museo 3",False,False],
"24":["sgabuzzino museo",False,False],
"33":["simulatore",False,False],
"34":["sottoscala",False,False],
"35":["rack",False,False],
"51":["corridoio p1",False,False],
"52":["sgabuzzino rack",False,False],
"53":["fablab 1",False,False],
"54":["ufficio 1",False,False],
"55":["slot car",False,False],
"56":["emeroteca",False,False],
"57":["fablab 2",False,False],
"58":["ufficio 2",False,False],
"61":["sala riunioni 2",False,False],
"62":["sala riunioni 1",False,False],
"63":["sala riunioni 3",False,False],
"64":["sala riunioni 4",False,False],
"65":["antibagno p1",False,False],
"66":["bagno p1",False,False],
"67":["sgabuzzino sala riunioni",False,False]}


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
