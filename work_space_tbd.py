# from src.service.audio_processing.audio_remove import audio_remove
# # from tools_tbd.warning_file import WarningFile
# from src.data_models.workflow import Workflow
# import os
# import copy
# from pytube import YouTube
# from pytube.cli import on_progress
# import srt
# import requests
# from tqdm import tqdm
# from pydub import AudioSegment
# import asyncio
# import edge_tts
# import datetime
# from moviepy.editor import VideoFileClip
# import sys
# import traceback
# import tenacity
#
# PROXY = ""
# proxies = None
# TTS_MAX_TRY_TIMES = 16
# CHATGPT_URL = "https://api.openai.com/v1/"
# GHATGPT_TERMS_FILE = "configs/gpt_terms.json"
#
# diagnosisLog = None
# executeLog = None
#
# # 默认utf-8编码
# os.environ['PYTHONIOENCODING'] = 'utf-8'
# os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"  # 强制GPU版本cuda
#
#
# # def stringToVoice(url, string, outputFile):
# #     data = {
# #         "text": string,
# #         "text_language": "zh"
# #     }
# #     response = requests.post(url, json=data)
# #     if response.status_code != 200:
# #         return False
# #
# #     with open(outputFile, "wb") as f:
# #         f.write(response.content)
# #
# #     return True
# #
# #
# # def srtToVoice(url, srtFileNameAndPath, outputDir):
# #     # create output directory if not exists
# #     if not os.path.exists(outputDir):
# #         os.makedirs(outputDir)
# #
# #     srtContent = open(srtFileNameAndPath, "r", encoding="utf-8").read()
# #     subGenerator = srt.parse(srtContent)
# #     subTitleList = list(subGenerator)
# #     index = 1
# #     fileNames = []
# #     print("Start to convert srt to voice")
# #     with tqdm(total=len(subTitleList)) as pbar:
# #         for subTitle in subTitleList:
# #             string = subTitle.content
# #             fileName = str(index) + ".wav"
# #             outputNameAndPath = os.path.join(outputDir, fileName)
# #             fileNames.append(fileName)
# #             tryTimes = 0
# #
# #             while tryTimes < TTS_MAX_TRY_TIMES:
# #                 if not stringToVoice(url, string, outputNameAndPath):
# #                     return False
# #
# #                 # 获取outputNameAndPath的时间长度
# #                 audio = AudioSegment.from_wav(outputNameAndPath)
# #                 duration = len(audio)
# #                 # 获取最大音量
# #                 maxVolume = audio.max_dBFS
# #
# #                 # 如果音频长度小于500ms，则重试，应该是数据有问题了
# #                 if duration > 600 and maxVolume > -15:
# #                     break
# #
# #                 tryTimes += 1
# #
# #             if tryTimes >= TTS_MAX_TRY_TIMES:
# #                 print(f"Warning Failed to convert {fileName} to voice.")
# #                 print(f"Convert {fileName} duration: {duration}ms, max volume: {maxVolume}dB")
# #
# #             index += 1
# #             pbar.update(1)  # update progress bar
# #
# #     voiceMapSrt = copy.deepcopy(subTitleList)
# #     for i in range(len(voiceMapSrt)):
# #         voiceMapSrt[i].content = fileNames[i]
# #     voiceMapSrtContent = srt.compose(voiceMapSrt)
# #     voiceMapSrtFileAndPath = os.path.join(outputDir, "voiceMap.srt")
# #     with open(voiceMapSrtFileAndPath, "w", encoding="utf-8") as f:
# #         f.write(voiceMapSrtContent)
# #
# #     srtAtitionalFile = os.path.join(outputDir, "zh.srt")
# #     with open(srtAtitionalFile, "w", encoding="utf-8") as f:
# #         f.write(srtContent)
# #
# #     print("Convert srt to voice successfully")
# #     return True
#
#
#
# if __name__ == "__main__":
#     paramDirPathAndName = input("please input the path and name of the parameter file (json format), or press enter "
#                                 "to skip\n")
#     if paramDirPathAndName == "":
#         paramDirPathAndName = "data/workflow/default_param_dict.json"
#
#     # 检查paramDirPathAndName是否存在，是否为json文件
#     if not os.path.exists(paramDirPathAndName) or not os.path.isfile(
#             paramDirPathAndName) or not paramDirPathAndName.endswith(".json"):
#         print("Please select a valid parameter file.")
#         exit(-1)
#
#     workflow = Workflow(paramDirPathAndName)
#
#     # TODO: change the proxy field to json
#     proxies = None if not workflow.proxy else {
#         'http': f"{workflow.proxy}",
#         'https': f"{workflow.proxy}",
#         'socks5': f"{workflow.proxy}"
#     }
#
#     # create the working directory if it does not exist
#     if not os.path.exists(workflow.work_path):
#         os.makedirs(workflow.work_path)
#         print(f"Directory {workflow.work_path} created.")
#
#     # TODO: 日志系统需要改造
#     # logFileName = "diagnosis.log"
#     # diagnosisLog = WarningFile(os.path.join(workPath, logFileName))
#     # # 执行日志文件的格式为excute_yyyyMMdd_HHmmss.log
#     # logFileName = "execute_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".log"
#     # executeLog = WarningFile(os.path.join(workPath, logFileName))
#     #
#     # nowString = str(datetime.datetime.now())
#     # executeLog.write(f"Start at: {nowString}")
#     # executeLog.write("Params\n" + json.dumps(paramDict, indent=4) + "\n")
#
#     # 下载视频
#     # voiceFileName = f"{videoId}.mp4"
#     # viedoFileNameAndPath = os.path.join(workPath, voiceFileName)
#     #
#     # if paramDict["download video"]:
#     #     print(f"Downloading video {videoId} to {viedoFileNameAndPath}")
#     #     try:
#     #         # 如果已经有了，就不下载了
#     #         if os.path.exists(viedoFileNameAndPath):
#     #             print(f"Video {videoId} already exists.")
#     #             executeLog.write("[WORK -] Skip downloading video.")
#     #             print("Now at: " + str(datetime.datetime.now()))
#     #         else:
#     #             yt = YouTube(f'https://www.youtube.com/watch?v={videoId}', proxies=proxies,
#     #                          on_progress_callback=on_progress)
#     #             video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').asc().first()
#     #             video.download(output_path=workPath, filename=voiceFileName)
#     #             # go back to the script directory
#     #             executeLog.write(
#     #                 f"[WORK o] Download video {videoId} to {viedoFileNameAndPath} whith {video.resolution}.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while downloading video {videoId} to {viedoFileNameAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip downloading video."
#     #     executeLog.write(logStr)
#     #
#     # # try download more high-definition video
#     # # 需要单独下载最高分辨率视频，因为pytube下载的1080p视频没音频
#     # voiceFhdFileName = f"{videoId}_fhd.mp4"
#     # voiceFhdFileNameAndPath = os.path.join(workPath, voiceFhdFileName)
#     # if paramDict["download fhd video"]:
#     #     try:
#     #         # 如果已经有了，就不下载了
#     #         if os.path.exists(voiceFhdFileNameAndPath):
#     #             print(f"Video {videoId} already exists.")
#     #             executeLog.write("[WORK -] Skip downloading video.")
#     #             print("Now at: " + str(datetime.datetime.now()))
#     #         else:
#     #             print(f"Try to downloading more high-definition video {videoId} to {voiceFhdFileNameAndPath}")
#     #             yt = YouTube(f'https://www.youtube.com/watch?v={videoId}', proxies=proxies,
#     #                          on_progress_callback=on_progress)
#     #             video = yt.streams.filter(progressive=False, file_extension='mp4').order_by('resolution').desc().first()
#     #             video.download(output_path=workPath, filename=voiceFhdFileName)
#     #             executeLog.write(
#     #                 f"[WORK o] Download 1080p high-definition {videoId} to {voiceFhdFileNameAndPath} whith {video.resolution}.")
#     #     except Exception as e:
#     #         logStr = (
#     #             f"[WORK x] Error: Program blocked while downloading high-definition video"
#     #             f" {videoId} to {voiceFhdFileNameAndPath} with {video.resolution}: {e}")
#     #         executeLog.write(logStr)
#     #         logStr = "Program will not exit for that the error is not critical."
#     #         executeLog.write(logStr)
#     # else:
#     #     logStr = "[WORK -] Skip downloading high-definition video."
#     #     executeLog.write(logStr)
#     #
#     # # 打印当前系统时间
#     # print("Now at: " + str(datetime.datetime.now()))
#     #
#     # # 视频转声音提取
#     # audioFileName = f"{videoId}.wav"
#     # audioFileNameAndPath = os.path.join(workPath, audioFileName)
#     # if paramDict["extract audio"]:
#     #     # remove the audio file if it exists
#     #     print(f"Extracting audio from {viedoFileNameAndPath} to {audioFileNameAndPath}")
#     #     try:
#     #         video = VideoFileClip(viedoFileNameAndPath)
#     #         audio = video.audio
#     #         audio.write_audiofile(audioFileNameAndPath)
#     #         executeLog.write(
#     #             f"[WORK o] Extract audio from {viedoFileNameAndPath} to {audioFileNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while extracting audio from {viedoFileNameAndPath} to {audioFileNameAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip extracting audio."
#     #     executeLog.write(logStr)
#     #
#     # # 去除音频中的音乐
#     # voiceName = videoId + "_voice.wav"
#     # voiceNameAndPath = os.path.join(workPath, voiceName)
#     # insturmentName = videoId + "_insturment.wav"
#     # insturmentNameAndPath = os.path.join(workPath, insturmentName)
#     # if paramDict["audio remove"]:
#     #     print(f"Removing music from {audioFileNameAndPath} to {voiceNameAndPath} and {insturmentNameAndPath}")
#     #     try:
#     #         audio_remove(audioFileNameAndPath, voiceNameAndPath, insturmentNameAndPath, audioRemoveModelNameAndPath,
#     #                      "cuda:0")
#     #         executeLog.write(
#     #             f"[WORK o] Remove music from {audioFileNameAndPath} to {voiceNameAndPath} and {insturmentNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = (f"[WORK x] Error: Program blocked while removing music from {audioFileNameAndPath} "
#     #                   f"to {voiceNameAndPath} and {insturmentNameAndPath}.")
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip removing music."
#     #     executeLog.write(logStr)
#     #
#     # # 语音转文字
#     # srtEnFileName = videoId + "_en.srt"
#     # srtEnFileNameAndPath = os.path.join(workPath, srtEnFileName)
#     # if paramDict["audio transcribe"]:
#     #     try:
#     #         print(f"Transcribing audio from {voiceNameAndPath} to {srtEnFileNameAndPath}")
#     #         transcribeAudioEn(voiceNameAndPath, paramDict["audio transcribe model"], "en", srtEnFileNameAndPath)
#     #         executeLog.write(
#     #             f"[WORK o] Transcribe audio from {voiceNameAndPath} to {srtEnFileNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while transcribing audio from {voiceNameAndPath} to {srtEnFileNameAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip transcription."
#     #     executeLog.write(logStr)
#     #
#     # # 字幕语句合并
#     # srtEnFileNameMerge = videoId + "_en_merge.srt"
#     # srtEnFileNameMergeAndPath = os.path.join(workPath, srtEnFileNameMerge)
#     # if paramDict["srt merge"]:
#     #     try:
#     #         print(f"Merging sentences in {srtEnFileNameAndPath} to {srtEnFileNameMergeAndPath}")
#     #         srtSentanceMerge(srtEnFileNameAndPath, srtEnFileNameMergeAndPath)
#     #         executeLog.write(
#     #             f"[WORK o] Merge sentences in {srtEnFileNameAndPath} to {srtEnFileNameMergeAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while merging sentences in {srtEnFileNameAndPath} to {srtEnFileNameMergeAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip sentence merge."
#     #     executeLog.write(logStr)
#     #
#     # # 英文字幕转文字
#     # tetEnFileName = videoId + "_en_merge.txt"
#     # tetEnFileNameAndPath = os.path.join(workPath, tetEnFileName)
#     # if paramDict["srt merge en to text"]:
#     #     try:
#     #         enText = srt_to_text(srtEnFileNameMergeAndPath)
#     #         print(f"Writing EN text to {tetEnFileNameAndPath}")
#     #         with open(tetEnFileNameAndPath, "w") as file:
#     #             file.write(enText)
#     #         executeLog.write(f"[WORK o] Write EN text to {tetEnFileNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Writing EN text to {tetEnFileNameAndPath} failed."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         # 这不是关键步骤，所以不退出程序
#     #         logStr = "Program will not exit for that the error is not critical."
#     #         executeLog.write(logStr)
#     # else:
#     #     logStr = "[WORK -] Skip writing EN text."
#     #     executeLog.write(logStr)
#     #
#     # # 字幕翻译
#     # srtZhFileName = videoId + "_zh_merge.srt"
#     # srtZhFileNameAndPath = os.path.join(workPath, srtZhFileName)
#     # if paramDict["srt merge translate"]:
#     #     try:
#     #         print(f"Translating subtitle from {srtEnFileNameMergeAndPath} to {srtZhFileNameAndPath}")
#     #         if paramDict["srt merge translate tool"] == "deepl":
#     #             if paramDict["srt merge translate key"] == "":
#     #                 logStr = "[WORK x] Error: DeepL API key is not provided. Please provide it in the parameter file."
#     #                 executeLog.write(logStr)
#     #                 sys.exit(-1)
#     #             srtFileDeeplTran(srtEnFileNameMergeAndPath, srtZhFileNameAndPath, paramDict["srt merge translate key"])
#     #         elif 'gpt' in paramDict["srt merge translate tool"]:
#     #             if paramDict['srt merge translate key'] == '':
#     #                 logStr = "[WORK x] Error: GPT API key is not provided. Please provide it in the parameter file."
#     #                 executeLog.write(logStr)
#     #                 sys.exit(-1)
#     #             srtFileGPTTran(paramDict['srt merge translate tool'],
#     #                            proxies,
#     #                            srtEnFileNameMergeAndPath,
#     #                            srtZhFileNameAndPath,
#     #                            paramDict['srt merge translate key'])
#     #         else:
#     #             srtFileGoogleTran(srtEnFileNameMergeAndPath, srtZhFileNameAndPath)
#     #             executeLog.write(
#     #                 f"[WORK o] Translate subtitle from {srtEnFileNameMergeAndPath} to {srtZhFileNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while translating subtitle from {srtEnFileNameMergeAndPath} to {srtZhFileNameAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip subtitle translation."
#     #     executeLog.write(logStr)
#     #
#     # # 中文字幕转文字
#     # textZhFileName = videoId + "_zh_merge.txt"
#     # textZhFileNameAndPath = os.path.join(workPath, textZhFileName)
#     # if paramDict["srt merge zh to text"]:
#     #     try:
#     #         zhText = srt_to_text(srtZhFileNameAndPath)
#     #         print(f"Writing ZH text to {textZhFileNameAndPath}")
#     #         with open(textZhFileNameAndPath, "w", encoding="utf-8") as file:
#     #             file.write(zhText)
#     #         executeLog.write(f"[WORK o] Write ZH text to {textZhFileNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Writing ZH text to {textZhFileNameAndPath} failed."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         # 这不是关键步骤，所以不退出程序
#     #         logStr = "Program will not exit for that the error is not critical."
#     #         executeLog.write(logStr)
#     # else:
#     #     logStr = "[WORK -] Skip writing ZH text."
#     #     executeLog.write(logStr)
#     #
#     # # 字幕转语音
#     # ttsSelect = paramDict["TTS"]
#     # voiceDir = os.path.join(workPath, videoId + "_zh_source")
#     # voiceSrcSrtName = "zh.srt"
#     # voiceSrcSrtNameAndPath = os.path.join(voiceDir, voiceSrcSrtName)
#     # voiceSrcMapName = "voiceMap.srt"
#     # voiceSrcMapNameAndPath = os.path.join(voiceDir, voiceSrcMapName)
#     # if paramDict["srt to voice srouce"]:
#     #     try:
#     #         if ttsSelect == "GPT-SoVITS":
#     #             print(f"Converting subtitle to voice by GPT-SoVITS  in {srtZhFileNameAndPath} to {voiceDir}")
#     #             voiceUrl = paramDict["TTS param"]
#     #             srtToVoice(voiceUrl, srtZhFileNameAndPath, voiceDir)
#     #         else:
#     #             charator = paramDict["TTS param"]
#     #             if charator == "":
#     #                 srtToVoiceEdge(srtZhFileNameAndPath, voiceDir)
#     #             else:
#     #                 srtToVoiceEdge(srtZhFileNameAndPath, voiceDir, charator)
#     #             print(f"Converting subtitle to voice by EdgeTTS in {srtZhFileNameAndPath} to {voiceDir}")
#     #         executeLog.write(
#     #             f"[WORK o] Convert subtitle to voice in {srtZhFileNameAndPath} to {voiceDir} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while converting subtitle to voice in {srtZhFileNameAndPath} to {voiceDir}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip voice conversion."
#     #     executeLog.write(logStr)
#     #
#     # # 语音合并
#     # voiceConnectedName = videoId + "_zh.wav"
#     # voiceConnectedNameAndPath = os.path.join(workPath, voiceConnectedName)
#     # if paramDict["voice connect"]:
#     #     try:
#     #         print(f"Connecting voice in {voiceDir} to {voiceConnectedNameAndPath}")
#     #         ret = voiceConnect(voiceDir, voiceConnectedNameAndPath)
#     #         if ret:
#     #             executeLog.write(f"[WORK o] Connect voice in {voiceDir} to {voiceConnectedNameAndPath} successfully.")
#     #         else:
#     #             executeLog.write(f"[WORK x] Connect voice in {voiceDir} to {voiceConnectedNameAndPath} failed.")
#     #             sys.exit(-1)
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while connecting voice in {voiceDir} to {voiceConnectedNameAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip voice connection."
#     #     executeLog.write(logStr)
#     #
#     # # 合成后的语音转文字
#     # srtVoiceFileName = videoId + "_zh.srt"
#     # srtVoiceFileNameAndPath = os.path.join(workPath, srtVoiceFileName)
#     # if paramDict["audio zh transcribe"]:
#     #     try:
#     #         if os.path.exists(srtVoiceFileNameAndPath):
#     #             print("srtVoiceFileNameAndPath exists.")
#     #         else:
#     #             print(f"Transcribing audio from {voiceConnectedNameAndPath} to {srtVoiceFileNameAndPath}")
#     #             transcribeAudioZh(voiceConnectedNameAndPath, paramDict["audio zh transcribe model"], "zh",
#     #                               srtVoiceFileNameAndPath)
#     #             executeLog.write(
#     #                 f"[WORK o] Transcribe audio from {voiceConnectedNameAndPath} to {srtVoiceFileNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while transcribing audio from {voiceConnectedNameAndPath} to {srtVoiceFileNameAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip transcription."
#     #     executeLog.write(logStr)
#     #
#     # # 合成预览视频
#     # previewVideoName = videoId + "_preview.mp4"
#     # previewVideoNameAndPath = os.path.join(workPath, previewVideoName)
#     # if paramDict["video zh preview"]:
#     #     try:
#     #         sourceVideoNameAndPath = ""
#     #         if os.path.exists(voiceFhdFileNameAndPath):
#     #             sourceVideoNameAndPath = voiceFhdFileNameAndPath
#     #         elif os.path.exists(viedoFileNameAndPath):
#     #             print(
#     #                 f"Cannot find high-definition video, use low-definition video {viedoFileNameAndPath}
#     for preview video {previewVideoNameAndPath}")
#     #             sourceVideoNameAndPath = viedoFileNameAndPath
#     #         else:
#     #             logStr = f"[WORK x] Error: Cannot find source video for preview video {previewVideoNameAndPath}."
#     #             executeLog.write(logStr)
#     #             sys.exit(-1)
#     #
#     #         print(f"Generating zh preview video in {previewVideoNameAndPath}")
#     #         zhVideoPreview(sourceVideoNameAndPath, voiceConnectedNameAndPath, insturmentNameAndPath,
#     #                        srtVoiceFileNameAndPath, previewVideoNameAndPath)
#     #         executeLog.write(f"[WORK o] Generate zh preview video in {previewVideoNameAndPath} successfully.")
#     #     except Exception as e:
#     #         logStr = f"[WORK x] Error: Program blocked while generating zh preview video in {previewVideoNameAndPath}."
#     #         executeLog.write(logStr)
#     #         error_str = traceback.format_exception_only(type(e), e)[-1].strip()
#     #         executeLog.write(error_str)
#     #         sys.exit(-1)
#     # else:
#     #     logStr = "[WORK -] Skip zh preview video."
#     #     executeLog.write(logStr)
#     #
#     # executeLog.write("All done!!")
#     # print("dir: " + workPath)
#     #
#     # # push any key to exit
#     # input("Press any key to exit...")
