# 说明
本项目能够快速地将英文视频转换为中文视频，本项目的特点在于其速度快体现在整个运作流程之上，而不是某一单一节点。以往的其他方案文本翻译质量很差，90%的时间都消耗在人工文本校对和重新翻译之上。本方案的特点在于文本翻译质量极高，需要校对的时间特别少，因此能够快速出视频。  
<br>
本方案优势：  
- 文本翻译质量高，节约了其他方案中占比约90%的人工文本校对和翻译时间。  
- 可以从任意步骤开始，因为每一步骤都生成文件且串行执行，下一步就依赖于上一步骤执行的文件。
- 正如上一步所说的串行执行优点代码结构清晰，可以摘取任意一段为己所用。  
<br>
本方案缺陷：
- 作者比较懒，没有时间做易用性调整。所以一些自定义的修改功能需要去源码里面查找。

# 目录
- [依赖](#依赖)
- [流程说明](#流程说明)
  - [流程列表](#流程列表)
- [json全参数说明](#json全参数说明)
- [工作流程](#工作流程)

# 依赖
安装依赖需要：requirements.txt中的各种依赖，pythorch库，ffmpeg(可选)。本工程Python 3.9.19上验证。另外如果你想体验完整的工作流程，推荐下载一个字幕文件编辑器，尽管本程序用不到，但是在转换视频的工作中，你一定用得到，我使用Aegisub。

各种基本库安装  
``
pip install -r requirements.txt
``

pytorch安装  
在[点击这里](https://pytorch.org/get-started/locally/)，选择合适的安装版本，**必须要选择gpu版！！！！** 原因是作者偷懒没有做gpu方案。

其他依赖  
因为本项目依赖[whisper](https://github.com/openai/whisper)，所以下载模型的时候国内可能会比较慢，可自行寻找解决方案whisper

# 快速使用
由于作者偷懒，根本没有做什么易用性，所以这个快速使用也不会有多快。  
1. 找到example里面的paramDict.json，文件拷出来准备作为参数输入。
2. "proxy"选择为自己的代理ip+端口
3. "video Id"选择为油管视频id。
4. "work path"工作目录
5. "audio remove model path"选择去背景音模型。models目录下提供了一个基本可用的模型baseline.pth
6. `python work_space.py`运行脚本，并输入你刚刚修改的脚本

# 流程说明
本项目流程串行执行后面的流程，依赖前面流程输出的文件。通过配置输入的Json文件，可以开关相应的流程。

## 流程列表
下面几乎所有的流程都会依赖这"video Id"和"work path"参数，所以在参数依赖说明中就省略了。  
以下使用“[video id]”代替油管视频ID
### 下载视频
- 流程开关："download video"  
- 依赖参数："proxy"
- 输入文件：无
- 输出文件：[video id].mp4
  
顾名思义从从管上下载视频。本流程将会选择一个清晰度最高且具有音频的视频流，该视频通常为720p。"proxy"参数选择带给路径。

### 下载高清视频
- 流程开关："download fhd video"  
- 依赖参数："proxy"  
- 输入文件：无  
- 输出文件：[video id]_fhd.mp4  

油管下载下来的720以上视频是不带音频的，为此专门提供了一个步骤单独下载1080p的视频，以此方便最终的视频合成，此视频文件不会被其他流程所使用到。

### 音频提取
- 流程开关："extract audio"  
- 依赖参数：无
- 输入文件：[video id].mp4  
- 输出文件：[video id].wav  

单独提取视频的音频轨道。

### 人声分离
- 流程开关："audio remove"  
- 依赖参数："audio remove model path"
- 输入文件：[video id].wav  
- 输出文件：[video id]_voice.wav，[video id]_insturment.wav

将人声与背景音乐分离。"audio remove model path"参数选择模型路径.为了方便广大用户,在models路径下有一个初步能用的模型。  

### 英文语音转字幕
- 流程开关："audio transcribe" 
- 依赖参数："audio transcribe model"
- 输入文件：[video id]_voice.wav 
- 输出文件：[video id]_en.srt

使用stable-ts(whisper的一个改进)将英文语音转换为字幕文件。这里选择的模型实际上是whisper的模型名称，可选"tiny.en"，"tiny"，"base.en"，"base"，"small.en"，"small"，"medium.en"，"medium"，"large"，"large-v2"，"large-v3"。  需要说明的是点en结尾的为纯英文模型，只能识别英文，这类模型在英语转字幕中具有优势。如果不差显存不差时间，推荐"medium.en"。

### 英文字幕合并
- 流程开关："srt merge"
- 依赖参数：无
- 输入文件：[video id]_en.srt
- 输出文件：[video id]_en_merge.srt

这一步骤中将英文字幕合并成句子，使得字幕文件的每一行都代表一整个英文句子。这一步正是此方案中翻译准确率高的关键。

### 英文合并字幕转文字
- 流程开关："srt merge en to text"
- 依赖参数：无  
- 输入文件：[video id]_en_merge.srt
- 输出文件：[video id]_en_merge.txt

这是一个没啥用的流程，只是为了方便大家看英文原文而已。

### 字幕翻译
- 流程开关："srt merge translate"
- 依赖参数："proxy"  
- 输入文件：[video id]_en_merge.srt
- 输出文件：[video id]_zh_merge.srt

将字幕文件送给谷歌进行翻译。至于为什么不选其他的翻译软件？我试过了效果都不好。这一步骤生成的文件特别重要，不出意外，你校对完成之后修改的就是[video id]_zh_merge.srt，然后从[video id]_zh_merge.srt步开始重新生成语音的。

### 中文合并字幕转文字
- 流程开关："srt merge zh to text"
- 依赖参数：无
- 输入文件：[video id]_zh_merge.srt
- 输出文件：[video id]_zh_merge.txt

这是一个没啥用的流程，只是为了方便大家看中文译文而已。

### 中文合并字幕转语音
- 流程开关："srt to voice srouce"
- 依赖参数："GPT-SoVITS url"    
- 输入文件：[video id]_zh_merge.txt
- 输出文件：[video id]_zh_source目录

这是一部是通过字幕文件转换成语音片段。"GPT-SoVITS url" 参数留空则使用edgeTTS，输入[GPT-SoVIT](https://github.com/RVC-Boss/GPT-SoVITS)创建的服务器地址则使用GPT-SoVIT文字转语音，推荐使用edge-TTS。GPT-SoVIT这个方案我虽然做了，但是根据实用来看并不是很实用，就当前这个时间点而言，其输出的音频并不是特别稳定，有时候还需要抽卡,至少我经常收到没有声音的音频。而这种自动化的流程无法判别你输出的音频质量是否符合视频要求。

### 语音片段合并
- 流程开关："voice connect"
- 依赖参数：无    
- 输入文件：[video id]_zh_source目录
- 输出文件：[video id]_zh.wav

将语音片段合成为完整的语音。需要注意的是，该过程会根据“[video id]_zh_source目录/voiceMap.srt”字幕文件中原语句出现的位置放置语音。也就是说其语音开始播放的位置与字幕开始的时间相同。这同时也会导致一个问题，如果最后一句的字幕长度不足，则语音的最后一句可能会被截断。

#### 中文语音转字幕
- 流程开关："audio zh transcribe" 
- 依赖参数："audio zh transcribe model"
- 输入文件：[video id]_zh.wav 
- 输出文件：[video id]_zh.srt

需要这一步骤的主要原因是之前的中文字幕文件都是以一句一句作为分割，作为字幕来讲可能太长了，所以这里重新生成一份字幕文件。

# json全参数说明
参考paramDictTemplate的注释即可  
```python
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
    "GPT-SoVITS url": "", # 不填写就是用edgeTTS，填写则为GPT-SoVITS 服务地址。建议不要用GPT-SoVITS
    "voice connect": True, # [工作流程开关]语音合并
    "audio zh transcribe": True, # [工作流程开关]合成后的语音转文字
    "audio zh transcribe model": "medium" # 中文语音转文字模型名称
}
```
## 需要特别说明的参数
"proxy"
如果留空则不使用代理。  
  
"download fhd video"  
我们总是希望自己转换出来的视频，高清又好看，但是油管下载下来的720以上视频是不带音频的，为此专门提供了一个步骤单独下载1080p的视频。这个步骤特别容易出现问题，比如说视频本身没有1080p。但是好在这个下载下来的全高清视频并不会参与之后的工作流程，只会影响到你最后人工视频合成那一步有没有好看的素材。  
  
"audio remove model path"  
models目录下提供了一个基本可用的模型baseline.pth
  
"GPT-SoVITS url"  
留空使用dege-TTS。输入GPT-SoVIT项目的服务器地址，则使用[GPT-SoVIT](https://github.com/RVC-Boss/GPT-SoVITS)项目进行文字转语音配音。这个方案我虽然做了，但是根据实用来看并不是很实用，就当前这个时间点而言，其输出的音频并不是特别稳定，有时候还需要抽卡,至少我经常收到没有声音的音频。而这种自动化的流程无法判别你输出的音频质量是否符合视频要求。

# 工作流程
你应该也看到了，在一个example目录下，我们还提供1.json和1.json，这两个是我常用的。一般转换一个视频，我通过以下几个步骤就完成了。以下使用“[video id]”代替油管视频ID  
1. 使用1.json下载视频并完成转换。
2. [video id]_zh.srt+[video id].wav+[video id].mp4(或者[video id]_fhd.mp4)初步完成视频并校对。
3. 校对发现问题则修改：[video id]_zh_merge.srt。校对过程几乎一定会发现问题。
4. 使用2.json再次生成音频。
5. [video id]_zh.srt+[video id].wav+[video id].mp4(或者[video id]_fhd.mp4)+[video id]_insturment.wav合成视频。

# 主要上游开源项目
 - [pytube](https://github.com/pytube/pytube)
 - [ffmpeg](https://ffmpeg.org/)
 - [stable-ts](https://github.com/jianfch/stable-ts)
 - [whisper](https://github.com/openai/whisper)
 - [vocal-remover](https://github.com/tsurumeso/vocal-remover/releases)
 - [srt](https://srt.readthedocs.io/en/latest/api.html)
 - [pygtrans](https://github.com/foyoux/pygtrans)
 - [edge-tts](https://github.com/hasscc/hass-edge-tts)
 - [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
 - [moviepy](https://github.com/Zulko/moviepy)

