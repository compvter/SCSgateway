#!/usr/bin/python3
import serial
import cherrypy
import threading
import time
import threading
import queue
import json
import datetime
import requests

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

nomi = {
"11":{"on": False, "fromweb": False, "watt":270, "description": "ingresso"},
"12":{"on": False, "fromweb": False, "watt":216, "description": "ingresso laterale"},
"13":{"on": False, "fromweb": False, "watt":162, "description": "reception"},
"14":{"on": False, "fromweb": False, "watt":144, "description": "scala"},
"15":{"on": False, "fromweb": False, "watt":108, "description": "corridoio pT"},
"16":{"on": False, "fromweb": False, "watt":108, "description": "cabinati"},
"17":{"on": False, "fromweb": False, "watt":18, "description": "antibagno pT"},
"18":{"on": False, "fromweb": False, "watt":36, "description": "bagno pT"},
"21":{"on": False, "fromweb": False, "watt":324, "description": "museo 1"},
"22":{"on": False, "fromweb": False, "watt":324, "description": "museo 2"},
"23":{"on": False, "fromweb": False, "watt":324, "description": "museo 3"},
"24":{"on": False, "fromweb": False, "watt":60, "description": "sgabuzzino museo"},
"33":{"on": False, "fromweb": False, "watt":270, "description": "simulatore"},
"34":{"on": False, "fromweb": False, "watt":36, "description": "sottoscala"},
"35":{"on": False, "fromweb": False, "watt":60, "description": "rack"},
"51":{"on": False, "fromweb": False, "watt":162, "description": "corridoio p1"},
"52":{"on": False, "fromweb": False, "watt":60, "description": "sgabuzzino rack"},
"53":{"on": False, "fromweb": False, "watt":216, "description": "fablab 1"},
"54":{"on": False, "fromweb": False, "watt":108, "description": "ufficio 1"},
"55":{"on": False, "fromweb": False, "watt":270, "description": "slot car"},
"56":{"on": False, "fromweb": False, "watt":54, "description": "emeroteca"},
"57":{"on": False, "fromweb": False, "watt":216, "description": "fablab 2"},
"58":{"on": False, "fromweb": False, "watt":270, "description": "ufficio 2"},
"61":{"on": False, "fromweb": False, "watt":324, "description": "sala riunioni 2"},
"62":{"on": False, "fromweb": False, "watt":324, "description": "sala riunioni 1"},
"63":{"on": False, "fromweb": False, "watt":324, "description": "sala riunioni 3"},
"64":{"on": False, "fromweb": False, "watt":162, "description": "sala riunioni 4"},
"65":{"on": False, "fromweb": False, "watt":18, "description": "antibagno p1"},
"66":{"on": False, "fromweb": False, "watt":36, "description": "bagno p1"},
"67":{"on": False, "fromweb": False, "watt":60, "description": "sgabuzzino sala riunioni"}}

ser.write("@MA".encode())
ser.write("@l".encode())

def postusage():
	while True:
		try:
			wattage = postqueue.get()
			r = requests.get('http://172.18.0.8/emoncms/input/post.json?node=1&json={lightwatt:'+str(wattage)+'}&apikey=e8fd32598350e1568c090d283563057c', timeout=5)
		except:
			pass


def checkdouble(first,second):
	if nomi[first]["on"] & nomi[second]["on"]:
		swritequeue.put([int(second,16),0x4])


def overload():
	checkdouble("11","12")
	checkdouble("13","15")
	checkdouble("22","21")
	checkdouble("57","53")
	checkdouble("54","58")
	checkdouble("62","61")
	checkdouble("63","64")
	checkdouble("14","51")
	swritequeue.put([0x23,0x4])
	swritequeue.put([0x24,0x4])
	swritequeue.put([0x35,0x4])
	swritequeue.put([0x23,0x4])
	swritequeue.put([0x56,0x4])
	swritequeue.put([0x67,0x4])


def postinstconsumption():
	consumption = 0
	for i in nomi:
		this = nomi[i]
		if this["on"] == True:
			consumption = consumption + this["watt"]
	postqueue.put(consumption)

def instconsumption():
	while True:
		postinstconsumption()
		time.sleep(15)


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
	time.sleep(0.75)

def deduplicator():
	lastpacket = ['inizio'] #Dummy packet
	while True:
		serialinput = sreadqueue.get()
		if (set(serialinput) != set(lastpacket)):  #If the queue returned something (i.e. a packet) and it's not a duplicate, forward along
			inpacketqueue.put(serialinput)
			lastpacket = serialinput[0:7]

def logger(packet):
	if int(packet[4]) == 4:
		try:
			nomi[str(packet[2])]["on"] = False
			nomi[str(packet[2])]["fromweb"] = False
			print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')+" "+str(packet)+" OFF")
			postinstconsumption()
		except:
			pass
	elif int(packet[4]) == 8:
		try:
			nomi[str(packet[2])]["on"] = True
			print(datetime.datetime.fromtimestamp(time.time()).strftime('%Y-%m-%d %H:%M:%S')+" "+str(packet)+" ON")
			postinstconsumption()
		except:
			pass


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

	@cherrypy.expose
	def poweroverload(self):
		overload()

	def status(self):
		tempdict = {}
		for lightid in nomi:
			tempdict[str(lightid)] = nomi[lightid]["on"]
		return json.dumps(tempdict,sort_keys=True)
	status.exposed = True

sreadqueue		= queue.Queue()	#Queue for packets coming from the serial
inpacketqueue	= queue.Queue()	#Queue of deduplicated packets
swritequeue		= queue.Queue()	#Queue of commands to write
postqueue		= queue.Queue() #Queue of power usage

serialreadThread = threading.Thread(target=serialread)
serialreadThread.start()

switchThread = threading.Thread(target=switch)
switchThread.start()

dedupThread = threading.Thread(target=deduplicator)
dedupThread.start()

loggingThread = threading.Thread(target=instconsumption)
loggingThread.start()

postusageThread = threading.Thread(target=postusage)
postusageThread.start()

cherrypy.server.socket_host = "0.0.0.0"
cherrypy.quickstart(LightAPI())