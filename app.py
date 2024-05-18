import os

from pytube import YouTube
from moviepy.editor import VideoFileClip
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory

from tools.audio_remove import audio_remove
from work_space import transcribeAudioEn, srtSentanceMerge

app = Flask(__name__)

app_path = os.path.abspath(__file__)
dir_path = os.path.dirname(app_path)
output_path = os.path.join(dir_path, "output")
model_path = os.path.join(dir_path, "models")
baseline_path = os.path.join(model_path, "baseline.pth")


def log_info_return_str(message):
    app.logger.info(message)
    return message


def log_error_return_str(message):
    app.logger.error(message)
    return message


def log_warning_return_str(message):
    app.logger.warning(message)
    return message


def require_video_id_from_post_request(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):
        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400

        data = request.get_json()

        if 'video_id' not in data:
            return jsonify({"message": "Missing 'video_id' in request"}), 400

        video_id = data['video_id']
        return func(video_id)

    return decorated_func


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/yt_download', methods=['POST'])
@require_video_id_from_post_request
def yt_download(video_id):
    video_fn = f"{video_id}.mp4"
    video_fhd = f"{video_id}_fhd.mp4"
    video_save_path = os.path.join(output_path, video_fn)
    video_fhd_save_path = os.path.join(output_path, video_fhd)

    if os.path.exists(video_save_path) and os.path.exists(video_fhd_save_path):
        return jsonify({"message": log_info_return_str(f"Video already exists at {video_save_path}, skip downloading."),
                        "video_id": video_id}), 200

    try:
        # 下载标清视频
        if not os.path.exists(video_save_path):
            yt = YouTube(f'https://www.youtube.com/watch?v={video_id}', proxies=None)
            video  = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').asc().first()
            video.download(output_path=output_path, filename=video_fn)

        # 下载高清视频
        if not os.path.exists(video_fhd_save_path):
            yt = YouTube(f'https://www.youtube.com/watch?v={video_id}', proxies=None)
            video  = yt.streams.filter(progressive=False, file_extension='mp4').order_by('resolution').desc().first()
            video.download(output_path=output_path, filename=video_fhd)

        return jsonify({"message": log_info_return_str(f"Download video {video_id} and {video_fhd} to {output_path} successfully."),
                        "video_id": video_id}), 200
    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while downloading video  {video_id} to {video_save_path}: {exception}')}), 500


@app.route('/yt/<video_id>', methods=['GET'])
def yt_serve(video_id):
    video_fn = f'{video_id}.mp4'

    if os.path.exists(os.path.join(output_path, video_fn)):
        return send_from_directory(output_path, video_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(f'Video {video_fn} not found at {output_path}')}), 404


@app.route('/extra_audio', methods=['POST'])
@require_video_id_from_post_request
def extra_audio(video_id):
    video_fn = f'{video_id}.mp4'
    audio_fn = f'{video_id}.wav'

    video_path, audio_path = os.path.join(output_path, video_fn), os.path.join(output_path, audio_fn)

    if os.path.exists(audio_path):
        return jsonify({"message": log_info_return_str(f"Audio already exists at {audio_path}, skip extracting."),
                        "video_id": video_id}), 200

    if not os.path.exists(video_path):
        jsonify({"message": log_warning_return_str(
            f'Video to extract {video_fn} not found at {output_path}, please download it first')}), 404

    try:
        video = VideoFileClip(video_path)
        video.audio.write_audiofile(audio_path)
        return jsonify({"message": log_info_return_str(f"Extracted audio {audio_fn} from {video_path} successfully."),
                        "video_id": video_id}), 200

    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while extracting audio {audio_fn} from {video_fn}: {exception}')}), 500


@app.route('/audio/<video_id>', methods=['GET'])
def audio_serve(video_id):
    video_fn = f'{video_id}.mp4'
    audio_fn = f'{video_id}.wav'

    video_path, audio_path = os.path.join(output_path, video_fn), os.path.join(output_path, audio_fn)

    if os.path.exists(audio_path):
        return send_from_directory(output_path, audio_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(f'Extracted audio {audio_fn}  not found at {audio_path}')}), 404


@app.route('/remove_audio_bg', methods=['POST'])
@require_video_id_from_post_request
def remove_audio_bg(video_id):
    video_fn = f'{video_id}.mp4'
    audio_fn = f'{video_id}.wav'
    audio_no_bg_fn, audio_bg_fn = f'{video_id}_no_bg.wav', f'{video_id}_bg.wav'

    video_path, audio_path, audio_no_bg_path, audio_bg_fn_path = (os.path.join(output_path, video_fn),
                                                                  os.path.join(output_path, audio_fn),
                                                                  os.path.join(output_path, audio_no_bg_fn),
                                                                  os.path.join(output_path, audio_bg_fn))

    if os.path.exists(audio_no_bg_path) and os.path.exists(audio_bg_fn_path):
        return jsonify({"message": log_info_return_str(
            f"Audio already exists at {audio_no_bg_path} and {audio_bg_fn_path}, skip removing background music."),
            "video_id": video_id}), 200

    if not os.path.exists(audio_path):
        jsonify({"message": log_warning_return_str(
            f'Audio to remove background music for {audio_path} '
            f'not found at {output_path}, please extract it first')}), 404

    try:
        audio_remove(audio_path, audio_no_bg_path, audio_bg_fn_path, baseline_path)
        return jsonify({"message": log_info_return_str(
            f"Remove remove background music for {audio_fn} as {audio_no_bg_fn} and {audio_bg_fn_path} successfully."),
            "video_id": video_id}), 200

    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while removing background music for {audio_fn} as {audio_no_bg_fn} and {audio_bg_fn_path}: {exception}')}), 500


@app.route('/audio_no_bg/<video_id>', methods=['GET'])
def audio_no_bg_serve(video_id):
    audio_no_bg_fn = f'{video_id}_no_bg.wav'
    audio_no_bg_path = os.path.join(output_path, audio_no_bg_fn)

    if os.path.exists(audio_no_bg_path):
        return send_from_directory(output_path, audio_no_bg_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Audio without background music {audio_no_bg_fn} not found at {audio_no_bg_path}')}), 404


@app.route('/audio_bg/<video_id>', methods=['GET'])
def audio_bg_serve(video_id):
    audio_bg_fn = f'{video_id}_bg.wav'
    audio_bg_path = os.path.join(output_path, audio_bg_fn)

    if os.path.exists(audio_bg_path):
        return send_from_directory(output_path, audio_bg_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Audio with background music only {audio_bg_fn} not found at {audio_bg_path}')}), 404


@app.route('/transcribe', methods=['POST'])
@require_video_id_from_post_request
def transcribe(video_id):
    transcribe_model = "medium"
    en_srt_fn, en_srt_merged_fn, audio_no_bg_fn = f'{video_id}_en.srt', f'{video_id}_en_merged.srt', f'{video_id}_no_bg.wav'

    en_srt_path, en_srt_merged_path, audio_no_bg_path = (os.path.join(output_path, en_srt_fn),
                                                         os.path.join(output_path, en_srt_merged_fn),
                                                         os.path.join(output_path, audio_no_bg_fn))

    if os.path.exists(en_srt_path) and os.path.exists(en_srt_merged_path):
        return jsonify({"message": log_info_return_str(
            f"English subtitles already exists at {en_srt_fn} and {en_srt_merged_fn}, skip generating."),
            "video_id": video_id}), 200

    if not os.path.exists(audio_no_bg_path):
        jsonify({"message": log_warning_return_str(
            f'Audio with voice '
            f'not found at {audio_no_bg_path}, please extract it first')}), 404

    try:
        transcribeAudioEn(audio_no_bg_path, transcribe_model, "en", srtFilePathAndName=en_srt_path)
        srtSentanceMerge(en_srt_path, en_srt_merged_path)

        return jsonify({"message": log_info_return_str(
            f"Transcribed SRT from {audio_no_bg_fn} as {en_srt_fn} and {en_srt_merged_fn} successfully."),
            "video_id": video_id}), 200

    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while transcribing SRT from {audio_no_bg_fn} as {en_srt_fn} and {en_srt_merged_fn}: {exception}')}), 500


@app.route('/srt_en/<video_id>', methods=['GET'])
def srt_en_serve(video_id):
    en_srt_fn = f'{video_id}_en.srt'
    en_srt_path = os.path.join(output_path, en_srt_fn)

    if os.path.exists(en_srt_path):
        return send_from_directory(output_path, en_srt_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Transcribed English SRT {en_srt_fn} not found at {en_srt_path}')}), 404


@app.route('/srt_en_merged/<video_id>', methods=['GET'])
def srt_en_merged_serve(video_id):
    en_srt_merged_fn = f'{video_id}_en_merged.srt'
    en_srt_merged_path = os.path.join(output_path, en_srt_merged_fn)

    if os.path.exists(en_srt_merged_path):
        return send_from_directory(output_path, en_srt_merged_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Transcribed English SRT {en_srt_merged_fn} not found at {en_srt_merged_path}')}), 404
