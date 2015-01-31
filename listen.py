#!/usr/bin/python3
import serial
import cherrypy

ser = serial.Serial('/dev/ttyUSB0', 115200, timeout=1)

nomi = {"11":"ingresso",
"12":"ingresso laterale",
"13":"reception",
"14":"scala",
"15":"corridoio p1",
"16":"cabinati",
"17":"antibagno p1",
"18":"bagno p1",
"21":"museo 1",
"22":"museo 2",
"23":"museo 3",
"24":"sgabuzzino museo",
"33":"simulatore",
"34":"sottoscala",
"35":"rack",
"51":"corridoio p2",
"52":"sgabuzzino rack",
"53":"fablab 1",
"54":"ufficio 1",
"55":"slot car",
"56":"emeroteca",
"57":"fablab 2"}
"58":"ufficio 2",
"61":"sala riunioni 2",
"62":"sala riunioni 1",
"63":"sala riunioni 3",
"64":"sala riunioni 4",
"65":"antibagno p2",
"66":"bagno p2",
"67":"sgabuzzino sala riunioni",

def send(id,stat):
	xor = id^ter^quat^stat
	key = "@W7A8"+hex(id)[2:4]+"50120"+hex(stat)[2:4]+str(hex(xor)[2:4])+"A3"
	ser.write(key.encode())
	return key

class LightAPI(object):
	@cherrypy.expose
	def action(self,id=0,status=0):
		answer = send(int(id,16),int(status,16))
		return answer

	def index(self):
		body = """<html><title>comPVter Lighting system</title><body>"""
		for i in nomi:
			name = nomi[i]
			body = ''.join([body,name," <a href=\"/action?id=",i,"&status=8\">ON</a>  <a href=\"/action?id=",i,"&status=4\">OFF</a><br>"])
		return body
	index.exposed = True


cherrypy.quickstart(LightAPI())

array = []
trasmissione = 0

while True:
	line=ser.readline()
	try:
		octet=line.decode('utf-8').split(" ")[1]
	except IndexError:
		octet = "00"

	if octet == "A5":
		print("ACK")

	if octet == "A8":
		trasmissione = 1

	if trasmissione == 1:
		array.append(octet)

	if octet == "A3":
		trasmissione = 0
		checksum = int(array[1],16)^int(array[2],16)^int(array[3],16)^int(array[4],16)
		if checksum == int(array[5],16):
			comando = "ON"
			if array[4] == "04":
				comando = "OFF"
			print(nomi[array[2]], comando)
			#print("ERRORE CHECKSUM")
#		print("checksum "+hex(checksum))
		
		array=[]