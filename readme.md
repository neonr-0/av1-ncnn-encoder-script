# Distributed AV1 encoder 

This script encode to AV1 with RealESRGAN Image Processing, mainly focused to remove noise, improve quality and reduce size of video.
This script can work on several machines to help with distributing load. It doesn't have encryption so I will recommend use it in your local network.

Here is 3 scripts:

* AI Enhance: Extracting audio and encoding audio, subtitles, chapter information and sending it to server
* Storage Server
* AV1 Encoder

## AI Enhance Script

### Requirements:

- Vulkan capable GPU with 2GB+ VRAM
- Storage space to hold all frames in video

To use this script you need GPU with Vulkan support on it (works on latest intel iGPU too), there are no support for CPU processing, CPU load will be only read input images and to compress output images with WebP file format. 

[RealESRGAN](https://github.com/neonr-0/Real-ESRGAN-ncnn-vulkan) was slightly modified to apply downscaling and remove original file. 

This script doing:
1. Extracting and converting audio
2. Extracting subtitles and chapters information.
3. Extracting frames.
4. Processing frames using RealESRGAN.
5. Sending everything to storage server

To hold 25min of video frames you need around 25-50GB of storage space using WebP frame extraction method, using PNG can be little bit more due to fact it's lossless.

This method of encoding uses a lot of writing so be careful using SSD due to high amount of writing on device. I will recommend to use HDD or RAM drive.

## Storage Server Script

This is just simple TCP server to get all data from AI Enhance script, so make sure you have enough storage to hold data for AV1 encoding machines.

## AV1 Encoder

This script focused only on CPU encoding and don't rely on GPU encoding, for better ratio of encoding speed/NCNN frames processing I will recommend to tune it. By default it's preset 0 (extremely slow). Check [Performance](#Performance) header.

# Example

input 1920x1080 PNG, model: realesr-animevideov3-x2, scale 2x, downscale 2x
|input|output|
|---|---|
|![input](./examples/input.png)|![output](./examples/out_scale_2x_2x.png)|
|200%|200%|
|![input](./examples/in_1.png)|![output](./examples/out_1.png)|
|![input](./examples/in_2.png)|![output](./examples/out_2.png)|
|![input](./examples/in_3.png)|![output](./examples/out_3.png)|

# AI Enhance Script 

ReasESRGAN parameters:

|Option|Value|Description|
|---|---|---|
|noise_level|0-3|Filter| 
|scale_ratio|1-4|Upscaling ratio|
|downsscale_ratio|1-4|Downscaling ratio, using value 1 ignoring downscaling step|
|ncnn_model|realesr-animevideov3-x2 (x3/x4)|Model to use (better use x4 for 4x upscaling|

Main settings
|Option|Value|Description|
|---|---|---|
|thread_count|1 or more|Amount of threads using to **send** frames|
|FastFirstPass|True/False|Use PNG  format at stage of extracting frames (affects performance)|
|DeleteInput|True/False|Delete input files after completion|

## Installation and Running

### Windows

1. Install [Python](https://www.python.org/downloads/) 3.8+
1. Make sure you have latest drivers installed
1. Download latest release of ai-enhance.zip
1. Unpack it into folder
1. Create folder input
1. Edit settings in **main.py** to fit your requirements
1. Launch start.bat

Check if paths to executables are correct

# Storage Server

Use this script to store all data for AV1 Encoder script.
You can edit path to store all data in **main.py**
```
#settings
store_folder = './tmp/' # path to store all data 
server_port = 7890 # change if need
```

## Installation and Running

### Windows

1. Install [Python](https://www.python.org/downloads/) 3.8+
1. Set path and port if need
1. Launch **start.bat**

### Linux
1. Install Python
```
# Debian-based:
sudo apt install wget git python3 python3-venv
# Suse-based:
zypper in python3
```
2. Set path and port if need
2. Make sure you have rights to launch main.py and start.sh if not set it with **chmod +x start.sh**
2. Launch **start.sh**

# AV1 Encoder Script

You can launch this script in multiple instances if need due to not full utilization of all available cores.
You can edit paths to where is your data located in **main.py**
```
#settings
store_folder = './tmp/' # path to store all data 
server_port = 7890 # change if need
```
FFMPEG Settings:
|Option|Value|Description|
|---|---|---|
|quality_level|1 or more|AV1 encoder CRF value|
|preset_level|0-11|AV1 encoder preset|

Main Settings:
|Option|Value|Description|
|---|---|---|
|CleanTemp|True/False|Delete frames/audio/subtitles/etc|
|CleanInput|True/False|Delete encoded MKV after encoding (not merged video)|

MKVMerge Parameters:
|Option|Value|Description|
|---|---|---|
|AudioLang|any language present in MKVMerge|Audio track language|
|SubTitlesLang|any language present in MKVMerge|Subtitles language (if present)|
|VideoLang|any language present in MKVMerge|Video track language|

Make sure your paths for executables is correct (especially on linux platform)
```
output_folder = '/mnt/shared_drive/output/'
tmp_folder = '/mnt/shared_drive/tmp/'
```

## Installation and Running

### Windows

1. Install [Python](https://www.python.org/downloads/) 3.8+
1. Make sure you have network access to storage server (SMB)
1. Setup settings (make sure your have correct paths)
Make sure your paths for executables is correct (especially on linux platform)
```
output_folder = 'Z:/temp/ffmpeg_temp/'
tmp_folder = 'Z:/temp/output/'
```
1. Launch: **python main.py**

### Linux
1. Install Python and dependecies
```
# Debian-based:
sudo apt install wget git python3 python3-venv mkvtoolnix
# Suse-based:
zypper in python3 mkvtoolnix
```
2. Setup settings (make sure your have correct paths)
Make sure your paths for executables is correct (especially on linux platform)
```
output_folder = '/mnt/shared_drive/output/'
tmp_folder = '/mnt/shared_drive/tmp/'
```
2. Make sure you have network access to storage server (SMB/NFS)
2. Make sure you have rights to launch main.py if not set it with **chmod +x main.py**
2. Launch: **python3 main.py**

# Performance

## CPU performance

AV1 Encoding performance 

ffmpeg parameters: 
```ffmpeg -r 24000/1001 -i "ffmpeg_%08d.webp" -c:v libsvtav1 -crf 36 -g 240 -pix_fmt yuv420p10le -preset 0 -svtav1-params tune=0:film-grain=8:fast-decode=0:enable-overlays=1:scd=1 preset_0.mkv```

ffmpeg version N-109398-g826c6c3e10-g9651f873f8+2  

SVT-AV1 Encoder Lib v1.4.0-14-g98c69b5d **AVX2**
|CPU|FPS|Preset|
|---|---|---|
|2x Intel Xeon Gold 6130|0.2fps|Preset 0|
|2x Intel Xeon Gold 6130|0.7fps|Preset 1|
|2x Intel Xeon Gold 6130|1.3fps|Preset 2|
|2x Intel Xeon Gold 6130|4.3fps|Preset 3|
|2x Intel Xeon Gold 6130|7.9fps|Preset 4|
|2x Intel Xeon Gold 6130|11fps|Preset 5|
|2x Intel Xeon Gold 6130|20fps|Preset 6|
|2x Intel Xeon E5-2650 v4|0.2fps|Preset 0|
|2x Intel Xeon E5-2650 v4|0.7fps|Preset 1|
|2x Intel Xeon E5-2650 v4|1.0fps|Preset 2|
|2x Intel Xeon E5-2650 v4|2.1fps|Preset 3|
|2x Intel Xeon E5-2650 v4|3.8fps|Preset 4|
|2x Intel Xeon E5-2650 v4|6.8fps|Preset 5|
|2x Intel Xeon E5-2650 v4|11fps|Preset 6|

Due to fact SVT-AV1 encoder can't utilize all available cores you can launch up to 4x instances on Intel Xeon Gold 6130 so you can make 4 simultanious encoding processes.

---

ffmpeg version N-109587-gfc263f073e-20230112

SVT-AV1 Encoder Lib v1.4.1-5-g91832ee2 **AVX512**

|CPU|FPS|Preset|
|---|---|---|
|2x Intel Xeon Silver 4114|0.1fps|Preset 0|
|2x Intel Xeon Silver 4114|0.5fps|Preset 1|
|2x Intel Xeon Silver 4114|0.7fps|Preset 2|
|2x Intel Xeon Silver 4114|2.0fps|Preset 3|
|2x Intel Xeon Silver 4114|3.1fps|Preset 4|
|2x Intel Xeon Silver 4114|5.7fps|Preset 5|
|2x Intel Xeon Silver 4114|11fps|Preset 6|

## GPU performance
Real-ESRGAN-nccn performance (input 1920x1080 PNG, model: realesr-animevideov3-x2, scale 2x, downscale 2x, output 1920x1080 WebP):

|GPU|FPS|
|---|---|
|Intel Core i7-12700H iGPU|0.3fps|
|AMD RX480|1.01fps|
|NVIDIA 3060 Laptop GPU 140W|3.04fps|
|NVIDIA 3060|3.46fps|


