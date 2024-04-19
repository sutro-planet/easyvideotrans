from audio_remove import audio_remove
from warning_file import WarningFile

import os
import copy
import json
from pytube import YouTube
from pytube.cli import on_progress
import stable_whisper
import srt
import re
from pygtrans import Translate
import requests
from tqdm import tqdm
from pydub import AudioSegment
import asyncio  
import edge_tts
from concurrent.futures import ThreadPoolExecutor
import datetime
from moviepy.editor import VideoFileClip

PROXY = "127.0.0.1:7890"
proxies = None
TTS_MAX_TRY_TIMES = 16

paramDictTemplate = {
    "proxy": "127.0.0.1:7890", # 代理地址，留空则不使用代理
    "video Id": "VIDEO_ID", # 油管视频ID
    "work path": "WORK_PATH", # 工作目录
    "download video": True, # [工作流程开关]下载视频
    "download fhd video": True, # [工作流程开关]下载1080p视频
    "extract audio": True, # [工作流程开关]提取音频
    "audio remove": True, # [工作流程开关]去除音乐
    "audio remove model path": "/path/to/your/audio_remove_model", # 去音乐模型路径
    "audio transcribe": True, # [工作流程开关]语音转文字
    "audio transcribe model": "medium.en", # [工作流程开关]英文语音转文字模型名称
    "srt merge": True, # [工作流程开关]字幕合并
    "srt merge en to text": True, # [工作流程开关]英文字幕转文字
    "srt merge translate": True, # [工作流程开关]字幕翻译
    "srt merge zh to text": True, # [工作流程开关]中文字幕转文字
    "srt to voice srouce": True, # [工作流程开关]字幕转语音
    "GPT-SoVITS url": "", # 不填写就是用edgeTTS，填写则为GPT-SoVITS 服务地址。简易不要用GPT-SoVITS
    "voice connect": True, # [工作流程开关]语音合并
    "audio zh transcribe": True, # [工作流程开关]合成后的语音转文字
    "audio zh transcribe model": "medium" # 中文语音转文字模型名称
}

def create_param_template(path):
    with open(path, "w", encoding="utf-8") as file:
        json.dump(paramDictTemplate, file, indent=4)

def load_param(path):
    with open(path, "r", encoding="utf-8") as file:
        paramDict = json.load(file)
    return paramDict

def download_youtube_video(video_id, fileNameAndPath):
    from pytube import YouTube
    YouTube(f'https://youtu.be/{video_id}', proxies=proxies).streams.first().download(filename=fileNameAndPath)

def transcribe_audio(path, modelName="base.en", languate="en",srtFilePathAndName="VIDEO_FILENAME.srt"):
    model = stable_whisper.load_model(modelName) # Change this to your desired model
    print("Whisper model loaded.")

    # 确保简体中文 
    initial_prompt=None
    if languate=="zh":
        initial_prompt="简体"
    
    transcribe = model.transcribe(audio=path,  language=languate, suppress_silence=False, vad=True, suppress_ts_tokens=False, temperature=0, initial_prompt=initial_prompt)
    print("Transcription complete.")

    transcribe.to_srt_vtt(srtFilePathAndName, word_level=False)
    print("SRT file created.")
    print("Output file: " + srtFilePathAndName)
    return True

def srtSentanceMerge(sourceSrtFilePathAndName, OutputSrtFilePathAndName):
    srtContent = open(sourceSrtFilePathAndName, "r").read()
    subGenerator = srt.parse(srtContent)
    subList = list(subGenerator)
    if len(subList) == 0:
        print("No subtitle found.")
        return False
    
    subPorcessingIndex = 1
    subItemList = []
    subItemProcessing = None
    for subItem in subList:
        dotIndex = subItem.content.rfind('.')
        exclamationIndex = subItem.content.rfind('!')
        questionIndex = subItem.content.rfind('?')
        endSentenceIndex = max(dotIndex, exclamationIndex, questionIndex)

        # 异常情况，句号居然在中间
        if endSentenceIndex != -1 and endSentenceIndex != len(subItem.content) - 1:
            print("Warning!! Sentence not end at the end of the subtitle.")
            print("Index: " + str(endSentenceIndex))
            print("Content: " + subItem.content)
            print(subItem)
            print("")
    
        # 以后一个字幕，直接拼接送入就可以了
        if subItem == subList[-1]:
            if subItemProcessing is None:
                subItemProcessing = copy.copy(subItem)
                subItemList.append(subItemProcessing)
                break
            else:
                subItemProcessing.end = subItem.end
                subItemProcessing.content += subItem.content
                subItemList.append(subItemProcessing)
                break

        # 新处理一串字符，则拷贝
        if subItemProcessing is None:
            subItemProcessing = copy.copy(subItem)
            subItemProcessing.content = '' # 清空内容是为了延续后面拼接的逻辑
        
        subItemProcessing.index = subPorcessingIndex
        subItemProcessing.end = subItem.end
        subItemProcessing.content += subItem.content
        # 如果一句话结束了，就把这一句话送入处理
        if endSentenceIndex == len(subItem.content) - 1:
            subItemList.append(subItemProcessing)
            subItemProcessing = None
            subPorcessingIndex += 1

    srtContent = srt.compose(subItemList)
    with open(OutputSrtFilePathAndName, "w") as file:
        file.write(srtContent)

def srt_to_text(srt_path):
    with open(srt_path, "r", encoding="utf-8") as file:
        lines = [line.rstrip() for line in file.readlines()]
    text = ""
    for line in lines:
        line = line.replace('\r', '')
        if line.isdigit():
            continue
        if line == "\n":
            continue
        if line == "":
            continue
        if re.search('\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}', line):
            continue
        text += line + '\n'
    return text

def trans(texts):
    if PROXY == "":
        client = Translate()
    else:
        client = Translate(proxies={'https': proxies['https']})
        # client = Translate(proxies={'https': PROXY})
    textsResponse = client.translate(texts, target='zh')
    textsTranslated = []
    for txtResponse in textsResponse:
        textsTranslated.append(txtResponse.translatedText)
    return textsTranslated


def srtFileTran(sourceFileNameAndPath, outputFileNameAndPath):
    srtContent = open(sourceFileNameAndPath, "r", encoding="utf-8").read()
    subGenerator = srt.parse(srtContent)
    subTitleList = list(subGenerator)
    contentList = []
    for subTitle in subTitleList:
        contentList.append(subTitle.content)
    
    contentList = trans(contentList)

    for i in range(len(subTitleList)):
        subTitleList[i].content = contentList[i]
    
    srtContent = srt.compose(subTitleList)
    with open(outputFileNameAndPath, "w", encoding="utf-8") as file:
        file.write(srtContent)

def stringToVoice(url, string, outputFile):
    data = {
        "text": string,
        "text_language": "zh"
    }
    response = requests.post(url, json=data)
    if response.status_code != 200:
        return False
    
    with open(outputFile, "wb") as f:
        f.write(response.content)

    return True

def srtToVoice(url, srtFileNameAndPath, outputDir):
    # create output directory if not exists
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    
    srtContent = open(srtFileNameAndPath, "r", encoding="utf-8").read()
    subGenerator = srt.parse(srtContent)
    subTitleList = list(subGenerator)
    index = 1
    fileNames = []
    print("Start to convert srt to voice")
    with tqdm(total=len(subTitleList)) as pbar:
        for subTitle in subTitleList:
            string = subTitle.content
            fileName = str(index) + ".wav"
            outputNameAndPath = os.path.join(outputDir, fileName)
            fileNames.append(fileName)
            tryTimes = 0

            while tryTimes < TTS_MAX_TRY_TIMES:
                if not stringToVoice(url, string, outputNameAndPath):
                    return False
                
                # 获取outputNameAndPath的时间长度
                audio = AudioSegment.from_wav(outputNameAndPath)
                duration = len(audio)
                # 获取最大音量
                maxVolume = audio.max_dBFS

                # 如果音频长度小于500ms，则重试，应该是数据有问题了
                if duration > 600 and maxVolume > -15:
                    break

                tryTimes += 1
            
            if tryTimes >= TTS_MAX_TRY_TIMES:
                print(f"Warning Failed to convert {fileName} to voice.")
                print(f"Convert {fileName} duration: {duration}ms, max volume: {maxVolume}dB")

            index += 1
            pbar.update(1) # update progress bar

    voiceMapSrt = copy.deepcopy(subTitleList)
    for i in range(len(voiceMapSrt)):
        voiceMapSrt[i].content = fileNames[i]
    voiceMapSrtContent = srt.compose(voiceMapSrt)
    voiceMapSrtFileAndPath = os.path.join(outputDir, "voiceMap.srt")
    with open(voiceMapSrtFileAndPath, "w", encoding="utf-8") as f:
        f.write(voiceMapSrtContent)
    
    srtAtitionalFile = os.path.join(outputDir, "zh.srt")
    with open(srtAtitionalFile, "w", encoding="utf-8") as f:
        f.write(srtContent)
    
    print("Convert srt to voice successfully")
    return True


def srtToVoiceEdge(srtFileNameAndPath, outputDir):
    # create output directory if not exists
    if not os.path.exists(outputDir):
        os.makedirs(outputDir)
    
    srtContent = open(srtFileNameAndPath, "r", encoding="utf-8").read()
    subGenerator = srt.parse(srtContent)
    subTitleList = list(subGenerator)
    index = 1
    fileNames = []
    fileMp3Names = []
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    print("Start to convert srt to voice")
    coroutines  = []
    for subTitle in subTitleList:
        string = subTitle.content
        fileMp3Name = str(index) + ".mp3"
        fileName = str(index) + ".wav"
        outputMp3NameAndPath = os.path.join(outputDir, fileMp3Name)
        fileMp3Names.append(fileMp3Name)
        fileNames.append(fileName)

        communicate = edge_tts.Communicate(string, "zh-CN-XiaoyiNeural")
        coroutine = communicate.save(outputMp3NameAndPath)
        coroutines.append(coroutine)
        index += 1
    
    # loop.run_until_complete(asyncio.gather(*coroutines))
    with ThreadPoolExecutor() as executor:
        executor.submit(loop.run_until_complete, asyncio.gather(*coroutines))
        while True:
            all_tasks = asyncio.all_tasks(loop)
            remaining_tasks = [task for task in all_tasks if not task.done()]
            print(f"\rbegin tasks: {len(coroutines)}, all tasks: {len(remaining_tasks)}", end='')
            if not remaining_tasks:
                break
    loop.close()
    print("\nConvert srt to mp3 voice successfully")

    # convert mp3 to wav
    for i in range(len(fileMp3Names)):
        mp3FileName = fileMp3Names[i]
        wavFileName = fileNames[i]
        mp3FileAndPath = os.path.join(outputDir, mp3FileName)
        wavFileAndPath = os.path.join(outputDir, wavFileName)
        sound = AudioSegment.from_mp3(mp3FileAndPath)
        sound.export(wavFileAndPath, format="wav")
        os.remove(mp3FileAndPath)

    voiceMapSrt = copy.deepcopy(subTitleList)
    for i in range(len(voiceMapSrt)):
        voiceMapSrt[i].content = fileNames[i]
    voiceMapSrtContent = srt.compose(voiceMapSrt)
    voiceMapSrtFileAndPath = os.path.join(outputDir, "voiceMap.srt")
    with open(voiceMapSrtFileAndPath, "w", encoding="utf-8") as f:
        f.write(voiceMapSrtContent)
    
    srtAtitionalFile = os.path.join(outputDir, "sub.srt")
    with open(srtAtitionalFile, "w", encoding="utf-8") as f:
        f.write(srtContent)
    
    print("Convert srt to wav voice successfully")
    return True

def voiceConnect(sourceDir, outputAndPath):
    MAX_SPEED_UP = 1.2  # 最大音频加速
    MIN_GAP_DURATION = 0.1  # 最小间隔时间，单位秒。低于这个间隔时间就认为音频重叠了

    if not os.path.exists(sourceDir):
        return False
    
    srtMapFileName = "voiceMap.srt"
    srtMapFileAndPath = os.path.join(sourceDir, srtMapFileName)
    if not os.path.exists(srtMapFileAndPath):
        return False
    
    voiceMapSrtContent = ""
    with open(srtMapFileAndPath, "r", encoding="utf-8") as f:
        voiceMapSrtContent = f.read()

    logFileNameAndPath = outputAndPath + ".log"
    logFile = WarningFile(logFileNameAndPath)

    # 确定音频长度
    voiceMapSrt = list(srt.parse(voiceMapSrtContent))
    duration = voiceMapSrt[-1].end.total_seconds() * 1000
    finalAudioFileAndPath = os.path.join(sourceDir, voiceMapSrt[-1].content)
    finalAudioEnd = voiceMapSrt[-1].start.total_seconds() * 1000
    finalAudioEnd += AudioSegment.from_wav(finalAudioFileAndPath).duration_seconds
    duration = max(duration, finalAudioEnd)

    # 初始化一个空的音频段
    combined = AudioSegment.silent(duration=duration)
    for i in range(len(voiceMapSrt)):
        audioFileAndPath = os.path.join(sourceDir, voiceMapSrt[i].content)
        audio = AudioSegment.from_wav(audioFileAndPath)
        audio = audio.strip_silence(silence_thresh=-40, silence_len=100) # 去除头尾的静音
        audioPosition = voiceMapSrt[i].start.total_seconds() * 1000

        if i != len(voiceMapSrt) - 1:
            # 检查上这一句的结尾到下一句的开头之间是否有静音，如果没有则需要缩小音频
            audioEndPosition = audioPosition + audio.duration_seconds * 1000 + MIN_GAP_DURATION *1000
            audioNextPosition = voiceMapSrt[i+1].start.total_seconds() * 1000
            if audioNextPosition < audioEndPosition:
                speedUp = (audio.duration_seconds * 1000 + MIN_GAP_DURATION *1000) / (audioNextPosition - audioPosition)
                if speedUp > MAX_SPEED_UP:
                    logFile.write(f"Warning: The audio {i} , at {audioPosition} , is too short, speed up is {speedUp}.")
                    print(f"Warning: The audio {i} , at {audioPosition} , is too short, speed up  is {speedUp}.")
                
                # 音频如果提速一个略大于1，则speedup函数可能会出现一个错误的音频，所以这里确定最小的speedup为1.01
                if speedUp < 1.05:
                    logFile.write(f"Warning: The audio {i}, speed up {speedUp} is too near to 1.0, change to 1.05.")
                    print(f"Warning: The audio {i}, speed up {speedUp} is too near to 1.0, change to 1.05.")
                    speedUp = 1.05
                audio = audio.speedup(playback_speed=speedUp)

        combined = combined.overlay(audio, position=audioPosition)
    
    combined.export(outputAndPath, format="wav")
    return True

if __name__ == "__main__":
    paramDirPathAndName = input("Please input the path and name of the parameter file: ")
    if not os.path.exists(paramDirPathAndName):
        create_param_template(paramDirPathAndName)
        print(f"Parameter file created at {paramDirPathAndName}.")
        print("Please edit the file and run the script again.")
        exit(0)
    
    # 打印当前系统时间
    print("Start at: " + str(datetime.datetime.now()))
    
    paramDict = load_param(paramDirPathAndName)
    workPath = paramDict["work path"]
    videoId = paramDict["video Id"]
    PROXY = paramDict["proxy"]
    audioRemoveModelNameAndPath = paramDict["audio remove model path"]

    proxies = {
        'http': f"{PROXY}",
        'https': f"{PROXY}",
        'socks5': f"{PROXY}"
    }

    # create the working directory if it does not exist
    if not os.path.exists(workPath):
        os.makedirs(workPath)
        print(f"Directory {workPath} created.")

    # 下载视频
    voiceFileName = f"{videoId}.mp4"
    viedoFileNameAndPath = os.path.join(workPath, voiceFileName)
    
    if paramDict["download video"]:
        print(f"Downloading video {videoId} to {viedoFileNameAndPath}")
        yt = YouTube(f'https://www.youtube.com/watch?v={videoId}', proxies=proxies, on_progress_callback=on_progress)
        video  = yt.streams.filter(progressive=True).last()
        video.download(output_path=workPath, filename=voiceFileName)
        # go back to the script directory
        print("Download complete.")
    else:
        print("Skip downloading video.")

    
    # try download 1080p video
    # 需要单独下载1080p视频，因为pytube下载的1080p视频没音频
    voiceFhdFileName = f"{videoId}_fhd.mp4"
    voiceFhdFileNameAndPath = os.path.join(workPath, voiceFhdFileName)
    if paramDict["download fhd video"]:
        try:
            print(f"Try to downloading 1080p video {videoId} to {voiceFhdFileNameAndPath}")
            yt = YouTube(f'https://www.youtube.com/watch?v={videoId}', proxies=proxies, on_progress_callback=on_progress)
            video  = yt.streams.filter(res="1080p").first()
            video.download(output_path=workPath, filename=voiceFhdFileName)
        except:
            print(f"Failed to download 1080p video {videoId} to {voiceFhdFileNameAndPath}")
    else:
        print("Skip downloading 1080p video.")

    # 打印当前系统时间
    print("Now at: " + str(datetime.datetime.now()))

    # 视频转声音提取
    audioFileName = f"{videoId}.wav"
    audioFileNameAndPath = os.path.join(workPath, audioFileName)
    if paramDict["extract audio"]:
        # remove the audio file if it exists
        print(f"Extracting audio from {viedoFileNameAndPath} to {audioFileNameAndPath}")
        video = VideoFileClip(viedoFileNameAndPath)
        audio = video.audio
        audio.write_audiofile(audioFileNameAndPath)
        print("Audio extraction complete.")
    else:
        print("Skip extracting audio.")
    
    # 去除音频中的音乐
    voiceName = videoId + "_voice.wav"
    voiceNameAndPath = os.path.join(workPath, voiceName)
    insturmentName = videoId + "_insturment.wav"
    insturmentNameAndPath = os.path.join(workPath, insturmentName)
    if paramDict["audio remove"]:
        print(f"Removing music from {audioFileNameAndPath} to {voiceNameAndPath} and {insturmentNameAndPath}")
        audio_remove(audioFileNameAndPath, voiceNameAndPath, insturmentNameAndPath, audioRemoveModelNameAndPath)
        print("Music removal complete.")
    else:
        print("Skip removing music.")
        
    # 语音转文字
    srtEnFileName = videoId + "_en.srt"
    srtEnFileNameAndPath = os.path.join(workPath, srtEnFileName)
    if paramDict["audio transcribe"]:
        print(f"Transcribing audio from {voiceNameAndPath} to {srtEnFileNameAndPath}")
        transcribe_audio(voiceNameAndPath, paramDict["audio transcribe model"], "en", srtEnFileNameAndPath)
        print("Transcription complete.")
    else:
        print("Skip transcription.")

    # 字幕语句合并
    srtEnFileNameMerge = videoId + "_en_merge.srt"
    srtEnFileNameMergeAndPath = os.path.join(workPath, srtEnFileNameMerge)
    if paramDict["srt merge"]:
        print(f"Merging sentences in {srtEnFileNameAndPath} to {srtEnFileNameMergeAndPath}")
        srtSentanceMerge(srtEnFileNameAndPath, srtEnFileNameMergeAndPath)
        print("Sentence merge complete.")
    else:
        print("Skip sentence merge.")

    # 英文字幕转文字
    tetEnFileName = videoId + "_en_merge.txt"
    tetEnFileNameAndPath = os.path.join(workPath, tetEnFileName)
    if paramDict["srt merge en to text"]:
        enText = srt_to_text(srtEnFileNameMergeAndPath)
        print(f"Writing EN text to {tetEnFileNameAndPath}")
        with open(tetEnFileNameAndPath, "w") as file:
            file.write(enText)
        print("Text file created.")
    else:
        print("Skip writing EN text.")

    # 字幕翻译
    srtZhFileName = videoId + "_zh_merge.srt"
    srtZhFileNameAndPath = os.path.join(workPath, srtZhFileName)
    if paramDict["srt merge translate"]:
        print(f"Translating subtitle from {srtEnFileNameMergeAndPath} to {srtZhFileNameAndPath}")
        srtFileTran(srtEnFileNameMergeAndPath, srtZhFileNameAndPath)
        print("Subtitle translation complete.")
    else:
        print("Skip subtitle translation.")

    # 中文字幕转文字
    textZhFileName = videoId + "_zh_merge.txt"
    textZhFileNameAndPath = os.path.join(workPath, textZhFileName)
    if paramDict["srt merge zh to text"]:
        zhText = srt_to_text(srtZhFileNameAndPath)
        print(f"Writing ZH text to {textZhFileNameAndPath}")
        with open(textZhFileNameAndPath, "w", encoding="utf-8") as file:
            file.write(zhText)
        print("Text file created.")
    else:
        print("Skip writing ZH text.")

    # 字幕转语音
    voiceUrl = paramDict["GPT-SoVITS url"]
    voiceDir = os.path.join(workPath, videoId + "_zh_source")
    voiceSrcSrtName = "zh.srt"
    voiceSrcSrtNameAndPath = os.path.join(voiceDir, voiceSrcSrtName)
    voiceSrcMapName = "voiceMap.srt"
    voiceSrcMapNameAndPath = os.path.join(voiceDir, voiceSrcMapName)
    if paramDict["srt to voice srouce"]:
        if voiceUrl == "":
            print(f"Converting subtitle to voice by EdgeTTS in {srtZhFileNameAndPath} to {voiceDir}")
            srtToVoiceEdge(srtZhFileNameAndPath, voiceDir)
        else:
            print(f"Converting subtitle to voice by GPT-SoVITS  in {srtZhFileNameAndPath} to {voiceDir}")
            srtToVoice(voiceUrl, srtZhFileNameAndPath, voiceDir)
        print("Voice conversion complete.")
    else:
        print("Skip voice conversion.")
    
    # 语音合并
    voiceConnectedName = videoId + "_zh.wav"
    voiceConnectedNameAndPath = os.path.join(workPath, voiceConnectedName)
    if paramDict["voice connect"]:
        print(f"Connecting voice in {voiceDir} to {voiceConnectedNameAndPath}")
        voiceConnect(voiceDir, voiceConnectedNameAndPath)
        print("Voice connection complete.")
    else:
        print("Skip voice connection.")
    
    # 合成后的语音转文字
    srtVoiceFileName = videoId + "_zh.srt"
    srtVoiceFileNameAndPath = os.path.join(workPath, srtVoiceFileName)
    if paramDict["audio zh transcribe"]:
        print(f"Transcribing audio from {voiceConnectedNameAndPath} to {srtVoiceFileNameAndPath}")
        transcribe_audio(voiceConnectedNameAndPath, paramDict["audio zh transcribe model"] ,"zh", srtVoiceFileNameAndPath)
        print("Transcription complete.")
    else:
        print("Skip transcription.")

    print("All done.")
    print("dir: " + workPath)
    

    