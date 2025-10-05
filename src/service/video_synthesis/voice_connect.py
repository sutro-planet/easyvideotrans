import os
import srt
import datetime
from math import log10
from pydub import AudioSegment
from src.utils.log_util import WarningFile


def connect_voice(logger, sourceDir, outputAndPath, warningFilePath, voice_volume=1.0):
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
    finalAudioEnd += AudioSegment.from_wav(finalAudioFileAndPath).duration_seconds * 1000
    duration = max(duration, finalAudioEnd)

    diagnosisLog = WarningFile(warningFilePath)
    # 初始化一个空的音频段
    combined = AudioSegment.silent(duration=duration)
    for i in range(len(voiceMapSrt)):
        audioFileAndPath = os.path.join(sourceDir, voiceMapSrt[i].content)
        audio = AudioSegment.from_wav(audioFileAndPath)
        audio = audio.strip_silence(silence_thresh=-40, silence_len=100)  # 去除头尾的静音
        audio_position = voiceMapSrt[i].start.total_seconds() * 1000

        if i != len(voiceMapSrt) - 1:
            # 检查上这一句的结尾到下一句的开头之间是否有静音，如果没有则需要缩小音频
            audio_end_position = audio_position + audio.duration_seconds * 1000 + MIN_GAP_DURATION * 1000
            audio_next_position = voiceMapSrt[i + 1].start.total_seconds() * 1000
            if audio_next_position < audio_end_position:
                position_delta = (audio_next_position - audio_position)
                speedUp = (audio.duration_seconds * 1000 + MIN_GAP_DURATION * 1000) / position_delta
                seconds = audio_position / 1000.0
                timeStr = str(datetime.timedelta(seconds=seconds))
                if speedUp > MAX_SPEED_UP:
                    # 转换为 HH:MM:SS 格式
                    logStr = f"Warning: The audio {i + 1} , at {timeStr} , is too short, speed up is {speedUp}."
                    diagnosisLog.write(logStr)

                # 音频如果提速一个略大于1，则speedup函数可能会出现一个错误的音频，所以这里确定最小的speedup为1.01
                if speedUp < MIN_SPEED_UP:
                    logStr = (f"Warning: The audio {i + 1} , at {timeStr} , speed up {speedUp} is too near to 1.0."
                              f" Set to {MIN_SPEED_UP} forcibly.")
                    diagnosisLog.write(logStr)
                    speedUp = MIN_SPEED_UP
                audio = audio.speedup(playback_speed=speedUp)

        # 应用音量调整
        if voice_volume != 1.0:
            audio = audio + (20 * log10(voice_volume))  # 使用分贝调整音量

        combined = combined.overlay(audio, position=audio_position)

    combined.export(outputAndPath, format="wav")
    return True
