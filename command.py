#!/usr/bin/python3
import serial
ser = serial.Serial('/dev/ttyUSB0', 115200)
import sys

header = 0xa8
num = int(sys.argv[1],16)
ter = 0x50
quat = 0x12
stat = int(sys.argv[2],16 )*4
xor = num^ter^quat^stat
trailer = 0xa3

key = [hex(header),hex(num),hex(ter),hex(quat),hex(stat),hex(xor),hex(trailer)]
print(key)

key = "@W7A8"+str(sys.argv[1])+"50120"+str(int(sys.argv[2])*4)+str(hex(xor)[2:4])+"A3"

print(key)

ser.write(key.encode())
