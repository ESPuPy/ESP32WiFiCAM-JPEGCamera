#-------------------------------------------
#
#    ESP32 WiFi Camera (Grove Serial Camera Version)
#    ESP32WiFiCAM-JPEGCamera
#
#    file:main.py
#   

from ESP32WiFiCAM import ESP32WiFiCAM

camera = ESP32WiFiCAM()

if camera.setup():
    camera.mainLoop()
else:
    print("Error in setup CameraSystem")



