
<div align="center"><a name="readme-top"></a>

<a href="https://github.com/sutro-planet/pytvzhen-web" target="_blank">
  <img src="assets/cartography.png" alt="alt text">
</a>

<h1>EasyVideoTrans</h1>
<h3>
易用AI频翻译配音工具的web后端<br />
</h3>

<div style="text-align: center;">

[Changelog](./doc/change_log.md) <br>
![Linux Verfied](https://img.shields.io/badge/Linux-Verfied-brightgreen)
[![Bilibili](https://img.shields.io/badge/Bilibili-蓝色硫酸铜-FF69B4?style=flat&logo=bilibili)](https://space.bilibili.com/278134)
[![x zornlink](https://img.shields.io/twitter/url/https/twitter.com/cloudposse.svg?style=social&label=Follow%20%40Zornlink)](https://x.com/zornlink)
[![q群1](https://img.shields.io/badge/企鹅群-536918174-1EBAFC?style=flat&logo=tencentqq)](https://qm.qq.com/q/pJMgV3liiO)
</div>

</div>

# 简介
本项目着眼于从原始视频到翻译后最终视频的整个工作流程，确保从一而终的整个过程顺畅高效。项目提供了web后端，方便<br>
<br>
本方案优势：
- 方案简单好用，经过验证，十分可靠，避免被巨量的不靠普方案迷惑，节约用户选择成本。<br>
- 翻译结果质量高，大幅减少人工校对。前期项目<a href="https://github.com/CuSO4Gem/pytvzhen">pytvzhen</a>已经接受广大群友考验，倍受好评。<br>
- 方案开源可靠，免费使用。代码结构清晰，可读性强，可扩展性强，适合二次开发。


相关技术说明：
在[技术关注&开发计划](#技术关注开发计划)部分，我们列出了本方案的主要技术关注点，以及后续的开发计划。本项目重点强调易用、可靠、以及产生最终最终视频的速度。因此我们排除了大量不稳定、不可靠的方案，进保留整个工作流程中最好用的方案献给广大用户。

<img src="assets/logo.png" alt="图片">


# 目录
- [简介](#简介)
- [目录](#目录)
- [部署](#部署)
  - [Docker部署（推荐）](#docker部署推荐)
  - [本地部署](#本地部署)
    - [环境准备](#环境准备)
    - [运行](#运行)
- [API说明](#api说明)
- [技术关注\&开发计划](#技术关注开发计划)
- [主要上游开源项目](#主要上游开源项目)

# 部署

## Docker部署（推荐）


```shell
sudo docker run --rm -p 8888:8080 -v output:/app/output --runtime=nvidia --gpus all hanfa/pytvzhen-web:latest
```


## 本地部署
### 环境准备
安装依赖需要：requirements.txt中的各种依赖，pythorch库，ffmpeg(可选)。本工程Python 3.9.19上验证。另外如果你想体验完整的工作流程，推荐下载一个字幕文件编辑器，尽管本程序用不到，但是在转换视频的工作中，你一定用得到，我使用Aegisub。

各种基本库安装
``
pip install -r requirements.txt
``

pytorch安装：
在[点击这里](https://pytorch.org/get-started/locally/)，选择合适的安装版本，**必须要选择gpu版！！！！** 原因是作者偷懒没有做cpu方案，其实如果你愿意，改几行源码实现在CPU上跑应该也不难。

其他依赖：

确保 RabbitMQ 作为broker在[./configs/celery.json](./configs/celery.json)里定义的`broker_url`运行，
具体方法参考[这里](https://www.rabbitmq.com/docs/download)，用`sudo rabbitmqctl status` 确保其正常运行。

ffmpeg安装
```
sudo apt-get install ffmpeg
```
[faster-whisper](https://github.com/SYSTRAN/faster-whisper/)下载自动模型的时候，国内可能会比较慢，甚至无法下载！！faster-whisper_models目录中，使得目录结构为：
```
faster-whisper_models
     |-models--Systran--faster-whisper-base.en
     |-models--Systran--faster-whisper-medium
     |-...
```

### 运行

在一个 terminal 里面启动 Celery 队列和 worker 来处理视频渲染请求。

`celery -A celery_tasks.celery_app worker --concurrency 1 -Q video_preview`

在另一个 terminal 里运行flask app。
```
flask run --host=0.0.0.0 --debug
```

然后浏览器打开http://127.0.0.1:5000.

# API说明
[API文档](./doc/api.md)

# 技术关注&开发计划
后续计划：谨慎添加更多可靠的功能，增加其他语言到中文的翻译
| 项目名称 | 功能 | 当前状况 | 计划 |
| --- | --- | --- | --- |
| [whisper](https://github.com/openai/whisper)、[stable-whisper](https://github.com/jianfch/stable-ts)| 语言转字幕| 效果不如faster-whisper | 不添加 |
| [Funasr](https://gitcode.com/alibaba-damo-academy/FunASR/)| 语言转字幕| 还没验证 | 验证后再决策 |
| [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)| TTS | TTS输出不稳定 | 观望|
| [ChatTTS](https://github.com/2noise/ChatTTS) | TTS | TTS输出不稳定 | 观望 |
| [Open AI TTS](https://platform.openai.com/docs/guides/text-to-speech) | TTS | 要钱 | 后续添加 |
| [EmotiVoice](https://github.com/netease-youdao/EmotiVoice) | TTS | 不稳定 | 观望 |
| [StreamSpeech](https://github.com/ictnlp/StreamSpeech) | TTS | 还没验证 | 验证后再决策|
| 百度翻译、有道翻译、迅飞翻译 | 翻译 | 效果远不如谷歌 | 不添加 |
| [ChatGpt](https://chatgpt.com) | 翻译 | 效果不错 | 后续添加 |



# 主要上游开源项目
 - [pytvzhen](https://github.com/CuSO4Gem/pytvzhen)
 - [pytube](https://github.com/pytube/pytube)
 - [ffmpeg](https://ffmpeg.org/)
 - [faster-whisper](https://github.com/SYSTRAN/faster-whisper)
 - [vocal-remover](https://github.com/tsurumeso/vocal-remover/releases)
 - [srt](https://srt.readthedocs.io/en/latest/api.html)
 - [pygtrans](https://github.com/foyoux/pygtrans)
 - [edge-tts](https://github.com/hasscc/hass-edge-tts)
 - [GPT-SoVITS](https://github.com/RVC-Boss/GPT-SoVITS)
 - [moviepy](https://github.com/Zulko/moviepy)

