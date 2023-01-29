import os
import subprocess
import glob
import hashlib
import time
import pickle
import platform

#output_folder = 'Z:/temp/ffmpeg_temp/output/'
output_folder = '/mnt/server_drive/output/' #linux
#tmp_folder = 'Z:/temp/ffmpeg_temp/'
tmp_folder = '/mnt/server_drive/' #linux
#Parameters
CleanTemp = False
CleanInput = False
#ffmpeg parameters
quality_level = 30
preset_level = 5
#mkvMerge
AudioLang = '--language 0:ja'
SubTitlesLang = '--language 0:en'
VideoLang = '--language 0:ja'
TrackOrder = '--track-order 0:0,1:0,2:0'

def buildFFmpegCommandAV1(inputFile,framerate,outputFile,Force):
    Overwrite = ''
    if Force:
        Overwrite = ' -y '
    dirname = os.path.dirname(__file__)
    commands_list = f'{dirname}/ffmpeg -r {framerate} {Overwrite} -i "{inputFile}" -c:v libsvtav1 -crf {quality_level} -g 240 -pix_fmt yuv420p10le -preset {preset_level} -svtav1-params tune=0:film-grain=8:fast-decode=0:enable-overlays=1:scd=1 "{outputFile}"'
    print('DEBUG: '+commands_list)
    return commands_list
def buildMKVMerge(inputFileSub,inputFileAudio,inputFileVideo,inputChapters,outputFileVideo):
    SubTitlesStr = ''
    if inputFileSub != 'none':
        SubTitlesStr = f'{SubTitlesLang} "{inputFileSub}"'
    ChaptersStr = ''
    if inputChapters != 'none':
        ChaptersStr = f'--chapter-language en --chapters "{inputChapters}"'
    if platform.system() == 'Windows':
        mkvMerge = 'mkvmerge\\mkvmerge'
    else:
        mkvMerge = 'mkvmerge'
    commands_list = f'{mkvMerge} --output "{outputFileVideo}" {VideoLang} --default-track 0:yes "{inputFileVideo}" {AudioLang} "{inputFileAudio}" {SubTitlesStr} {ChaptersStr} {TrackOrder}'
    print(f'DEBUG: {commands_list}')
    return commands_list

def runProcess(cmds):
    if subprocess.run(cmds, shell=True).returncode == 0:
        print ("Process exit successfully")
    else:
        print ("There was an error launching process")

def GetFramesCount(InputFile):
    dirname = os.path.dirname(__file__)
    if platform.system() == 'Windows':
        OSSeparator = '\\'
    else:
        OSSeparator = '/'
    proc = subprocess.Popen(f'{dirname}{OSSeparator}ffprobe -v error -select_streams v:0 -count_packets -show_entries stream=nb_read_packets -of csv=p=0 "{InputFile}"',stdout=subprocess.PIPE, shell=True)
    line = proc.stdout.readline()
    return line.decode('utf-8').rstrip()

def ReadInfoData(fileName):
    with open(fileName+'.pkl', 'rb') as f:
        read_dict = pickle.load(f)
        return read_dict

if __name__== '__main__':
    if platform.system() == 'Windows':
        OSSeparator = '\\'
    else:
        OSSeparator = '/'
    while True:
        #getting input video files from folder
        videoFilesArr = []
        for file in glob.glob(tmp_folder+"*.txt"):
            videoFilesArr.append(os.path.basename(file))
            if len(videoFilesArr)==0:
                exit()
    
        for VideoFile in videoFilesArr:                   
            outFileName = os.path.splitext(VideoFile)[0]
            inputImgFolder = os.path.splitext(outFileName)[0]
            #Load parameters
            VideoDataInfo = ReadInfoData(tmp_folder+outFileName)
            FileOverwrite = False
            if not VideoDataInfo:
                print('Error: cant read data info')
                print(VideoDataInfo)
                exit()
            #Delete file to prevent other process to launch same instance (still have race condition issue, but very rare)
            if os.path.exists(tmp_folder+VideoFile) == True:
                os.remove(tmp_folder+VideoFile)
            
            runProcess(buildFFmpegCommandAV1(tmp_folder+inputImgFolder+OSSeparator+'ffmpeg_%08d.webp',VideoDataInfo.get('FrameTime')[0],tmp_folder+os.path.splitext(outFileName)[0]+'.mkv',FileOverwrite)) #Video first pass
            print('FILE: '+VideoFile)
            #Check file at least for missing frames before merge
            if VideoDataInfo.get('FrameCount')[0] != GetFramesCount(tmp_folder+os.path.splitext(outFileName)[0]+'.mkv'):               
                f = open(f'{tmp_folder+outFileName}.error','w')
                f.close()
                print('Error: mismatch frame count')
                #something wrong
                exit()

            #Merge
            if VideoDataInfo.get('ChaptersFile')[0]:
                ChaptersPath = tmp_folder+outFileName+'.xml'
            else:
                ChaptersPath = 'none'
            if VideoDataInfo.get('SubtitlesFile')[0] != 'none':
                SubtitlesPath = tmp_folder+VideoDataInfo.get('SubtitlesFile')[0]
            else:
                SubtitlesPath = 'none'            
            runProcess(buildMKVMerge(SubtitlesPath,tmp_folder+VideoDataInfo.get('AudioFile')[0],tmp_folder+os.path.splitext(outFileName)[0]+'.mkv',ChaptersPath,output_folder+os.path.splitext(outFileName)[0]+'.mkv'))

            #cleanup
            #tmp
            if CleanTemp:
                if os.path.exists(tmp_folder+VideoDataInfo.get('AudioFile')[0]): #audio
                    os.remove(tmp_folder+VideoDataInfo.get('AudioFile')[0])
                if os.path.exists(tmp_folder+outFileName+'.xml'): #chapters information
                    os.remove(tmp_folder+outFileName+'.xml')
                if os.path.exists(tmp_folder+VideoDataInfo.get('SubtitlesFile')[0]): #sub
                    os.remove(tmp_folder+VideoDataInfo.get('SubtitlesFile')[0])
                if os.path.exists(tmp_folder+inputImgFolder): #frames
                    os.remove(tmp_folder+inputImgFolder+'\\*.webp')
            #input
            if CleanInput:
                if os.path.exists(tmp_folder+VideoFile): #video
                    os.remove(tmp_folder+VideoFile)

            if os.path.exists(f'{tmp_folder+outFileName}.error'): #error file
                os.remove(f'{tmp_folder+outFileName}.error')
            print (f"Converting file: {os.path.splitext(outFileName)[0]} completed")
            break

        videoFilesArr.clear()
        time.sleep(60)
        #exit() #DEBUG
