#-------------------------------------------
#
#    ESP32 WiFi Camera (Grove Serial Camera Version)
#    ESP32WiFiCAM-JPEGCamera
#
#    file:GroveCAM.py
#   
#
#  a Class for controlling Grove Serial Camera Kit
#
#   e.g   http://wiki.seeedstudio.com/Grove-Serial_Camera_Kit/
#         https://www.switch-science.com/catalog/1626/
#         
#

from time import sleep
import mylib
import utime  # for time measurement of execute
import uselect

WAIT_TIME = 0.5
POLLING_TIMEOUT = 500  # timeout of polling is 500msec 

MAX_RETRY_COUNT = 100
MAX_CONNECT_RETRY_COUNT = 50
MAX_RECEIVE_RETRY_COUNT = 50

CAM_PACKAGE_SIZE = 256
PACKAGE_HEADER_VRFY = 6

ACK = bytes((0xAA, 0x0E, 0x00, 0x00, 0x00, 0x00))
SYNC = bytes((0xAA, 0x0D, 0x00, 0x00, 0x00, 0x00))
ACK_FOR_SYNC = bytes((0xAA, 0x0E, 0x0D, 0x00, 0x00, 0x00))

CMD_ID_TBL = {'INITIAL' : 0x01, 'GET_PICTURE' : 0x04, 'SNAPSHOT' : 0x05,
              'SET_PACKAGE_SIZE' : 0x06, 'SET_BAUD_RATE' : 0x07,
              'RESET' : 0x08, 'POWER_DOWN' : 0x09, 'DATA' : 0x0A,
              'SYNC' : 0x0D, 'ACK' : 0x0E, 'NAK' : 0x0F,}

CMD_NAME_TBL = {0x01 : 'INITIAL', 0x04 : 'GET_PICTURE', 0x05 : 'SNAPSHOT', 
                0x06 : 'SET_PACKAGE_SIZE', 0x07 : 'SET_BAUD_RATE', 
                0x08 : 'RESET', 0x09 : 'POWER_DOWN', 0x0A : 'DATA', 
                0x0D : 'SYNC', 0x0E : 'ACK', 0x0F : 'NACK',}


PACKET_SIZE=6

#DBG_MEMORY_REPORT = True
DBG_MEMORY_REPORT = False

class GroveCAM():

    def __init__(self,uart):    
        self.uart = uart

    def setup(self):
        status = self.makeConnection()
        if status == True:
            print('Camera connection OK!')
            self.sendCmd('INITIAL',0x00,0x07,0x00,0x07)
            self.sendCmd('SET_PACKAGE_SIZE',0x08,0x00,0x01,0x00)  # 0x100 (256B)
            return True
        else:
            print('Error!! Camera connection Failed!')
            return False
    
    def makeConnection(self):
        for x in range(MAX_CONNECT_RETRY_COUNT):
            print('send init...')
            self.sendPacket(SYNC)
            sleep(WAIT_TIME)
            size = self.uart.any()
            if size == 0:
                print("no response")
                continue
            elif size < PACKET_SIZE:
                print("receive some data, drop")
                self.uart.read()  # read and drop
                continue
            packet = self.receivePacket()
            if packet is None:
                print('Error in makeConnection')
                print('cannot receive packet')
            else:
                if self.getPacketType(packet) == 'ACK': 
                   sleep(WAIT_TIME)
                   packet = self.receivePacket()
                   # we expect [ACK]->[SYNC]
                   if self.getPacketType(packet) == 'SYNC': 
                       print('receive:ACK_SYNC')
                       self.sendPacket(ACK_FOR_SYNC)
                       print('establised connection')
                       return True
                   else:
                       print('Error in makeConnection')
                       print('cannot receive SYNC packet')
                       return False
                else:
                    print('Error in makeConnection')
                    print('cannot receive ACK packet')
                    return False
        # exit loop
        print('Error in makeConnection')
        print('cannot receive packet')
        return False
    
    #
    # return False ... fail to take picture
    #        fileWithPath(str) .... success to  take picture
    #
    def takePictureAndSaveToFile(self,fileName):
    
        ret = self.sendCmd('SNAPSHOT',0x00,0x00,0x00,0x00)  # snap No1 (drop)
        ret = self.sendCmd('SNAPSHOT',0x00,0x00,0x00,0x00)  # snap No2
    
        if ret == False:
            print('Error in takePicture; fail to exec SNAPSHOT')
            return False
    
        ret = self.sendCmd('GET_PICTURE',0x01,0x00,0x00,0x00)
    
        if ret == False:
            print('Error in takePicture; fail to exec GET_PICTURE')
            return False
    
        if self.getPacketType(ret) != 'DATA':
            print('Error in takePicture, Illegal Response type')
            return False
    
        # get PictSize
        pictSize = ret[5]
        pictSize <<= 8
        pictSize |= ret[4]
        pictSize <<= 8
        pictSize |= ret[3]
       
        if pictSize == 0:
            print('Error in takePicture, pictSize is 0')
            return False
    
        print("pictSize:{:d}".format(pictSize))
        mylib.collectMemory()
        s = utime.ticks_ms()   # for time measurement
        with open(fileName, 'wb') as f:
            state = self.getImageDataAndWriteFile(pictSize, f)
            mylib.collectMemory()
        e = utime.ticks_ms()   # for time measurement    
        diff = utime.ticks_diff(e, s)
        print("receive picture and save takes:{:d}(ms)".format(diff))
        return True
    
    def getImageDataAndWriteFile(self, pictSize, fp=None, verb=False):

        buffer=bytearray(CAM_PACKAGE_SIZE)
        n_of_blocks = int(pictSize / (CAM_PACKAGE_SIZE - PACKAGE_HEADER_VRFY))
        get_size=0
    
        #
        # receive  packets
        #

        poll = uselect.poll()
        poll.register(self.uart, uselect.POLLIN)

        for i in range(0, n_of_blocks):
            lowCount = i & 0xFF
            highCount = (i >> 8) & 0xFF
            self.sendCmd('ACK',0,0,lowCount,highCount,True)
            getPacket = False    # flag for nth packet is received or not
    
            #s = utime.ticks_ms()   # for time measurement
            for i in range(MAX_RETRY_COUNT):

                if poll.poll(POLLING_TIMEOUT):

                    size = self.uart.any() 
                    if verb:
                        print('uart receive size:{:d}'.format(size))
    
                    if size != CAM_PACKAGE_SIZE:
                        if verb:
                           print('w.. ',end="")
                        continue
                    else:
                        get_size += CAM_PACKAGE_SIZE
                        if verb:
                            print(get_size)
                        self.uart.readinto(buffer,size)
                        # for time measurement (tune up)
                        #e = utime.ticks_ms()
                        #diff = utime.ticks_diff(e, s)
                        #print("write time:{:d}(ms)".format(diff))
                        #if diff == 0:
                        #     pass
                        #else:
                        #     print("{:d}pbs".format(int(512 * 8 * 1000 / diff )))
                        #if verb:
                        #    print(buffer)
                        if fp is None:
                            print(buffer)
                        else:
                            fp.write(buffer[4:(size-2)])   # strip headner and verify field
                        if DBG_MEMORY_REPORT:
                            print(mylib.reportMemory()) # for debug
                        getPacket = True
                        break

      
            # check packet is read or not
            if not getPacket:
                print('Fail to read packet in {:d} times'.format(MAX_RETRY_COUNT))
                print('so discard this picture')           
                self.dummyGetImageData()
                return False
    
        #
        # receive last packet 
        #
        # PACKAGE_HEADER_VRFY means...  ID(2):SIZE(2):Verify(2)
        lestSize = pictSize - (CAM_PACKAGE_SIZE - PACKAGE_HEADER_VRFY) * n_of_blocks + PACKAGE_HEADER_VRFY  
        lowCount = n_of_blocks & 0xFF
        highCount = (n_of_blocks  >> 8) & 0xFF
      
        self.sendCmd('ACK', 0, 0, lowCount, highCount, True)
        for i in range(MAX_RETRY_COUNT):

            if poll.poll(POLLING_TIMEOUT):

                size = self.uart.any() 
                if verb:
                    print('uart receive size:{:d}'.format(size))
                if size != lestSize:
                    if verb:
                        print('not yet...')
                    continue
                else:
                    get_size += size
                    print(get_size)
                    self.uart.readinto(buffer,size)
                    if fp is None:
                        print(buffer)
                    else:
                        fp.write(buffer[4:(size-2)])   # strip headner and verify field
                    break
        
        if self.uart.any() == 0:
            print('read image completed')
    
        else:
            print('Warning: some data remains in UART buffer')
            print('rest size in buffer:{:d}'.format(self.uart.any()))
            self.dropPacket()
    

        del poll        # to be on the safe side
        buffer = None
        self.sendCmd('ACK',0,0,0xF0,0xF0,True)
        return True
    
    def sendCmd(self, cmd_name,param1=0,param2=0,param3=0,param4=0,no_receive=False):
        cmd_id = CMD_ID_TBL[cmd_name]
        if cmd_id is None:
            print('Error in sendCmd\n unkown command')
            return False
        self.sendPacket(bytes((0xAA,cmd_id,param1,param2,param3,param4)))
        if no_receive == True:
            return True
        # receive return packet
        for i in range(MAX_RECEIVE_RETRY_COUNT):
            packet=self.receivePacket()
            if packet is None:
                print('receive is none ,so retry')
                continue
            packet_type = self.getPacketType(packet)
            self.showPacket(packet)
            print('type:'+packet_type)
            if packet_type  == 'ACK':
                print('ACK')
                if cmd_name == 'GET_PICTURE' :
                    print('get picture...')
                    packet=self.receivePacket()
                    if packet is None:
                        print('Error in get picture')
                        print('cannot receive Data packet')
                        return False
                    else:
                        self.showPacket(packet)
                        if self.getPacketType(packet) == 'DATA':
                            print('size..')
                            print('{:02x},{:02x},{:02x}'.format(packet[3],packet[4],packet[5]))
                        else:
                            print('Error:not data packet')
                        return packet   # if get right status from Camera, then returns it to caller
                else:
                   return  packet   # if get right status from Camera, then returns it to caller
            elif packet_type  == 'NACK':
                print('NACK')
                return False
            else:
                print('Error Unkown type')
                return False
        print('cannot get receive packet')
        return False
    
    def stopToGetImage(self):
        self.sendCmd('ACK',0,0,0xF0,0xF0,True)
    
    def resetCamera(self):
        self.sendCmd('RESET',0,0,0,0,True)
    
    def receivePacket(self):
        print('R:',end='')
        for x in range(MAX_RECEIVE_RETRY_COUNT):
            if self.uart.any() >= PACKET_SIZE :
                return self.uart.read(PACKET_SIZE)
            else:
                print('.',end='')
                sleep(WAIT_TIME)
        return None
    
    
    def checkAckSync(self,packet):
        if (self.getPacketType(packet) == 'ACK') and (self.getPacketType(packet[6:]) == 'SYNC'):
            return True
        else:
            return False
    
    def getPacketType(self,packet):
        cmd_name = None
        if packet is None:
            return 'UNKNOWN_PACKET'
        if packet[0] == 0xAA:
            cmd_name = CMD_NAME_TBL.get(packet[1])
            if cmd_name is None:
                return 'UNKNOWN_PACKET'
            else:
                return cmd_name
        else:
            return 'UNKNOWN_PACKET'
    
    def sendPacket(self,packet):
        print('send',end='')
        self.showPacket(packet)
        self.uart.write(packet)
    
    def showPacket(self,packet):
        for i in range(len(packet)):
            print('[{:02x}]'.format(packet[i]),end='')
        print('')
    
    def dummyGetImageData(self):
        self.dropPacket()
        self.sendCmd('ACK',0,0,0xF0,0xF0,True)
    
    def dropPacket(self):
        print('drop packet from camera')
        print('size:{:d}bytes'.format(self.uart.any()))
        self.uart.read()     # read data from uart1 and drop
    
    