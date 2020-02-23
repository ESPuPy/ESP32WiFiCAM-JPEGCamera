# ESP32WiFiCAM-JPEGCamera
figure <br><img src="fig/fig1.jpg" width=200>

ESP32 WiFi Camera application has the following functions.

1. take pictures in VGA size and JPEG format
1. save pictures to the SD Memory card
1. upload pictures to the Cloudinary Album Service that is a cloud service
1. notify users using LINE BOT API

Following parts are used

|parts type|parts name|
----|----
|MicroController|ESP32|
|Camera Unit|Grove Serial Camera Kit|
|Monitor|1.8inch TFT LCD(ST7735)|
|Memory|SD Memory Card|

ESP32WiFiCAM is implemented in MicroPython

The following drivers are required to execute this application.

1. sdcard.py<br>https://github.com/micropython/micropython/tree/master/drivers/sdcard
1. ST7735.py<br>https://github.com/boochow/MicroPython-ST7735
1. terminalfont.py<br>https://github.com/GuyCarver/MicroPython/tree/master/lib

All files are subject to MIT license.
