import math
import struct
import wave
import datetime

import srt
from faster_whisper import WhisperModel


def load_whisper_model(modelName, device="cuda"):
    return WhisperModel(modelName, device=device, compute_type="float16", download_root="faster-whisper_models",
                        local_files_only=False)


def save_srt_file(subs, srtFilePathAndName):
    content = srt.compose(subs)
    with open(srtFilePathAndName, "w", encoding="utf-8") as file:
        file.write(content)


def calculate_not_silence_threshold(threshold_db):
    return math.pow(10, threshold_db / 20)


def adjust_subtitle_timing(subs, path, notSilenceThreshold):
    audio = wave.open(path, 'rb')
    frameRate = audio.getframerate()
    for sub in subs:
        startTime = sub.start.total_seconds()
        startFrame = int(startTime * frameRate)
        endTime = sub.end.total_seconds()
        endFrame = int(endTime * frameRate)

        newStartTime = startTime
        audio.setpos(startFrame)
        readFrames = endFrame - startFrame
        for i in range(readFrames):
            frame = audio.readframes(1)
            if not frame:
                break
            samples = struct.iter_unpack("<h", frame)
            maxVolume = max(abs(sample[0]) / 32768 for sample in samples)
            if maxVolume > notSilenceThreshold:
                newStartTime = startTime + i / frameRate
                break

        sub.start = datetime.timedelta(seconds=newStartTime)


def transcribe_audio_en(logger, path, modelName="base.en", language="en", srtFilePathAndName="VIDEO_FILENAME.srt"):
    # 非静音检测阈值，单位为分贝，越小越严格
    NOT_SILENCE_THRESHOLD_DB = -30

    END_INTERPUNCTION = ["…", ".", "!", "?", ";"]
    NUMBER_CHARACTERS = "0123456789"
    # 确保简体中文
    initial_prompt = None
    if language == "zh":
        initial_prompt = "简体"

    model = WhisperModel(modelName, device="cuda", compute_type="float16", download_root="faster-whisper_models",
                         local_files_only=False)
    logger.info("Whisper model loaded.")

    # faster-whisper
    segments, _ = model.transcribe(audio=path, language=language, word_timestamps=True, initial_prompt=initial_prompt)
    # 转换为srt的Subtitle对象
    index = 1
    subs = []
    subtitle = None
    for segment in segments:
        for word in segment.words:
            if subtitle is None:
                subtitle = srt.Subtitle(index, datetime.timedelta(seconds=word.start),
                                        datetime.timedelta(seconds=word.end), "")
            finalWord = word.word.strip()
            subtitle.end = datetime.timedelta(seconds=word.end)

            # 一句结束。但是要特别排除小数点被误认为是一句结尾的情况。
            if (finalWord[-1] in END_INTERPUNCTION) and not (len(finalWord) > 1 and finalWord[-2] in NUMBER_CHARACTERS):
                pushWord = " " + finalWord
                subtitle.content += pushWord
                subs.append(subtitle)
                index += 1
                subtitle = None

            else:
                if subtitle.content == "":
                    subtitle.content = finalWord
                # 如果上一个字符是"."，则要考虑小数的可能性
                elif finalWord[0] == ".":
                    subtitle.content = subtitle.content + finalWord
                elif len(subtitle.content) > 0 and subtitle.content[-1] == "." and finalWord[0] in NUMBER_CHARACTERS:
                    subtitle.content = subtitle.content + finalWord
                else:
                    subtitle.content = subtitle.content + " " + finalWord

    # 补充最后一个字幕
    if subtitle is not None:
        subs.append(subtitle)
        index += 1

    logger.info("Transcription complete.")

    # 重新校准字幕开头，以字幕开始时间后声音大于阈值的第一帧为准
    notSilenceThreshold = calculate_not_silence_threshold(NOT_SILENCE_THRESHOLD_DB)
    adjust_subtitle_timing(subs, path, notSilenceThreshold)

    save_srt_file(subs, srtFilePathAndName)
    logger.info("SRT file created.")
    logger.info(f"Output file: {srtFilePathAndName}")
    return True


def transcribe_audio_zh(logger, path, modelName="base.en", language="en", srtFilePathAndName="VIDEO_FILENAME.srt"):
    END_INTERPUNCTION = ["。", "！", "？", "…", "；", "，", "、", ",", ".", "!", "?", ";"]
    ENGLISH_AND_NUMBER_CHARACTERS = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

    model = load_whisper_model(modelName)
    logger.info("Whisper model loaded.")

    segments, _ = model.transcribe(audio=path, language="zh", word_timestamps=True, initial_prompt="简体")

    index = 1
    subs = []
    subtitle = None
    for segment in segments:
        for word in segment.words:
            if subtitle is None:
                subtitle = srt.Subtitle(index, datetime.timedelta(seconds=word.start),
                                        datetime.timedelta(seconds=word.end), "")
            final_word = word.word.strip()
            subtitle.end = datetime.timedelta(seconds=word.end)

            # 排除英文字母+. 情况
            if ((final_word[-1] in END_INTERPUNCTION and not (
                    final_word[-1] == "." and len(final_word) > 1 and final_word[-2] in ENGLISH_AND_NUMBER_CHARACTERS))
                    or (len(subtitle.content) > 20)):
                subtitle.content += final_word[:-1] if final_word[-1] == "." and final_word[-2] in ENGLISH_AND_NUMBER_CHARACTERS else final_word
                subs.append(subtitle)
                index += 1
                subtitle = None
            else:
                subtitle.content += final_word

    if subtitle is not None:
        subs.append(subtitle)
        index += 1

    save_srt_file(subs, srtFilePathAndName)
    logger.info("SRT file created.")
    logger.info(f"Output file: {srtFilePathAndName}")
    return True
