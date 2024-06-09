# API说明
可以重点参考app.py文件中的代码。

## 视频上传
- 说明：上传视频文件，并返回视频ID。
- 路径：/video_to_audio
- 请求方法：POST
- 返回：
    - 成功：{"status": 200, "message": \[提示信息\], "video_id": \[视频ID\]}
    - 失败：{"status": 500, "message": \[错误信息\]}

## youtube视频获取
- 说明：根据视频ID获取下载youtube视频
- 路径：/yt_download
- 请求方法：POST
- 返回:
    - 成功：{"status": 200, "message": \[提示信息\], "video_id": \[视频ID\]}
    - 失败：{"status": 500, "message": \[错误信息\]}

## 视频下载
- 说明：根据视频ID下载视频文件
- 路径：/yt/<video_id>
- 请求方法：GET
- 返回：
    - 成功：视频文件
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 音视频分离
- 说明：根据视频ID分离音频和视频
- 路径：/extra_audio
- 请求方法：GET
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\], video_id: \[视频ID\]}
    - 失败：{"status": 500, "message": \[错误信息\]}
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 执行背景声分离
- 说明：根据视频ID执行背景声分离，将音频分割成背景声和人声
- 路径：/remove_audio_bg
- 请求方法：POST
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\], video_id: \[视频ID\]}
    - 失败：{"status": 500, "message": \[错误信息\]}
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 人声获取
- 说明：根据视频ID获取人声的音频文件
- 路径：/audio_no_bg/<video_id>
- 请求方法：GET
- 返回：
    - 成功：音频文件
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 背景声获取
- 说明：根据视频ID获取背景声的音频文件
- 路径：/bg_audio/<video_id>
- 请求方法：GET
- 返回：
    - 成功：音频文件
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 语言转字幕
- 说明：根据视频ID和语言，将音频转化为字幕
- 路径：/transcribe
- 请求方法：POST
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\], “video_id”: \[视频ID\]}
    - 失败：{"status": 500, "message": \[错误信息\]}
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 获取语言字幕
- 说明：获取原音频对应的字幕文件
- 路径：/srt_en/<video_id>
- 请求方法：GET
- 返回：
    - 成功：字幕文件
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 字幕翻译
- 说明：根据视频ID和语言，将字幕翻译为目标语言
- 路径：/translate_to_zh
- 请求方法：POST
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\], “video_id”: \[视频ID\]}
    - 失败：{"status": 500, "message": \[错误信息\]}
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 获取目标语言字幕
- 说明：获取原字幕对应的目标语言字幕文件
- 路径：/srt_zh_merged/<video_id>
- 请求方法：GET
- 返回：
    - 成功：目标语言字幕文件
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 上传目标语言字幕
- 说明：上传目标语言字幕文件
- 路径：/translated_zh_upload
- 请求方法：POST
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\]}

## 视频配音
- 说明：根据视频ID和配音人ID，将视频配音序列
- 路径：/tts
- 请求方法：POST
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\]}
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 获取配音包
- 说明：根据视频ID和配音人ID，获取视频配音包
- 路径：/tts/<video_id>
- 请求方法：GET
- 返回：
    - 成功：配音序列压缩包
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 配音连接
- 说明：根据视频ID将配音序列连接成完整的人声轨道
- 路径：/voice_connect
- 请求方法：POST
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\]}
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 获取人声轨道
- 说明：根据视频ID，获取人声轨道文件
- 路径：/voice_connect/<video_id>
- 请求方法：GET
- 返回：
    - 成功：人声轨道文件
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 预览视频合成
- 说明：根据视频ID，配音，背景声合成预览效果
- 请求路径：/video_preview
- 请求方法：POST
- 返回：
    - 成功：{“status”: 200, “message”: \[提示信息\], “video_id”: \[视频ID\]}
    - 失败：{"status": 404, "message": "\[错误信息\]}

## 获取预览视频
- 说明：根据视频ID，获取预览视频文件
- 请求路径：/video_preview/<video_id>
- 请求方法：GET
- 返回：
    - 成功：预览视频文件
    - 失败：{"status": 404, "message": "\[错误信息\]}