#-------------------------------------------
#
#    ESP32 WiFi Camera (Grove Serial Camera Version)
#    ESP32WiFiCAM-JPEGCamera
#
#    file:lineBOT.py
#   

#------------------------------
#
# funcs for POST to lineBOT
#
from urequests import Response 
from urequests import post

#
LINEBOTURL = "https://api.line.me/v2/bot/message/broadcast"

# JSON TEMPLATE FOR POST Text
POSTTEXT_JSONTMPL = '{"messages": [{"type": "text", "text": "__MSG__"}]}'

# JSON TEMPLATE FOR POST Text and Images
POSTIMAGE_JSONTMPL = '{"messages": [{"type": "text", "text": "__MSG__"}, {"type": "image", "originalContentUrl": "__ORGURL__", "previewImageUrl": "__PREVURL__"}]}'

def postText(token, message):
    body = POSTTEXT_JSONTMPL.replace("__MSG__", message)
    body = bytes(body.encode('utf-8'))
    headers = { 'Content-Type' : 'application/json', 'Authorization' : 'Bearer ' + token }
    resp = post(LINEBOTURL, headers = headers, data = body)
    statusCode = resp.status_code
    resp.close()
    return statusCode

def postImage(token, photoOrgURL, photoPrevURL, message="New Photo"):
    body = POSTIMAGE_JSONTMPL.replace("__MSG__", message)
    body = body.replace("__ORGURL__", photoOrgURL)
    body = body.replace("__PREVURL__", photoPrevURL)
    body = bytes(body.encode('utf-8'))
    headers = { 'Content-Type' : 'application/json', 'Authorization' : 'Bearer ' + token }
    resp = post(LINEBOTURL, headers = headers, data = body)
    statusCode = resp.status_code
    resp.close()
    return statusCode

