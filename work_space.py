from tools.audio_remove import audio_remove
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
import sys
import traceback
import deepl

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
    "srt merge translate tool": "google", # 翻译工具，目前支持google和deepl
    "srt merge translate key": "", # 翻译工具的key
    "srt merge zh to text": True, # [工作流程开关]中文字幕转文字
    "srt to voice srouce": True, # [工作流程开关]字幕转语音
    "GPT-SoVITS url": "", # 不填写就是用edgeTTS，填写则为GPT-SoVITS 服务地址。简易不要用GPT-SoVITS
    "voice connect": True, # [工作流程开关]语音合并
    "audio zh transcribe": True, # [工作流程开关]合成后的语音转文字
    "audio zh transcribe model": "medium" # 中文语音转文字模型名称
}
diagnosisLog = None
executeLog = None

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
    srtContent = open(sourceSrtFilePathAndName, "r", encoding="utf-8").read()
    subGenerator = srt.parse(srtContent)
    subList = list(subGenerator)
    if len(subList) == 0:
        print("No subtitle found.")
        return False
    
    diagnosisLog.write("\n<Sentence Merge Section>", False)

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
            logString = f"Warning: Sentence (index:{endSentenceIndex}) not end at the end of the subtitle.\n"
            logString += f"Content: {subItem.content}"
            diagnosisLog.write(logString)
    
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
    # 如果打开错误则返回false
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
        if re.search('\\d{2}:\\d{2}:\\d{2},\\d{3} --> \\d{2}:\\d{2}:\\d{2},\\d{3}', line):
            continue
        text += line + '\n'
    return text

def googleTrans(texts):
    if PROXY == "":
        client = Translate()
    else:
        client = Translate(proxies={'https': proxies['https']})
    textsResponse = client.translate(texts, target='zh')
    textsTranslated = []
    for txtResponse in textsResponse:
        textsTranslated.append(txtResponse.translatedText)
    return textsTranslated

def deeplTranslate(texts, key):
    translator = deepl.Translator(key)
    # list to string
    textEn = ""
    for oneLine in texts:
        textEn += oneLine + "\n"

    textZh = translator.translate_text(textEn, target_lang="zh")
    textZh = str(textZh)
    textsZh = textZh.split("\n")
    return textsZh

def srtFileGoogleTran(sourceFileNameAndPath, outputFileNameAndPath):
    srtContent = open(sourceFileNameAndPath, "r", encoding="utf-8").read()
    subGenerator = srt.parse(srtContent)
    subTitleList = list(subGenerator)
    contentList = []
    for subTitle in subTitleList:
        contentList.append(subTitle.content)
    
    contentList = googleTrans(contentList)

    for i in range(len(subTitleList)):
        subTitleList[i].content = contentList[i]
    
    srtContent = srt.compose(subTitleList)
    with open(outputFileNameAndPath, "w", encoding="utf-8") as file:
        file.write(srtContent)

def srtFileDeeplTran(sourceFileNameAndPath, outputFileNameAndPath, key):
    srtContent = open(sourceFileNameAndPath, "r", encoding="utf-8").read()
    subGenerator = srt.parse(srtContent)
    subTitleList = list(subGenerator)
    contentList = []
    for subTitle in subTitleList:
        contentList.append(subTitle.content)
    
    contentList = deeplTranslate(contentList, key)

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
    
    async def convertSrtToVoiceEdge(text, path):
        print(f"Start to convert srt to voice into {path}, text: {text}")
        communicate = edge_tts.Communicate(text, "zh-CN-XiaoyiNeural")
        await communicate.save(path)

    coroutines  = []
    for subTitle in subTitleList:
        fileMp3Name = str(index) + ".mp3"
        fileName = str(index) + ".wav"
        outputMp3NameAndPath = os.path.join(outputDir, fileMp3Name)
        fileMp3Names.append(fileMp3Name)
        fileNames.append(fileName)
        coroutines.append(convertSrtToVoiceEdge(subTitle.content, outputMp3NameAndPath))
        index += 1

    # wait for all coroutines to finish
    loop = asyncio.get_event_loop()
    loop.run_until_complete(asyncio.gather(*coroutines))
    
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
    MIN_SPEED_UP = 1.05  # 最小音频加速
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

    # 确定音频长度
    voiceMapSrt = list(srt.parse(voiceMapSrtContent))
    duration = voiceMapSrt[-1].end.total_seconds() * 1000
    finalAudioFileAndPath = os.path.join(sourceDir, voiceMapSrt[-1].content)
    finalAudioEnd = voiceMapSrt[-1].start.total_seconds() * 1000
    finalAudioEnd += AudioSegment.from_wav(finalAudioFileAndPath).duration_seconds
    duration = max(duration, finalAudioEnd)

    diagnosisLog.write("\n<Voice connect section>", False)

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
                seconds = audioPosition / 1000.0
                timeStr = str(datetime.timedelta(seconds=seconds))
                if speedUp > MAX_SPEED_UP:
                    # 转换为 HH:MM:SS 格式
                    logStr = f"Warning: The audio {i+1} , at {timeStr} , is too short, speed up is {speedUp}."
                    diagnosisLog.write(logStr)
                
                # 音频如果提速一个略大于1，则speedup函数可能会出现一个错误的音频，所以这里确定最小的speedup为1.01
                if speedUp < MIN_SPEED_UP:
                    logStr = f"Warning: The audio {i+1} , at {timeStr} , speed up {speedUp} is too near to 1.0. Set to {MIN_SPEED_UP} forcibly."
                    diagnosisLog.write(logStr)
                    speedUp = MIN_SPEED_UP
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
    
    paramDict = load_param(paramDirPathAndName)
    workPath = paramDict["work path"]
    videoId = paramDict["video Id"]
    PROXY = paramDict["proxy"]
    audioRemoveModelNameAndPath = paramDict["audio remove model path"]

    proxies = None if not PROXY else {
        'http': f"{PROXY}",
        'https': f"{PROXY}",
        'socks5': f"{PROXY}"
    }

    # create the working directory if it does not exist
    if not os.path.exists(workPath):
        os.makedirs(workPath)
        print(f"Directory {workPath} created.")
    
    # 日志
    logFileName = "diagnosis.log"
    diagnosisLog = WarningFile(os.path.join(workPath, logFileName))
    # 执行日志文件的格式为excute_yyyyMMdd_HHmmss.log
    logFileName = "execute_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"
    executeLog = WarningFile(os.path.join(workPath, logFileName))

    nowString = str(datetime.datetime.now())
    executeLog.write(f"Start at: {nowString}")
    executeLog.write("Params\n" + json.dumps(paramDict, indent=4) + "\n")

    # 下载视频
    voiceFileName = f"{videoId}.mp4"
    viedoFileNameAndPath = os.path.join(workPath, voiceFileName)
    
    if paramDict["download video"]:
        print(f"Downloading video {videoId} to {viedoFileNameAndPath}")
        try:
            yt = YouTube(f'https://www.youtube.com/watch?v={videoId}', proxies=proxies, on_progress_callback=on_progress)
            video  = yt.streams.filter(progressive=True).last()
            video.download(output_path=workPath, filename=voiceFileName)
            # go back to the script directory
            executeLog.write(f"[WORK o] Download video {videoId} to {viedoFileNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while downloading video {videoId} to {viedoFileNameAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip downloading video."
        executeLog.write(logStr)

    
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
            executeLog.write(f"[WORK o] Download 1080p video {videoId} to {voiceFhdFileNameAndPath} successfully.")
        except:
            logStr = f"[WORK x] Error: Program blocked while downloading 1080p video {videoId} to {voiceFhdFileNameAndPath}."
            executeLog.write(logStr)
            logStr = f"Program will not exit for that the error is not critical."
            executeLog.write(logStr)
    else:
        logStr = "[WORK -] Skip downloading 1080p video."
        executeLog.write(logStr)

    # 打印当前系统时间
    print("Now at: " + str(datetime.datetime.now()))

    # 视频转声音提取
    audioFileName = f"{videoId}.wav"
    audioFileNameAndPath = os.path.join(workPath, audioFileName)
    if paramDict["extract audio"]:
        # remove the audio file if it exists
        print(f"Extracting audio from {viedoFileNameAndPath} to {audioFileNameAndPath}")
        try:
            video = VideoFileClip(viedoFileNameAndPath)
            audio = video.audio
            audio.write_audiofile(audioFileNameAndPath)
            executeLog.write(f"[WORK o] Extract audio from {viedoFileNameAndPath} to {audioFileNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while extracting audio from {viedoFileNameAndPath} to {audioFileNameAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip extracting audio."
        executeLog.write(logStr)
    
    # 去除音频中的音乐
    voiceName = videoId + "_voice.wav"
    voiceNameAndPath = os.path.join(workPath, voiceName)
    insturmentName = videoId + "_insturment.wav"
    insturmentNameAndPath = os.path.join(workPath, insturmentName)
    if paramDict["audio remove"]:
        print(f"Removing music from {audioFileNameAndPath} to {voiceNameAndPath} and {insturmentNameAndPath}")
        try:
            audio_remove(audioFileNameAndPath, voiceNameAndPath, insturmentNameAndPath, audioRemoveModelNameAndPath)
            executeLog.write(f"[WORK o] Remove music from {audioFileNameAndPath} to {voiceNameAndPath} and {insturmentNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while removing music from {audioFileNameAndPath} to {voiceNameAndPath} and {insturmentNameAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip removing music."
        executeLog.write(logStr)
        
    # 语音转文字
    srtEnFileName = videoId + "_en.srt"
    srtEnFileNameAndPath = os.path.join(workPath, srtEnFileName)
    if paramDict["audio transcribe"]:
        try:
            print(f"Transcribing audio from {voiceNameAndPath} to {srtEnFileNameAndPath}")
            transcribe_audio(voiceNameAndPath, paramDict["audio transcribe model"], "en", srtEnFileNameAndPath)
            executeLog.write(f"[WORK o] Transcribe audio from {voiceNameAndPath} to {srtEnFileNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while transcribing audio from {voiceNameAndPath} to {srtEnFileNameAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip transcription."
        executeLog.write(logStr)

    # 字幕语句合并
    srtEnFileNameMerge = videoId + "_en_merge.srt"
    srtEnFileNameMergeAndPath = os.path.join(workPath, srtEnFileNameMerge)
    if paramDict["srt merge"]:
        try:
            print(f"Merging sentences in {srtEnFileNameAndPath} to {srtEnFileNameMergeAndPath}")
            srtSentanceMerge(srtEnFileNameAndPath, srtEnFileNameMergeAndPath)
            executeLog.write(f"[WORK o] Merge sentences in {srtEnFileNameAndPath} to {srtEnFileNameMergeAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while merging sentences in {srtEnFileNameAndPath} to {srtEnFileNameMergeAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip sentence merge."
        executeLog.write(logStr)

    # 英文字幕转文字
    tetEnFileName = videoId + "_en_merge.txt"
    tetEnFileNameAndPath = os.path.join(workPath, tetEnFileName)
    if paramDict["srt merge en to text"]:
        try:
            enText = srt_to_text(srtEnFileNameMergeAndPath)
            print(f"Writing EN text to {tetEnFileNameAndPath}")
            with open(tetEnFileNameAndPath, "w") as file:
                file.write(enText)
            executeLog.write(f"[WORK o] Write EN text to {tetEnFileNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Writing EN text to {tetEnFileNameAndPath} failed."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            # 这不是关键步骤，所以不退出程序
            logStr = f"Program will not exit for that the error is not critical."
            executeLog.write(logStr)
    else:
        logStr = "[WORK -] Skip writing EN text."
        executeLog.write(logStr)

    # 字幕翻译
    srtZhFileName = videoId + "_zh_merge.srt"
    srtZhFileNameAndPath = os.path.join(workPath, srtZhFileName)
    if paramDict["srt merge translate"]:
        try:
            print(f"Translating subtitle from {srtEnFileNameMergeAndPath} to {srtZhFileNameAndPath}")
            if paramDict["srt merge translate tool"] == "deepl":
                if paramDict["srt merge translate key"] == "":
                    logStr = "[WORK x] Error: DeepL API key is not provided. Please provide it in the parameter file."
                    executeLog.write(logStr)
                    sys.exit(-1)
                srtFileDeeplTran(srtEnFileNameMergeAndPath, srtZhFileNameAndPath, paramDict["srt merge translate key"])
            else:
                srtFileGoogleTran(srtEnFileNameMergeAndPath, srtZhFileNameAndPath)
                executeLog.write(f"[WORK o] Translate subtitle from {srtEnFileNameMergeAndPath} to {srtZhFileNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while translating subtitle from {srtEnFileNameMergeAndPath} to {srtZhFileNameAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip subtitle translation."
        executeLog.write(logStr)

    # 中文字幕转文字
    textZhFileName = videoId + "_zh_merge.txt"
    textZhFileNameAndPath = os.path.join(workPath, textZhFileName)
    if paramDict["srt merge zh to text"]:
        try:
            zhText = srt_to_text(srtZhFileNameAndPath)
            print(f"Writing ZH text to {textZhFileNameAndPath}")
            with open(textZhFileNameAndPath, "w", encoding="utf-8") as file:
                file.write(zhText)
            executeLog.write(f"[WORK o] Write ZH text to {textZhFileNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Writing ZH text to {textZhFileNameAndPath} failed."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            # 这不是关键步骤，所以不退出程序
            logStr = f"Program will not exit for that the error is not critical."
            executeLog.write(logStr)
    else:
        logStr = "[WORK -] Skip writing ZH text."
        executeLog.write(logStr)

    # 字幕转语音
    voiceUrl = paramDict["GPT-SoVITS url"]
    voiceDir = os.path.join(workPath, videoId + "_zh_source")
    voiceSrcSrtName = "zh.srt"
    voiceSrcSrtNameAndPath = os.path.join(voiceDir, voiceSrcSrtName)
    voiceSrcMapName = "voiceMap.srt"
    voiceSrcMapNameAndPath = os.path.join(voiceDir, voiceSrcMapName)
    if paramDict["srt to voice srouce"]:
        try:
            if voiceUrl == "":
                print(f"Converting subtitle to voice by EdgeTTS in {srtZhFileNameAndPath} to {voiceDir}")
                srtToVoiceEdge(srtZhFileNameAndPath, voiceDir)
            else:
                print(f"Converting subtitle to voice by GPT-SoVITS  in {srtZhFileNameAndPath} to {voiceDir}")
                srtToVoice(voiceUrl, srtZhFileNameAndPath, voiceDir)
            executeLog.write(f"[WORK o] Convert subtitle to voice in {srtZhFileNameAndPath} to {voiceDir} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while converting subtitle to voice in {srtZhFileNameAndPath} to {voiceDir}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip voice conversion."
        executeLog.write(logStr)
    
    # 语音合并
    voiceConnectedName = videoId + "_zh.wav"
    voiceConnectedNameAndPath = os.path.join(workPath, voiceConnectedName)
    if paramDict["voice connect"]:
        try:
            print(f"Connecting voice in {voiceDir} to {voiceConnectedNameAndPath}")
            ret = voiceConnect(voiceDir, voiceConnectedNameAndPath)
            if ret == True:
                executeLog.write(f"[WORK o] Connect voice in {voiceDir} to {voiceConnectedNameAndPath} successfully.")
            else:
                executeLog.write(f"[WORK x] Connect voice in {voiceDir} to {voiceConnectedNameAndPath} failed.")
                sys.exit(-1)
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while connecting voice in {voiceDir} to {voiceConnectedNameAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip voice connection."
        executeLog.write(logStr)
    
    # 合成后的语音转文字
    srtVoiceFileName = videoId + "_zh.srt"
    srtVoiceFileNameAndPath = os.path.join(workPath, srtVoiceFileName)
    if paramDict["audio zh transcribe"]:
        try:
            print(f"Transcribing audio from {voiceConnectedNameAndPath} to {srtVoiceFileNameAndPath}")
            transcribe_audio(voiceConnectedNameAndPath, paramDict["audio zh transcribe model"] ,"zh", srtVoiceFileNameAndPath)
            executeLog.write(f"[WORK o] Transcribe audio from {voiceConnectedNameAndPath} to {srtVoiceFileNameAndPath} successfully.")
        except Exception as e:
            logStr = f"[WORK x] Error: Program blocked while transcribing audio from {voiceConnectedNameAndPath} to {srtVoiceFileNameAndPath}."
            executeLog.write(logStr)
            error_str = traceback.format_exception_only(type(e), e)[-1].strip()
            executeLog.write(error_str)
            sys.exit(-1)
    else:
        logStr = "[WORK -] Skip transcription."
        executeLog.write(logStr)


    executeLog.write("All done!!")
    print("dir: " + workPath)
    

    