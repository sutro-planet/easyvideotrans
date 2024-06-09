# 简介
本项目为视频翻译配音工具，旨在为用户提供最简单可靠的视频翻译配音方案。自带简易web前端，
<br>
本方案优势：  
- 本方案提供最简单易用的流程接口，功能严格精选，确保用户最简单有效的为视频翻译配音，避免被巨量的不靠普方案迷惑。
- 翻译结果质量高，大幅减少人工校对。前期项目[pytvzhen](https://github.com/CuSO4Gem/pytvzhen)已经接受广大群友考验，倍受好评。
- 方案开源可靠，免费使用。代码结构清晰，可读性强，可扩展性强，适合二次开发。

# 目录
- [依赖](#依赖)
- [流程说明](#流程说明)
  - [流程列表](#流程列表)
- [json全参数说明](#json全参数说明)
- [工作流程](#工作流程)

# 部署

## Docker部署

## 本地部署
安装依赖需要：requirements.txt中的各种依赖，pythorch库，ffmpeg(可选)。本工程Python 3.9.19上验证。另外如果你想体验完整的工作流程，推荐下载一个字幕文件编辑器，尽管本程序用不到，但是在转换视频的工作中，你一定用得到，我使用Aegisub。

各种基本库安装  
``
pip install -r requirements.txt
``

pytorch安装  
在[点击这里](https://pytorch.org/get-started/locally/)，选择合适的安装版本，**必须要选择gpu版！！！！** 原因是作者偷懒没有做cpu方案，其实如果你愿意，改几行源码实现在CPU上跑应该也不难。

其他依赖  
ffmpeg安装  
```
sudo apt-get install ffmpeg
```
本项目依赖[whisper](https://github.com/openai/whisper)，所以下载模型的时候国内可能会比较慢，可自行寻找解决方案whisper


## API说明



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


# 网页版开发

在本地目录，跑Flask服务器

```
flask run --host=0.0.0.0 --debug
```

然后浏览器打开http://127.0.0.1:5000.

构建Docker镜像

```shell
docker build -t hanfa/pytvzhen-web:latest .
```

运行Docker容器
```shell
docker run --rm -p 8080:8080 -v output:/app/output hanfa/pytvzhen-web:latest
```

