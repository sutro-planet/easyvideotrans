import copy
import re
import srt


def srt_sentense_merge(logger, source_srt_path, output_srt_path):
    try:
        with open(source_srt_path, "r", encoding="utf-8") as file:
            srt_content = file.read()
    except IOError as e:
        logger.error(f"Failed to read source file: {e}")
        return False

    subtitles = list(srt.parse(srt_content))
    if not subtitles:
        logger.warning("No subtitles found.")
        return False

    subPorcessingIndex = 1
    subItemList = []
    subItemProcessing = None
    for subItem in subtitles:
        dotIndex = subItem.content.rfind('.')
        exclamationIndex = subItem.content.rfind('!')
        questionIndex = subItem.content.rfind('?')
        endSentenceIndex = max(dotIndex, exclamationIndex, questionIndex)

        # 异常情况，句号居然在中间
        if endSentenceIndex != -1 and endSentenceIndex != len(subItem.content) - 1:
            logString = f"Warning: Sentence (index:{endSentenceIndex}) not end at the end of the subtitle.\n"
            logString += f"Content: {subItem.content}"
            logger.info(logString)

        # 以后一个字幕，直接拼接送入就可以了
        if subItem == subtitles[-1]:
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
            subItemProcessing.content = ''  # 清空内容是为了延续后面拼接的逻辑

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
    with open(output_srt_path, "w", encoding="utf-8") as file:
        file.write(srtContent)


def srt_to_text(srt_path):
    timecode_pattern = re.compile(r'\d{2}:\d{2}:\d{2},\d{3} --> \d{2}:\d{2}:\d{2},\d{3}')

    with open(srt_path, "r", encoding="utf-8") as file:
        lines = file.readlines()

    text_lines = []
    for line in lines:
        line = line.strip()
        if line.isdigit() or not line or timecode_pattern.match(line):
            continue
        text_lines.append(line)

    return '\n'.join(text_lines)
