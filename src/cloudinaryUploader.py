#-------------------------------------------
#
#    ESP32 WiFi Camera (Grove Serial Camera Version)
#    ESP32WiFiCAM-JPEGCamera
#
#    file:cloudinaryUploader.py
#   
#
#
#
#   Photo uploader for Cloudinary Web Service
#   https://cloudinary.com/
#

import uos
import utime
from ubinascii import hexlify
from uhashlib import sha1
from urandom import random

import usocket
from ussl import wrap_socket
from urequests import Response 
import mylib


TMPL_CD = 'Content-Disposition: form-data; name="{:s}"'
TMPL_CD_FILE = 'Content-Disposition: form-data; name="file"; filename="{:s}"'
TMPL_CT_JPEG = 'Content-Type: image/jpeg'
CRLF = bytes((0x0d,0x0a))

EPOCH_2000_1_1 = 946684800  # offset value for change start Year(2001 -> 1970)

RESOURCE_TYPE = 'image'
CLO_URL_TEMPLATE = "https://api.cloudinary.com/v1_1/{:s}/{:s}/upload"

FILEBUFSIZE = 256


# for debug, enable memory report  
#DBG_MEMORY_REPORT = True
DBG_MEMORY_REPORT = False


def uploadPhoto(uploadFile, cloudName, apiKey, apiSecret, targetFolder=None):

    print("uploadPhoto")
    s = utime.ticks_ms()   # for time measurement
    mylib.collectMemory()
    #print(mylib.reportMemory())  # for debug
    if targetFolder is None:
        (year, month, mday, hour,min,sec,weekday,yearday) = mylib.getLocalTimeJST()
        targetFolder = "{:04d}{:02d}".format(year,month)
    params = {}
    params['api_key'] = apiKey
    params['timestamp'] = str(int(utime.time()) + EPOCH_2000_1_1) # adjust unix epoch time
    params['file'] = (uploadFile,None)        # load image at makeMultipartBody
    params['folder'] = targetFolder
    params['signature'] = makeSignature(params, apiSecret)
    (boundary,postBodyTMPFile) = makeMultipartBody(params)
    headers = {}
    headers['Content-Type'] = 'multipart/form-data; boundary={:s}'.format(boundary)
    url = CLO_URL_TEMPLATE.format(cloudName, RESOURCE_TYPE)
    e = utime.ticks_ms()   # for time measurement
    diff = utime.ticks_diff(e, s)
    print("create BodyPart takes:{:d}(ms)".format(diff))
    s = utime.ticks_ms()   # for time measurement
    resp = postBodyFromFile(url, file=postBodyTMPFile, headers=headers)
    status_code = resp.status_code
    postInfo = resp.json()
    resp.close()
    print("remove tmpfile:"+postBodyTMPFile)
    uos.remove(postBodyTMPFile)
    e = utime.ticks_ms()   # for time measurement
    diff = utime.ticks_diff(e, s)
    print("data transfer takes:{:d}(ms)".format(diff))
    return (status_code, postInfo)  


def makeMultipartBody(params):

    print("makeMultipartBody")
    mylib.collectMemory()
    #print(mylib.reportMemory())  # for debug
    uniq_str = sha1Hash(str(utime.time()*random()))
    bodyTMPfile = '/sd/' + 'tmp' + uniq_str[5:10] # make tmp file name (len:3+5)
    boundary = uniq_str[0:16]  # take string (len:16)
    fp = open(bodyTMPfile, 'wb')
    for key in params:
        fp.write(('--' + boundary).encode())
        fp.write(CRLF)
        value = params[key]

        if key == 'file':
            if len(value) == 1:
                file_name = value[0]
                file_body = None
            if len(value) == 2:
                (file_name, file_body) = value
            else:
                print("Error in makeMultipartBody")
                print("file entity illegal")
                fp.close()
                return None
  
            fp.write(TMPL_CD_FILE.format(file_name).encode())
            fp.write(CRLF)
            fp.write(TMPL_CT_JPEG)
            fp.write(CRLF * 2)
            if file_body is None:
                with open(file_name, "rb") as fp_body:
                    buffer=bytearray(FILEBUFSIZE)
                    while True:
                        if DBG_MEMORY_REPORT:
                           print(mylib.reportMemory())  # for debug
                        size = fp_body.readinto(buffer,FILEBUFSIZE)
                        if size == 0:
                            break
                        else:
                            fp.write(buffer,FILEBUFSIZE)
                    buffer=None
        else:
            fp.write(TMPL_CD.format(key).encode())
            fp.write(CRLF *2)
            if isinstance(value, str):
                fp.write(value.encode())
            else:
                print("Error in makeMultipartBody")
                print("entity is not string")
                fp.close()
                return None

        fp.write(CRLF)

    fp.write(('--' + boundary + '--').encode())
    fp.close()
    return (boundary, bodyTMPfile)


def sha1Hash(val):
    return str(hexlify(sha1(val).digest()),'utf-8')


def makeSignature(params,api_secret):
   params_kv = []
   for key in sorted(params.keys()):  # sort keys
      if key in ('api_key', 'file', 'signature'):
          continue   # exclude 'api_key','file'(and 'signature')
      else:
          params_kv.append("{:s}={:s}".format(key,str(params[key])))
   params_str = '&'.join(params_kv)
   return sha1Hash(params_str + api_secret)



#
# post HTTPS function 
# customized only for HTTPS POST and 
# post data read from spcified tmp file
#
# original source:
# https://github.com/micropython/micropython-lib/blob/master/urequests/urequests.py
# def request(method, url, data=None, json=None, headers={}, stream=None)
#
def postBodyFromFile(url, headers, file):

    print("postBodyFromFile")
    mylib.collectMemory()
    #print(mylib.reportMemory())  # for debug

    try:
        proto, dummy, host, path = url.split("/", 3)
    except ValueError:
        proto, dummy, host = url.split("/", 2)
        path = ""
    if proto == "https:":
        port = 443
    else:
        raise ValueError("Unsupported protocol: " + proto)

    if ":" in host:
        host, port = host.split(":", 1)
        port = int(port)

    ai = usocket.getaddrinfo(host, port, 0, usocket.SOCK_STREAM)
    ai = ai[0]

    s = usocket.socket(ai[0], ai[1], ai[2])
    try:
        s.connect(ai[-1])
        s = wrap_socket(s, server_hostname=host)
        s.write(b"%s /%s HTTP/1.0\r\n" % ('POST', path))
        if not "Host" in headers:
            s.write(b"Host: %s\r\n" % host)
        # Iterate over keys to avoid tuple alloc
        for k in headers:
            s.write(k)
            s.write(b": ")
            s.write(headers[k])
            s.write(b"\r\n")

        size = mylib.getFileSize(file)
        if size == None:
            raise ValueError("FileSize is None")
        s.write(b"Content-Length: %d\r\n" % size)
        s.write(b"\r\n")

        with open(file,'rb') as fp:            
            buffer=bytearray(FILEBUFSIZE)
            while True:
                if DBG_MEMORY_REPORT:
                   print(mylib.reportMemory())  # for debug
                size = fp.readinto(buffer,FILEBUFSIZE)
                if size == 0:
                     break
                else:
                    s.write(buffer,FILEBUFSIZE)
            buffer=None
        l = s.readline()
        l = l.split(None, 2)
        status = int(l[1])
        reason = ""
        if len(l) > 2:
            reason = l[2].rstrip()
        while True:
            l = s.readline()
            if not l or l == b"\r\n":
                break
            if l.startswith(b"Transfer-Encoding:"):
                if b"chunked" in l:
                    raise ValueError("Unsupported " + l)
            elif l.startswith(b"Location:") and not 200 <= status <= 299:
                raise NotImplementedError("Redirects not yet supported")
    except OSError:
        s.close()
        raise

    resp = Response(s)
    resp.status_code = status
    resp.reason = reason
    return resp


# create Resize URL
# for more information;
#   https://cloudinary.com/documentation/image_transformations#resizing_and_cropping_images
#
# resize photo size
#   original :(640 x 480) -> preview :(240 x 180)
#
#  org:  https://res.cloudinary.com/XXXXX/image/upload/v1547XX/kldmxXXX.jpg'
#                                                        v
#                                                        v
#  prev: https://res.cloudinary.com/XXXXX/image/upload/w_240/v1547XX/kldmxXXX.jpg'

def getResizeURL(url):

   FIXPATH = '/image/upload/'
   (preURL, postURL) = url.split(FIXPATH)
   resizedURL = preURL + FIXPATH + 'w_240/' + postURL  # resize to width:240
   return resizedURL

