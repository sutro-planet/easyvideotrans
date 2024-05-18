import requests
import os
import srt
import json
import IPython

def stringToVoice(url, string, outputFile):
    data = {
        "refer_wav_path": "ref/1.wav",
        "prompt_text": "",
        "text": string,
        "text_language": "zh"
    }
    response = requests.post(url, json=data)
    if response.status_code == 400:
        IPython.embed()
        return False
    
    with open(outputFile, "wb") as f:
        f.write(response.content)

def load_param(path):
    with open(path, "r", encoding="utf-8") as file:
        paramDict = json.load(file)
    return paramDict

if __name__ == "__main__":
    paramDirPathAndName = input("Please input the path and name of the parameter file: ")
    
    if not os.path.exists(paramDirPathAndName):
        print("Please edit the file and run the script again.")
        exit(0)

    paramDict = load_param(paramDirPathAndName)
    videoId = paramDict["video Id"]
    workPath = paramDict["work path"]
    voiceDir = os.path.join(workPath, videoId + "_zh_source")
    url = "http://127.0.0.1:9001"
    voiceSrcMapName = "voiceMap.srt"
    voiceSrcMapNameAndPath = os.path.join(voiceDir, voiceSrcMapName)
    voiceSrcSrtName = "zh.srt"
    voiceSrcSrtNameAndPath = os.path.join(voiceDir, voiceSrcSrtName)

    voiceMapSrtContent = open(voiceSrcMapNameAndPath, "r", encoding="utf-8").read()
    voiceMapSrt = list(srt.parse(voiceMapSrtContent))

    srtContent = open(voiceSrcSrtNameAndPath, "r", encoding="utf-8").read()
    subGenerator = srt.parse(srtContent)
    subTitleList = list(subGenerator)

    while True:
        index = int(input("请输入要合成的字幕序号:"))
        if index < 1 or index >= len(subTitleList) + 1:
            continue
        index -= 1
        print(voiceMapSrt[index].content)
        print(subTitleList[index].content)
        voiceFileName = voiceMapSrt[index].content
        voiceFileAndPath = os.path.join(voiceDir, voiceFileName)

        print("redo file: ", voiceFileAndPath)
        # delete the file if it exists
        if os.path.exists(voiceFileAndPath):
            print("Delete the file: ", voiceFileAndPath)
            os.remove(voiceFileAndPath)
        
        stringToVoice(url, subTitleList[index].content, voiceFileAndPath)