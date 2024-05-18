import subprocess

def add_subtitles_and_mix_audio(input_video, 
                                input_subtitle, 
                                input_audio1, 
                                input_audio2, 
                                output_video):
    """
    使用 FFmpeg 将字幕和两个音频文件合成到视频文件中。
    
    参数:
      input_video (str): 输入视频文件的路径。
      input_subtitle (str): 字幕文件（ASS格式）的路径。
      input_audio1 (str): 第一个音频文件的路径（例如乐器音轨）。
      input_audio2 (str): 第二个音频文件的路径（例如人声音轨）。
      output_video (str): 输出视频文件的路径。
    """
    print("正在添加字幕和音频到视频中...")
    input_subtitle = input_subtitle.replace("\\", "/")
    print("input_subtitle: ", input_subtitle)
    # 构建 FFmpeg 命令
    command = [
        'ffmpeg',
        '-i', input_video,
        '-i', input_audio1,
        '-i', input_audio2,
        '-filter_complex',
        f"[1:a][2:a]amix=inputs=2[a];[0:v]subtitles={input_subtitle}[v]",
        '-map', '[v]',
        '-map', '[a]',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-strict', 'experimental',
        '-b:a', '192k',
        output_video
    ]

    # 执行命令
    try:
        subprocess.run(command, check=True)
        print("字幕和音频已成功添加到视频中。")
    except subprocess.CalledProcessError as e:
        print(f"FFmpeg 命令执行失败：{e}")


def main():
    # 使用示例
    add_subtitles_and_mix_audio(input_video='eMlx5fFNoYc_fhd.mp4', 
                                input_subtitle='merged_subtitles.ass', 
                                input_audio1='eMlx5fFNoYc_insturment.wav', 
                                input_audio2='eMlx5fFNoYc_zh.wav', 
                                output_video='eMlx5fFNoYc_fhd_merge.mp4')


if __name__ == "__main__":
    main()