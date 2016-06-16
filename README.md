PiCapture.py
=====
#### Raspberry Pi camera helper script
PiCapture helps do a timelapse photo or video capture using your Raspberry Pi and a Pi camera module.

#### Usage:
 * Display help
   * `PiCapture.py -h`
 * Capture a photo every 5 seconds and display detailed logs
   * `PiCapture.py -t 5 -d dir -l`
 * Start a video capture at 5X speed and with video stabilization enabled
   * `PiCapture.py -v -vf 5 -vs`
<br><br>

#### Minimum requirements:
* Raspberry Pi Model A
* Pi camera module

#### Additional requirements:
 * [perceptualdiff](https://github.com/myint/perceptualdiff) : used to remove duplicate captured photos
   * To install on Raspberry Pi: `sudo apt-get install perceptualdiff`
 * [avconv](https://libav.org/documentation/avconv.html) : used to encode timelapse as video
   * `sudo apt-get install libav-tools`
<br><br>

#### To start capturing on Pi reboot:
* Edit crontab: `crontab -e`
* And add the command to run: `@reboot python PiCapture.py -t 5`
