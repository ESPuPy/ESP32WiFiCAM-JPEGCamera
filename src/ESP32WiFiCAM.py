#-------------------------------------------
#
#    ESP32 WiFi Camera (Grove Serial Camera Version)
#    ESP32WiFiCAM-JPEGCamera
#
#    file:ESP32WiFiCAM.py
#   

#
#load modules
#
import network
import uos
import gc
import utime
from machine import Pin
from machine import UART
from machine import SPI
from sdcard import SDCard
from ST7735 import TFT
from terminalfont import terminalfont
from GroveCAM import GroveCAM
import cloudinaryUploader
import lineBOT
import mylib



ESPCAM_VERSION = 'ESPWifiCAM_JPG(V0.02)'
WAITTIME_IN_MAINLOOP = 0.3  # wait for 300msec

# define GC threshold memory size 
GC_THRESHOLD_SIZE = 512   # GC THRESHOLD 512Bytes


#
# WiFi Connection Parameters
#
SSID = 'ssidXXXXX'   # set SSID for connect WiFi Network
PASS = 'passXXXXX'   # set password  for connect WiFi Network


#
# LINE BOT AccessToken
# set your access token
LINE_TOKEN = '{R7QjYXXXXXXilFU=}'  # set LINE BOT Access Token

#
# Cloudinary Settings
#
CLOUD_NAME = '_your_cloud_name_'         # set cloud name  e.g  espcamera
API_KEY = '123XXXXXXXX890'               # set your API KEY
API_SECRET = 'KMqXXXXXXXXO4'             # set your API Secret Key


# define for SPI Speed
HSPI_BAUDRATE=20000000    # TFT/FIFO Control 20MHz
VSPI_BAUDRATE=32000000    # SD Control 32MHz



#
# PIN Assign
# for TFT
TFT_SPI_SCK = 14
TFT_SPI_MOSI = 13
TFT_SPI_MISO = 12
TFT_DC = 4
TFT_RESET = 16
TFT_CS = 27

# for SD 
SD_SPI_SCK = 18
SD_SPI_MOSI = 23
SD_SPI_MISO = 19
SD_CS  =  5

# for BUTTON AND Sensor
SHUTTERBUTTON = 36
HUMANSENSOR = 35

# for UART
CAM_TX = 17    # GroveCAM RxD
CAM_RX = 34    # GroveCAM TxD
CAM_UART_HIGH_SPEED = 115200 
CAM_UART_INIT_SPEED = 9600


# mask time to avoid rensya (human sensor)
NONRESPONSIVETIME_FOR_HUMAN_SENSOR = 15
    
# mask time to avoid rensya (shutter button chattering)
NONRESPONSIVETIME_FOR_BUTTON = 3
    
# number of take photo(s) when sensor is detected
NOFPHOTOINDETECT = 1

#----------------------------------
#  
#   ESP32 WiFi Camera Class 
#   ESP32WiFiCAM
#  
#  
class ESP32WiFiCAM():
    """ESP32 WiFi Camera Class"""

    def __init__(self):    

        #
        # var for instance of HSPI(for TFT and FIFO), TFT
        #
        self.hspi = None
        self.vspi = None
        self.tft = None
        self.sd = None

        #
        # flags for setup status
        #
        self.stat_sd = None     # status for SD
        self.stat_ntp = None    # status for NTP

        self.setupSDFileSystem=None
        self.stat_if = None     # status for NetworkInterface
        self.stat_glovecam = None # status for GloveCamera

        # var for instance of shutterButton
        self.shutter = None

        # var for instance of humanSensor
        self.humanSensor = None

        #import machine
        self.shutterPressed = False
        self.sensorDetected = False

        # variables for cron Time Manage 
        self.cron3MinNext = 0
        self.cron5MinNext = 0
        self.cron10MinNext = 0
        self.cron30MinNext = 0
        self.lastMin=0



    #----------------------------------------
    #
    # Setup
    #
    def setup(self):
    
        screen_pos_y = 0
        print('*** camera Setup ***')
    
        from sys import implementation
        print(implementation)

        mylib.setGCThreshold(GC_THRESHOLD_SIZE)
        mylib.collectMemory()
        
        self.setupGlovecam=False
        self.setupSDFileSystem=False
        
        #
        # setup TFT
        #

        # SPI FOR TFT
        self.hspi = SPI(1, baudrate=HSPI_BAUDRATE, polarity=0, phase=0, sck=Pin(TFT_SPI_SCK), mosi=Pin(TFT_SPI_MOSI), miso=Pin(TFT_SPI_MISO))

        #
        # setup TFT Unit
        #
        self.tft = self.TFT_setup(self.hspi, TFT_DC, TFT_RESET, TFT_CS)
        self.tft.fill(self.tft.BLACK)
        msg = ESPCAM_VERSION
        self.tft.text((5, screen_pos_y), msg, self.tft.WHITE, terminalfont)
        msg = 'py:' + str(implementation[1]).replace(' ','')
        screen_pos_y += 8
        self.tft.text((5, screen_pos_y), msg, self.tft.WHITE, terminalfont)
        mylib.collectMemory()
        
        #
        # setup SD Card
        #
        screen_pos_y += 8
        self.tft.text((5, screen_pos_y), 'SD Setup', self.tft.WHITE,terminalfont )
        self.vspi = SPI(2, baudrate=VSPI_BAUDRATE, polarity=1, phase=0, sck=Pin(SD_SPI_SCK), mosi=Pin(SD_SPI_MOSI), miso=Pin(SD_SPI_MISO))
        self.sd = self.SD_setup(self.vspi, SD_CS)
        if self.sd is None:
            self.stat_sd = False
        else:
            self.stat_sd = True

        #
        #
        # setup WiFi and NTP
        #
        mylib.collectMemory()
        screen_pos_y += 8
        self.tft.text((5, screen_pos_y), 'Wifi Connect', self.tft.WHITE,terminalfont )
        mylib.wlan_connect(SSID, PASS)   
        self.stat_ntp = mylib.ntp_setup()
        mylib.collectMemory()
        
        screen_pos_y += 8
        if self.stat_ntp:
           self.tft.text((5, screen_pos_y), 'NTP Setup OK', self.tft.WHITE,terminalfont )
        else:
           self.tft.text((5, screen_pos_y), 'NTP Setup Error', self.tft.WHITE,terminalfont )
        mylib.collectMemory()
        
        screen_pos_y += 8
        mylib.collectMemory()
        if self.stat_sd and self.stat_ntp:
            if mylib.setupSDFileSystem(self.sd):
                self.tft.text((5, screen_pos_y), 'SD Setup OK', self.tft.WHITE,terminalfont )
                setupSDFileSystem=True
            else:
                setupSDFileSystem=False
                self.tft.text((5, screen_pos_y), 'SD Setup Error', self.tft.WHITE,terminalfont )
        else:
            print('Initialization failed, so skip setupSDFileSystem()')
        mylib.collectMemory()
        
        dt = mylib.getLocalTimeJST()
        timeStamp = '{:d}/{:02d}/{:02d} {:02d}:{:02d}'.format(dt[0],dt[1],dt[2],dt[3],dt[4])
        screen_pos_y += 8
        self.tft.text((5, screen_pos_y), 'NOW:' + timeStamp, self.tft.WHITE,terminalfont)

        #
        # setup GroveCAM
        #
        screen_pos_y += 8
        self.uart = UART(1, CAM_UART_HIGH_SPEED)
        self.uart.init(CAM_UART_HIGH_SPEED, bits=8, parity=None, stop=1, tx=CAM_TX, rx=CAM_RX)
        self.grovecam = GroveCAM(self.uart)
        status = self.grovecam.setup()
        if status:
           self.tft.text((5, screen_pos_y), 'Camera Setup OK', self.tft.WHITE,terminalfont)
           self.stat_glovecam = True
        else:
           self.tft.text((5, screen_pos_y), 'Camera Setup Error', self.tft.WHITE,terminalfont)
           self.stat_glovecam = False
        mylib.collectMemory()
        
        if self.stat_sd and self.stat_ntp and self.stat_glovecam:
            screen_pos_y += 8
            self.tft.text((5, screen_pos_y), 'Ready! Take to a Photo', self.tft.WHITE,terminalfont )
            self.shutter = Pin(SHUTTERBUTTON, Pin.IN)  # 36 is assigned for ShutterButton
            self.humanSensor = Pin(HUMANSENSOR, Pin.IN)  # 35 is assigned for HumanSensor
        else:
            screen_pos_y += 8
            self.tft.text((5, screen_pos_y), 'Error in Setup', self.tft.WHITE,terminalfont )
        return self.stat_sd and self.stat_ntp and self.stat_glovecam
    
    #-----------------------------------------
    #
    # mainLoop
    #
    def mainLoop(self):

       lastPhotoTakeTime = 0
    
       mylib.collectMemory()
    
       # setup CRON
       self.setupCRON()
    
       # setup IRQ(shutter, humanSensor)
       self.setupIRQ()
    
       msg = 'ESP32 WiFi Camera Started(' + ESPCAM_VERSION + ')'
       print('*** main loop start ***')
       print(msg)
       status_code = lineBOT.postText(LINE_TOKEN, msg)
       if status_code == 200:
             print('POST to LineBOT OK')
       elif status_code == 429:   # 429 is 'Too Many Requests'
             print('LineBOT API Error')
             print('Too Many Requests')
       else:
             print('Error in lineBOT.postText')
             print('status[{:03d}]'.format(status_code))
    
       while True:
          #print('.',end='')
          utime.sleep(WAITTIME_IN_MAINLOOP)
    
          if self.shutterPressed:
              currentTime = utime.time()
              print(mylib.getTimeStampJST(enableSecond=True))
              if (currentTime - lastPhotoTakeTime) < NONRESPONSIVETIME_FOR_BUTTON :
                  print('avoid too many take photo')
                  self.shutterPressed = False
              else:
                  print('take a photo because the shutter button was pressed')
                  self.deleteIRQ()
                  status_code = lineBOT.postText(LINE_TOKEN, 'pressed shutter button')
                  if status_code == 200:
                      print('POST to LineBOT OK')
                  elif status_code == 429:   # 429 is 'Too Many Requests'
                      print('LineBOT API Error')
                      print('Too Many Requests')
                  else:
                      print('LineBOT API Error')
                      print('status[{:03d}]'.format(status_code))

                  self.takePictureAndUpload()
                  lastPhotoTakeTime = currentTime
                  self.shutterPressed = False
                  self.setupIRQ()
                  status_code = lineBOT.postText(LINE_TOKEN, 'mem:' + mylib.collectMemory())
                  print('mem:' + mylib.collectMemory())
                  mylib.collectMemory()
    
          if self.sensorDetected:
              currentTime = utime.time()
              print(mylib.getTimeStampJST(enableSecond=True))
              if (currentTime - lastPhotoTakeTime) < NONRESPONSIVETIME_FOR_HUMAN_SENSOR :
                  print('avoid rensya form sensor')
                  self.sensorDetected = False
              else:
                  print('take a photo because the sensor detects some obj.')
                  status_code = lineBOT.postText(LINE_TOKEN, 'sensor detection')
                  if status_code == 200:
                      print('POST to LineBOT OK')
                  elif status_code == 429:   # 429 is 'Too Many Requests'
                      print('LineBOT API Error')
                      print('Too Many Requests')
                  else:
                      print('LineBOT API Error')
                      print('status[{:03d}]'.format(status_code))

                  self.deleteIRQ()
                  for i in range(NOFPHOTOINDETECT):
                      self.takePictureAndUpload() # take N photos
                  lastPhotoTakeTime = currentTime
                  self.sensorDetected = False
                  self.setupIRQ()
                  memSize = mylib.collectMemory()
                  print('mem:' + memSize)
                  status_code = lineBOT.postText(LINE_TOKEN, 'mem:' + memSize)
                  mylib.collectMemory()
                  if status_code != 200:
                      print('Error in lineBOT.postText')
                      print('status[{:03d}]'.format(status_code))
    
          self.checkAndRunCRON()
    
    
    
    #---------------------------------
    #  Define for CRON Service
    #
    def exec1MJobs(self):
        print('-------------1M-----')
        print(mylib.collectMemory())
    
    def exec3MJobs(self):
        print('-------------3M-----')
        print('no operation')
    
    def exec5MJobs(self):
        print('-------------5M-----')
        print('no operation')
    
    def exec10MJobs(self):
        print('-------------10M-----')
        status_code = lineBOT.postText(LINE_TOKEN, 'mem:' + mylib.collectMemory())
        print(mylib.collectMemory())

    
    def exec30MJobs(self):
        print('-------------30M-----')
        # execute as time lapse
        print('take a photo by self timer(every 30min)')
        status_code = lineBOT.postText(LINE_TOKEN, 'take a photo by self timer(every 30min)')
        self.shutterPressed = True  # press shutter button by self timer
    
    def takePictureAndUpload(self, uploadMessage=None):
    
        # take Picture and save to tmp File
        mylib.collectMemory()
        fileName = mylib.getPhotoFileNameWithPath('jpg')
        state = self.grovecam.takePictureAndSaveToFile(fileName)
    
        if state == False:
            print('Error in takeing a photo')
            return False
        else:
            print('photo is saved: ' + fileName)
        print('taking a photo ok, upload photo to CloudService')
        print(mylib.reportMemory())  # for debug
    
        # upload picture to Cloudinary Server
        mylib.collectMemory()
        s = utime.ticks_ms()   # for time measurement
        (status_code, response) = cloudinaryUploader.uploadPhoto(fileName,CLOUD_NAME, API_KEY, API_SECRET)
        e = utime.ticks_ms()   # for time measurement    
        diff = utime.ticks_diff(e, s)
        print("upload photo takes:{:d}(ms)".format(diff))
        if status_code != 200:
            print('Error in uploading a photo to the Cloud Album Service')
            print('StatusCode:[{:d}]'.format(status_code))
            return False
    
        print('uploading photo is completed')
        dt = mylib.getLocalTimeJST()
        timeStamp = '{:d}/{:02d}/{:02d} {:02d}:{:02d}'.format(dt[0],dt[1],dt[2],dt[3],dt[4])
        if uploadMessage == None:
            uploadMessage = 'Photo is Uploaded'
        uploadMessage =  uploadMessage + ' (' + timeStamp + ')'
        photoURL = response['secure_url']
        prevURL = cloudinaryUploader.getResizeURL(photoURL)
        print('access url(org):' + photoURL)
        print('access url(prev):' + prevURL)
        mylib.collectMemory()
        status_code = lineBOT.postImage(LINE_TOKEN, photoURL, prevURL, uploadMessage)

        if status_code == 200:
            print('POST to LineBOT OK')
        elif status_code == 429:   # 429 is 'Too Many Requests'
            print('Error in lineBOT.postImage')
            print('LineBOT API Error')
            print('Too Many Requests')
            return False
        else:
            print('Error in lineBOT.postImage')
            print('LineBOT API Error')
            print('status[{:03d}]'.format(status_code))
            return False

        return True
    
    
    def cb_shutterButton(self, p):
        self.shutterPressed = True
        print('Button')
    
    def cb_sensor(self, p):
        self.sensorDetected = True
        print('Detected')
    
    def setupIRQ(self):
       self.shutter.irq(trigger = Pin.IRQ_FALLING, handler = self.cb_shutterButton)
       self.humanSensor.irq(trigger = Pin.IRQ_RISING, handler = self.cb_sensor)
    
    def deleteIRQ(self):
       self.shutter.irq(None)
       self.humanSensor.irq(None)
   
    
    def setupCRON(self):
    
       (year, mon, mday, hour, min, sec, wday, yday) = mylib.getLocalTimeJST()
       sec = 0
    
       # 3MinNext
       adjMin = int(min / 3) * 3 + 3
       self.cron3MinNext = utime.mktime((year, mon, mday, hour, adjMin , sec, wday, yday))
    
       # 5MinNext
       adjMin = int(min / 5) * 5 + 5
       self.cron5MinNext = utime.mktime((year, mon, mday, hour, adjMin , sec, wday, yday))
    
       # 10MinNext
       adjMin = int(min / 10) * 10 + 10
       self.cron10MinNext = utime.mktime((year, mon, mday, hour, adjMin , sec, wday, yday))
    
       # 30MinNext
       adjMin = int(min / 30) * 30 + 30
       self.cron30MinNext = utime.mktime((year, mon, mday, hour, adjMin , sec, wday, yday))
    
    
    def checkAndRunCRON(self):
    
        (year, month, mday, hour, minute, second, weekday, yearday) = mylib.getLocalTimeJST()
        if self.lastMin == minute :
            return   # no need to execute following codes
        else:
            print(mylib.getTimeStampJST(enableSecond=True))
     
        currentTime = mylib.getLocalTimeJSTInSec()
     
        if self.lastMin != minute :
              self.exec1MJobs()
     
        if currentTime >= self.cron3MinNext:
              self.cron3MinNext += 3 * 60
              self.exec3MJobs()
     
        if currentTime >= self.cron5MinNext:
              self.cron5MinNext += 5 * 60
              self.exec5MJobs()
     
        if currentTime >= self.cron10MinNext:
              self.cron10MinNext += 10 * 60
              self.exec10MJobs()
     
        if currentTime >= self.cron30MinNext:
              self.cron30MinNext += 30 * 60
              self.exec30MJobs()
     
        self.lastMin = minute
    
    
    #---------------------------------------------
    #
    # Setup Devices(TFT, SD)
    #

    def TFT_setup(self, spi, dc, reset, cs):
    
        # setup TFT
        tft = TFT(spi=spi, aDC=dc, aReset=reset, aCS=cs)
        tft.initr()
        tft.rgb(True)
        tft.rotation(3)
        tft.fill(tft.BLACK)
        tft.text((0, 0), ESPCAM_VERSION, tft.WHITE, terminalfont)
        return tft
    
    def SD_setup(self, spi, cs):
    
        sd = None
        # setup SD card
        try:
            sd = SDCard(spi, Pin(cs))
        except Exception as e:
            print('Error in SDCard()!!')
            print(e)
            return None
        else:
            print('SD OK')
    
        # mount sd volume
        utime.sleep(0.1)
        uos.mount(sd, '/sd')
        utime.sleep(0.1)
        uos.listdir('/sd')
        #utime.sleep(0.1)
        #ls('/sd')
        return sd


