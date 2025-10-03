from moviepy.editor import VideoFileClip, AudioFileClip, CompositeAudioClip
import os


def zhVideoPreview(logger, videoFileNameAndPath, voiceFileNameAndPath, insturmentFileNameAndPath, srtFileNameAndPath,
                   outputFileNameAndPath, voice_volume=1.0, background_music_volume=0.5):
    # 从moviepy.editor导入VideoFileClip的创建音-视频剪辑
    video_clip = VideoFileClip(videoFileNameAndPath)

    # 加载音频
    voice_clip = None
    if (voiceFileNameAndPath is not None) and os.path.exists(voiceFileNameAndPath):
        voice_clip = AudioFileClip(voiceFileNameAndPath)
        if voice_volume != 1.0:
            voice_clip = voice_clip.volumex(voice_volume)  # 应用语音音量调整
    insturment_clip = None
    if (insturmentFileNameAndPath is not None) and os.path.exists(insturmentFileNameAndPath):
        insturment_clip = AudioFileClip(insturmentFileNameAndPath)
        if background_music_volume != 1.0:
            insturment_clip = insturment_clip.volumex(background_music_volume)  # 应用背景音乐音量调整

    # 组合音频剪辑
    final_audio = None
    if voiceFileNameAndPath is not None and insturmentFileNameAndPath is not None:
        final_audio = CompositeAudioClip([voice_clip, insturment_clip])
    elif voiceFileNameAndPath is not None:
        final_audio = voice_clip
    elif insturmentFileNameAndPath is not None:
        final_audio = insturment_clip

    video_clip = video_clip.set_audio(final_audio)
    video_clip.write_videofile(outputFileNameAndPath, codec='libx264', audio_codec='aac',
                               remove_temp=True, logger=None)
    video_clip.close()
    return True
