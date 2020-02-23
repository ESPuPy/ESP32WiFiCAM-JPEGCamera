# ESP32WiFiCAM-JPEGCamera

外観<br><img src="fig/fig1.jpg" width=200>

ESP32 WiFi Camera は以下の機能があります。

1. VGAサイズのJPEG画像を撮影
1. 撮影した画像データをSDカードメモリに保存
1. 撮影した画像データをクラウドアルバムサービス（Cloudinary Album Service）にアップロード
1. 撮影したことをLINE BOT APIを用いて通知、画像参照URLと共に送付することで、LINEアプリで画像確認可能

本カメラは以下のパーツで構成されています。

|デバイス種別|デバイス名|
----|----
|MicroController|ESP32|
|Camera Unit|Grove Serial Camera Kit|
|Monitor|1.8inch TFT LCD(ST7735)|
|Memory|SD Memory Card|

ESP32WiFiCAMはESP32上のMicroPythonで動作します。

本アプリを稼働させるには以下のドライバが必要です。URLを併記しますので取得して本アプリと同じディレクトリに置いてください。

1. sdcard.py<br>https://github.com/micropython/micropython/tree/master/drivers/sdcard
1. ST7735.py<br>https://github.com/boochow/MicroPython-ST7735
1. terminalfont.py<br>https://github.com/GuyCarver/MicroPython/tree/master/lib

本システムの概要説明は、[Interface 2020 4月号](https://interface.cqpub.co.jp/magazine/202004/) pp.70-79にも記載しています。併せてご参照ください。 本システムは開発時期、処理速度の関係により、MicroPython(V1.10)でテストしています。最新版のV1.20では未テストです。

すべてのファイル、ソースはMITライセンスに従っています。 All files are subject to MIT license.
