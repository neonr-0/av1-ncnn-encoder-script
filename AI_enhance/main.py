import os
import subprocess
import glob
import socket
import tqdm
import pickle
import hashlib
import time
import numpy as np
from pathlib import Path
#from joblib import Parallel, delayed
from threading import Thread

#Paths to apps
ffmpeg = "ffmpeg"
ffprobe = 'ffprobe'
mkvExtract = "./mkvmerge/mkvextract"
realesrgan = "./realesrgan-ncnn/realesrgan-ncnn-vulkan"
#Paths to files
input_folder = './input/'
output_folder = './output/'
tmp_folder = './tmp/'
tmp_img_folder = './tmp_img/'
#ffmpeg parameters
video_cmd_line = '' #by default it's empty but if you need you can add to arguments (example:-vf crop=480:264:0:50)
audio_cmd_line = '-c:a libfdk_aac -vbr 4 -map 0:a:0' #you can change if you want other codec or parameters to use | '-c:a copy -map 0:a:0' - don't convert but extract audio track
#audio_cmd_line = '-c:a copy' #uncomment this if you want to keep original audio
audio_file_type = '.aac'
#realesrgan parameters
scale_ratio = 2 # 1-4
downsscale_ratio = 2 # 1-4
ncnn_model = 'realesr-animevideov3-x2' # realesrgan-x4plus-anime
tile_size = '512'
#Options
thread_count = 6 # sending threads
FastFirstPass = True # making png images instead of webp at video decoding stage (faster but takes more drive space)
DeleteInput = False

#network
host = "127.0.0.1"

port = 7890
BUFFER_SIZE = 4096

class OutSendThread(Thread):
    def __init__(self,ImgsPath,fileList):
        Thread.__init__(self)
        self.ImgsPath = ImgsPath
        self.fileList = fileList
    def run(self):
        for file in self.fileList:
            while SendFile(self.ImgsPath+file, file,True) == False:
                time.sleep(5)

def buildFFmpegCommandAudio(inputFile,outputFile):
    commands_list = f'{ffmpeg} -i "{inputFile}" {audio_cmd_line} -vn "{outputFile}{audio_file_type}"'
    return commands_list
def buildFFmpegCommandSub(inputFile,outputFile):
    commands_list = f'{ffmpeg} -i "{inputFile}" -vn -an -codec:s copy "{outputFile}.sup"'
    return commands_list

def buildMKVExtractCommandChapters(inputFile,outputFile):
    commands_list = f'{mkvExtract} "{inputFile}" chapters "{outputFile}.xml"'
    return commands_list   

def buildFFmpegCommandRAW(inputFile,outputFolder,FastMode):
    if not FastMode:
        commands_list = f'{ffmpeg} -i "{inputFile}" -qscale:v 1 -qmin 1 -qmax 1 -vsync 0 -vcodec libwebp -lossless 1 -compression_level 1 -pix_fmt bgra "{outputFolder}ffmpeg_%08d.webp"'
    else:
        commands_list = f'{ffmpeg} -i "{inputFile}" {video_cmd_line} "{outputFolder}ffmpeg_%08d.png"' #fast mode
    return commands_list

def BuildNCNNCommand(inputFile,outputFile):
    commands_list = f'{realesrgan} -i "{inputFile}" -s {scale_ratio} -o "{outputFile}" -n {ncnn_model} -t {tile_size} -f webp -j 8:2:20 -r -d {downsscale_ratio}'
    return commands_list

def runProcess(cmds):
    if subprocess.run(cmds).returncode == 0:
        print ("Process exit successfully")
    else:
        print ("There was an error launching process")

def applyFilter(inputFolder,outputFolder):
    subprocess.run(BuildNCNNCommand(inputFolder[:-1],outputFolder))

def GetHashInfo(Path):
    with open(Path,"rb") as f:
        bytes = f.read() # read entire file as bytes
        readable_hash = hashlib.sha256(bytes).hexdigest()
        f.close()
        return readable_hash


def SendFileInfo(socket,fileName,fileSize,hashFile, imgFile = False):
    data = dict(filename = fileName, filesize = fileSize, isImgFile = imgFile, hash = hashFile)
    socket.send(pickle.dumps(data))

def SendFile(Path,fileName,isImgFile = False):
    #Getting size
    filesize = os.path.getsize(Path)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(10)
        s.connect((host,port))
        if isImgFile == False:
            SendFileInfo(s,fileName,filesize,GetHashInfo(Path))
        else:
            SendFileInfo(s,Path, filesize,GetHashInfo(Path), isImgFile)
        #Check if message sent
        recvBuf = s.recv(256)
        progress = tqdm.tqdm(range(filesize), f"Sending {fileName}", unit="B", unit_scale=True, unit_divisor=1024)
        with open(Path, "rb") as f:
            while True: #Read file        
                bytes_read = f.read(BUFFER_SIZE)
                if not bytes_read:
                    # file transmitting is done
                    break
                s.sendall(bytes_read)        
                progress.update(len(bytes_read))
        #Send EOF
        s.send(b'PYTHON_SPECIAL_EOF')
        recvBuf = s.recv(256) #Check if file is received   
        s.close() # close the socket
        if recvBuf == b'ok':
            #delete original
            if os.path.exists(Path):
                os.remove(Path)
            return True
        else:
            return False
    except socket.timeout as err:
        return False
    except:
        return False


def SendImages(Path,ListFiles):
    #Split job to amount of threads
    if thread_count <= 1:
        split_ListFiles = np.array_split(ListFiles, 1)
    else:
        split_ListFiles = np.array_split(ListFiles, thread_count)
    threads = []
    for filelist_chunk in split_ListFiles:
        newthread = OutSendThread(Path,filelist_chunk)
        newthread.start()
        threads.append(newthread)
    for t in threads:
        t.join()


def GetFramesCount(InputFile):
    proc = subprocess.Popen(f'{ffprobe} -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "{InputFile}"',stdout=subprocess.PIPE)
    line = proc.stdout.readline()
    return line.decode('utf-8').rstrip()
def GetFrameTime(InputFile):
    proc = subprocess.Popen(f'{ffprobe} -v 0 -of csv=p=0 -select_streams v:0 -show_entries stream=r_frame_rate "{InputFile}"',stdout=subprocess.PIPE)
    line = proc.stdout.readline()
    return line.decode('utf-8').rstrip()
def GetChaptersInfo(InputFile):
    proc = subprocess.Popen(f'{ffprobe} -v 0 -of csv=p=0 -select_streams v:0 -show_chapters "{InputFile}"',stdout=subprocess.PIPE)
    line = proc.stdout.readline()
    return line.decode('utf-8').rstrip()

def GetSubtitlesInfo(InputFile):
    proc = subprocess.Popen(f'{ffprobe} -v 0 -select_streams s -show_entries stream=disposition=forced,stream_tags=language,codec_name -of "csv=p=0" "{InputFile}"',stdout=subprocess.PIPE)
    line = proc.stdout.readline()
    return line.decode('utf-8').rstrip()

def WriteInfoData(inputDict,fileName):
    with open(fileName+'.pkl', 'wb') as f:
        pickle.dump(inputDict, f) 

if __name__== '__main__':
    #Create tmp folders
    if not os.path.exists(tmp_folder):          
         os.mkdir(tmp_folder)
    if not os.path.exists(tmp_img_folder):          
         os.mkdir(tmp_img_folder)
    if not os.path.exists(input_folder):          
         os.mkdir(tmp_img_folder)   
    #getting video files from input folder
    VideoFilesArr = []
    for file in glob.glob(input_folder+"*.mkv"):
        VideoFilesArr.append(os.path.basename(file))
    for file in glob.glob(input_folder+"*.mp4"):
        VideoFilesArr.append(os.path.basename(file))
    for file in glob.glob(input_folder+"*.flv"):
        VideoFilesArr.append(os.path.basename(file))
    for file in glob.glob(input_folder+"*.mpg"):
        VideoFilesArr.append(os.path.basename(file))
    for file in glob.glob(input_folder+"*.avi"):
        VideoFilesArr.append(os.path.basename(file))
    firstPassFileType = '.webp'
    if FastFirstPass:
        firstPassFileType = '.png'
    else:
        firstPassFileType = '.webp'
    for inputVideoFileName in VideoFilesArr:
        #VideoInformation
        VideoFileInfo = {"FrameCount":[],"FrameTime":[],"SubtitlesFile":[],"ChaptersFile":[],"AudioFile":[]}
         #Audio encoder
        if os.path.exists('AudioOk.done') == False:
            print('Converting audio')
            VideoFileInfo['AudioFile'].append(inputVideoFileName+audio_file_type)
            runProcess(buildFFmpegCommandAudio(input_folder+inputVideoFileName,tmp_folder+inputVideoFileName)) #Audio first
            while SendFile(tmp_folder+inputVideoFileName+audio_file_type,inputVideoFileName+audio_file_type) == False: #Send audio file
                time.sleep(5)
            f = open('AudioOk.done','w')
            f.close()    
        else:
            print('Audio already sent, skipping')
        
         #Export subtitles
        if os.path.exists('SubsOk.done') == False:
            subtitleFileType = 'none'
            subtitleType = GetSubtitlesInfo(input_folder+inputVideoFileName)
            if 'hdmv_pgs_subtitle' in subtitleType:
                subtitleFileType = '.sup'
            if 'ass' in subtitleType:
                subtitleFileType = '.ass'
            if 'subrip' in subtitleType:
                subtitleFileType = '.srt'
            if subtitleFileType != 'none':
                print('Export subtitles')
                runProcess(buildFFmpegCommandSub(input_folder+inputVideoFileName,tmp_folder+inputVideoFileName))  
                while SendFile(tmp_folder+inputVideoFileName+subtitleFileType, inputVideoFileName+subtitleFileType) == False: #Send subtitles file
                    time.sleep(5)
                VideoFileInfo['SubtitlesFile'].append(inputVideoFileName+subtitleFileType)
            else:
                VideoFileInfo['SubtitlesFile'].append(subtitleFileType)
            f = open('SubsOk.done','w')
            f.close() 
            
            
        else:
            print('subtitles already sent, skipping')

         #Export chapters
        if os.path.exists('ChapOk.done') == False:
            #Add additional data      
            VideoFileInfo['FrameCount'].append(GetFramesCount(input_folder+inputVideoFileName))
            VideoFileInfo['FrameTime'].append(GetFrameTime(input_folder+inputVideoFileName))
            if GetChaptersInfo(input_folder+inputVideoFileName):
                print('Export chapters')
                runProcess(buildMKVExtractCommandChapters(input_folder+inputVideoFileName,tmp_folder+inputVideoFileName))
                while SendFile(tmp_folder+inputVideoFileName+'.xml', inputVideoFileName+'.xml') == False: #Send chapters file
                    time.sleep(5)
                f = open('ChapOk.done','w')
                f.close()
                VideoFileInfo['ChaptersFile'].append(True)
            else:
                VideoFileInfo['ChaptersFile'].append(False)
            WriteInfoData(VideoFileInfo,inputVideoFileName)    
            while SendFile(inputVideoFileName+'.pkl', inputVideoFileName+'.pkl') == False: #Send data file
                time.sleep(5)   
        else:
            print('Chapters already sent, skipping') 
        
         #Prepare for filter
        if os.path.exists('FFMpegOk.done') == False:
            print('Prepare filter')
            runProcess(buildFFmpegCommandRAW(input_folder+inputVideoFileName,tmp_img_folder,FastFirstPass)) #make sequence of images
            f = open('FFMpegOk.done','w')
            f.close()
        else:
            print('Filter already prepared, skipping') 
         #Apply filter
        if not os.path.isdir(os.path.splitext(inputVideoFileName)[0]):
            os.mkdir(os.path.splitext(inputVideoFileName)[0])
        if os.path.exists('FilterOk.done') == False:
            print('Launch filter')
            applyFilter(tmp_img_folder,os.path.splitext(inputVideoFileName)[0])
            #Check if job done
            while True:
                ffmpegImgFiles = []
                for file in glob.glob(tmp_img_folder+"*"+firstPassFileType):
                    ffmpegImgFiles.append(os.path.basename(file))
                if not ffmpegImgFiles:
                    break
                else:
                    print('Filter error')
                    time.sleep(1)
                    applyFilter(tmp_img_folder,os.path.splitext(inputVideoFileName)[0])
                ffmpegImgFiles.clear()
            f = open('FilterOk.done','w')
            f.close()
        else:
            print('Filter already finished, skipping') 
        imgFiles = []
        filteredPath = os.path.splitext(inputVideoFileName)[0]+'/'
        for file in glob.glob(glob.escape(filteredPath)+"*.webp"):
            imgFiles.append(os.path.basename(file))
            if len(imgFiles)==0:
                break
        #Send Images async MT
        print('Sending images')
        SendImages(filteredPath,imgFiles)
        
        #CleanUp
        if os.path.exists('AudioOk.done'): #audio
            os.remove('AudioOk.done')
        if os.path.exists('SubsOk.done'): #subtitres
            os.remove('SubsOk.done')
        if os.path.exists('ChapOk.done'): #chapters
            os.remove('ChapOk.done')
        if os.path.exists('FFMpegOk.done'): #FFmpeg Imgs
            os.remove('FFMpegOk.done')
        if os.path.exists('FilterOk.done'): #Filter
            os.remove('FilterOk.done')
        
        #Send completing command
        if os.path.exists(inputVideoFileName+'.txt') == False:
            f = open(inputVideoFileName+'.txt','wb')
            f.write(b'OK\n')  
            f.close()
            while SendFile(inputVideoFileName+'.txt', inputVideoFileName+'.txt',False) == False:
                time.sleep(5)  
        
        #delete original
        if DeleteInput:  
            if os.path.exists(input_folder+inputVideoFileName) == True:
                os.remove(input_folder+inputVideoFileName)
        #delete folder
        if os.path.exists(filteredPath):          
            os.removedirs(filteredPath)
   
        print (f"Video file finished uploading: {inputVideoFileName}")
    print ("Task done")
