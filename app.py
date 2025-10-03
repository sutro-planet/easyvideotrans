import os
import json
import requests
import zipfile
import shutil
import uuid
from src.service.video_synthesis.voice_connect import connect_voice
from src.service.translation import get_translator
from src.service.tts import get_tts_client
from src.workload_client import EasyVideoTransWorkloadClient
from src.task_manager.celery_tasks.tasks import video_preview_task
from src.task_manager.celery_tasks.celery_utils import get_queue_length
from werkzeug.utils import secure_filename
from pytubefix import YouTube
from moviepy.editor import VideoFileClip
from functools import wraps
from flask import Flask, request, jsonify, render_template, send_from_directory
from prometheus_flask_exporter import PrometheusMetrics

app = Flask(__name__, template_folder="./appendix/templates", static_folder="./appendix/static")
app.config.from_file("./configs/easyvideotrans.json", load=json.load)
metrics = PrometheusMetrics(app)
metrics.info('pytvzhen_web', 'Pytvzhen backend API', version='1.0.0')

PYTVZHEN_STAGE = 'PYTVZHEN_STAGE'
pytvzhen_api_request_counter = metrics.counter(
    'pytvzhen_api_request_counter', 'Request count by request paths',
    labels={'base_url': lambda: url_rule_to_base(request.url_rule), 'stage': lambda: pytvzhen_stage(),
            'method': lambda: request.method, 'status': lambda r: r.status_code}
)

tts_request_counter = metrics.counter(
    'tts_request_counter', 'TTS request count by vendor',
    labels={'vendor': lambda: getattr(request, '_tts_vendor', 'unknown'), 'stage': lambda: pytvzhen_stage()}
)

tts_duration_histogram = metrics.histogram(
    'tts_duration_seconds', 'TTS processing duration in seconds',
    labels={'vendor': lambda: getattr(request, '_tts_vendor', 'unknown'), 'stage': lambda: pytvzhen_stage()}
)

# Setup workloads client to submit any GPU workloads to EasyVideoTrans compute backend
gpu_workload = EasyVideoTransWorkloadClient(
    audio_separation_endpoint=app.config['VOICE_BACKGROUND_SEPARATION_ENDPOINT'],
    audio_transcribe_endpoint=app.config['AUDIO_TRANSCRIBE_ENDPOINT'],
)


def pytvzhen_stage():
    return os.environ[PYTVZHEN_STAGE] if PYTVZHEN_STAGE in os.environ else 'default'


def log_info_return_str(message):
    app.logger.info(message)
    return message


def log_error_return_str(message):
    app.logger.error(message)
    return message


def log_warning_return_str(message):
    app.logger.warning(message)
    return message


def url_rule_to_base(url_rule):
    base_path = str(url_rule)
    return base_path.split('<')[0].rstrip('/')


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


log_info_return_str(f"Launching Pytvzhen config: \n\t{app.config}")


@app.route('/', methods=['GET'])
@metrics.do_not_track()
def index():
    return render_template('index.html')


ALLOWED_EXTENSIONS = {'mp4'}


def video_extension_allowed(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def get_extension(filename):
    return filename.rsplit('.', 1)[1].lower()


def unique_video_fn_with_extension(extension):
    video_id = str(uuid.uuid4())
    return video_id, video_id + '.' + extension


@app.route('/video_upload', methods=['POST'])
@pytvzhen_api_request_counter
def video_upload():
    output_path = app.config['OUTPUT_PATH']

    # check if the post request has the file part
    if 'file' not in request.files:
        return jsonify(error='No file part in the POST request'), 400

    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file.filename == '':
        return jsonify(error='No selected file from frontend'), 400

    if file and video_extension_allowed(file.filename):
        filename = secure_filename(file.filename)
        file_ext = get_extension(filename)
        video_id, video_fn = unique_video_fn_with_extension(file_ext)

        file.save(os.path.join(output_path, video_fn))
        return jsonify({"message": log_info_return_str(f"Video {file.filename} uploaded as {video_fn}"),
                        "video_id": video_id})
    else:
        return jsonify({"message", log_error_return_str(f"Video upload failed: {file.filename} extension not allowed")})


@app.route('/yt_thumbnail', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def yt_thumbnail(video_id):
    output_path = app.config['OUTPUT_PATH']
    thumbnail_fn = f"{video_id}_thumbnail.png"

    if os.path.isfile(thumbnail_fn):
        return send_from_directory(output_path, thumbnail_fn, mimetype='image/png')

    thumbnail_save_path = os.path.join(output_path, thumbnail_fn)
    try:
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}', proxies=None)

        response = requests.get(yt.thumbnail_url)
        if response.status_code == 200:
            with open(thumbnail_save_path, 'wb') as file:
                file.write(response.content)
            return send_from_directory(output_path, thumbnail_fn, mimetype='image/png')

        raise Exception(f"thumbnail download failed: {response.status_code} {response.content}")
    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while downloading video thumbnail {video_id} to {thumbnail_save_path}: {exception}')}), 500


@app.route('/yt_download', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def yt_download(video_id):
    output_path = app.config['OUTPUT_PATH']

    video_fn = f"{video_id}.mp4"
    video_fhd = f"{video_id}_fhd.mp4"
    video_save_path = os.path.join(output_path, video_fn)
    video_fhd_save_path = os.path.join(output_path, video_fhd)

    if os.path.exists(video_save_path) and os.path.exists(video_fhd_save_path):
        return jsonify({"message": log_info_return_str(f"Video already exists at {video_save_path}, skip downloading."),
                        "video_id": video_id}), 200

    try:

        # 限制视频长度
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}', proxies=None)
        if yt.length > app.config['VIDEO_MAX_DURATION']:
            return jsonify({"message": log_error_return_str(
                f'Video duration is too long. Please select videos with duration less than {app.config["VIDEO_MAX_DURATION"]} seconds. ')}), 400

        # 下载标清视频
        if not os.path.exists(video_save_path):
            yt = YouTube(f'https://www.youtube.com/watch?v={video_id}', proxies=None)
            video = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').asc().first()
            video.download(output_path=output_path, filename=video_fn)

        # 下载高清视频
        if not os.path.exists(video_fhd_save_path):
            yt = YouTube(f'https://www.youtube.com/watch?v={video_id}', proxies=None)
            video = yt.streams.filter(progressive=False, file_extension='mp4').order_by('resolution').desc().first()
            video.download(output_path=output_path, filename=video_fhd)

        return jsonify({"message": log_info_return_str(
            f"Download video {video_id} and {video_fhd} to {output_path} successfully."),
            "video_id": video_id}), 200
    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while downloading video {video_id} to {video_save_path}: {exception}')}), 500


@app.route('/yt/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def yt_serve(video_id):
    output_path = app.config['OUTPUT_PATH']
    video_fn = f'{video_id}.mp4'

    if os.path.exists(os.path.join(output_path, video_fn)):
        return send_from_directory(output_path, video_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(f'Video {video_fn} not found at {output_path}')}), 404


@app.route('/extra_audio', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def extra_audio(video_id):
    output_path = app.config['OUTPUT_PATH']

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
@pytvzhen_api_request_counter
def audio_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    video_fn = f'{video_id}.mp4'
    audio_fn = f'{video_id}.wav'

    _, audio_path = os.path.join(output_path, video_fn), os.path.join(output_path, audio_fn)

    if os.path.exists(audio_path):
        return send_from_directory(output_path, audio_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(f'Extracted audio {audio_fn}  not found at {audio_path}')}), 404


@app.route('/remove_audio_bg', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def remove_audio_bg(video_id):
    output_path = app.config['OUTPUT_PATH']

    video_fn = f'{video_id}.mp4'
    audio_fn = f'{video_id}.wav'
    audio_no_bg_fn, audio_bg_fn = f'{video_id}_no_bg.wav', f'{video_id}_bg.wav'

    _, audio_path, audio_no_bg_path, audio_bg_fn_path = (os.path.join(output_path, video_fn),
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
        audio_bg_fn_path, audio_no_bg_fn = gpu_workload.separate_audio(audio_fn)
        return jsonify({"message": log_info_return_str(
            f"Remove remove background music for {audio_fn} as {audio_no_bg_fn} and {audio_bg_fn_path} successfully."),
            "video_id": video_id}), 200

    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while removing background music for {audio_fn} as {audio_no_bg_fn} and {audio_bg_fn_path}: {exception}')}), 500


@app.route('/audio_no_bg/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def audio_no_bg_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    audio_no_bg_fn = f'{video_id}_no_bg.wav'
    audio_no_bg_path = os.path.join(output_path, audio_no_bg_fn)

    if os.path.exists(audio_no_bg_path):
        return send_from_directory(output_path, audio_no_bg_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Audio without background music {audio_no_bg_fn} not found at {audio_no_bg_path}')}), 404


@app.route('/audio_bg/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def audio_bg_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    audio_bg_fn = f'{video_id}_bg.wav'
    audio_bg_path = os.path.join(output_path, audio_bg_fn)

    if os.path.exists(audio_bg_path):
        return send_from_directory(output_path, audio_bg_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Audio with background music only {audio_bg_fn} not found at {audio_bg_path}')}), 404


@app.route('/transcribe', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def transcribe(video_id):
    output_path = app.config['OUTPUT_PATH']

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
        gpu_workload.transcribe_audio(audio_no_bg_fn, [en_srt_fn, en_srt_merged_fn])
        return jsonify({"message": log_info_return_str(
            f"Transcribed SRT from {audio_no_bg_fn} as {en_srt_fn} and {en_srt_merged_fn} successfully."),
            "video_id": video_id}), 200

    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(
        f'An error occurred while transcribing SRT from {audio_no_bg_fn} as {en_srt_fn} and {en_srt_merged_fn}: {exception}')}), 500


@app.route('/srt_en/<video_id>', methods=['GET'])
def srt_en_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    en_srt_fn = f'{video_id}_en.srt'
    en_srt_path = os.path.join(output_path, en_srt_fn)

    if os.path.exists(en_srt_path):
        return send_from_directory(output_path, en_srt_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Transcribed English SRT {en_srt_fn} not found at {en_srt_path}')}), 404


@app.route('/translate_to_zh', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def transhlate_to_zh(video_id):
    output_path = app.config['OUTPUT_PATH']
    en_srt_merged_fn = f'{video_id}_en_merged.srt'
    zh_srt_merged_fn = f'{video_id}_zh_merged.srt'
    en_srt_merged_path = os.path.join(output_path, en_srt_merged_fn)
    zh_srt_merged_path = os.path.join(output_path, zh_srt_merged_fn)
    data = request.get_json()
    video_id = data['video_id']
    translateVendor = data['translate_vendor']
    api_key = data['translate_key']

    if not os.path.exists(en_srt_merged_path):
        return jsonify({"message": log_warning_return_str(
            f'English SRT {en_srt_merged_fn} not found at {en_srt_merged_path}')}), 404

    # 检查支持的翻译厂商
    if translateVendor not in ["google", "deepl"] and "gpt" not in translateVendor:
        return jsonify({"message": log_warning_return_str("Unsupported translate vendor.")}), 404

    try:
        translator = get_translator(translateVendor, api_key, proxies=None)
        ret = translator.translate_srt(source_file_name_and_path=en_srt_merged_path,
                                       output_file_name_and_path=zh_srt_merged_path)
        if ret:
            return jsonify({"message": log_info_return_str(
                f"using {translateVendor} translate to translate SRT from {en_srt_merged_fn} to {zh_srt_merged_fn} successfully."),
                "video_id": video_id}), 200
        else:
            return jsonify({"message": log_warning_return_str(f"{translateVendor} translate failed.")}), 404
    except ValueError as e:
        return jsonify({"message": log_warning_return_str(str(e))}), 404


@app.route('/srt_en_merged/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def srt_en_merged_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    en_srt_merged_fn = f'{video_id}_en_merged.srt'
    en_srt_merged_path = os.path.join(output_path, en_srt_merged_fn)

    if os.path.exists(en_srt_merged_path):
        return send_from_directory(output_path, en_srt_merged_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Transcribed English SRT {en_srt_merged_fn} not found at {en_srt_merged_path}')}), 404


@app.route('/translated_zh_upload', methods=['POST'])
@pytvzhen_api_request_counter
def translated_zh_upload():
    video_id = request.form['video_id']
    output_path = app.config['OUTPUT_PATH']
    # check if the post request has the file part
    if 'file' not in request.files:
        return jsonify(error='No file part in the POST request'), 400

    file = request.files['file']
    # if user does not select file, browser also
    # submit an empty part without filename
    if file and get_extension(file.filename):
        filename = video_id + "_zh_merged.srt"
        print("save:" + filename)
        file.save(os.path.join(output_path, filename))
        return jsonify({"message": log_info_return_str(f"SRT {filename} uploaded")})
    else:
        return jsonify({"message", log_error_return_str(f"Video upload failed: {file.filename} extension not allowed")})


@app.route('/srt_zh_merged/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def srt_zh_merged_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    zh_srt_merged_fn = f'{video_id}_zh_merged.srt'
    zh_srt_merged_path = os.path.join(output_path, zh_srt_merged_fn)

    if os.path.exists(zh_srt_merged_path):
        return send_from_directory(output_path, zh_srt_merged_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Transcribed English SRT {zh_srt_merged_fn} not found at {zh_srt_merged_path}')}), 404


@app.route('/voice_connect', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def voice_connect(video_id):
    output_path = app.config['OUTPUT_PATH']

    data = request.get_json()
    video_id = data['video_id']
    voice_volume = data.get('voice_volume', 1.0)  # 获取语音音量参数，默认为1.0
    voiceDir = os.path.join(output_path, video_id + "_zh_source")
    voice_connect_fn = video_id + "_zh.wav"
    voice_connect_path = os.path.join(output_path, voice_connect_fn)
    warning_log_fn = video_id + "_connect_warning.log"
    warning_log_path = os.path.join(output_path, warning_log_fn)

    if not os.path.exists(voiceDir):
        return jsonify({"message": log_warning_return_str(
            f'Voice directory {voiceDir} not found at {output_path}')}), 404

    ret = connect_voice(app.logger, voiceDir, voice_connect_path, warning_log_path, voice_volume)
    if ret:
        return jsonify({"message": log_info_return_str(
            f"Voice connect {voice_connect_fn} successfully."),
            "video_id": video_id}), 200
    else:
        return jsonify({"message": log_warning_return_str("Voice connect failed.")}), 404


@app.route('/voice_connect_log/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def voice_connect_log_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    warning_log_fn = video_id + "_connect_warning.log"
    warning_log_path = os.path.join(output_path, warning_log_fn)

    if os.path.exists(warning_log_path):
        return send_from_directory(output_path, warning_log_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Voice connect {warning_log_path} not found at {warning_log_path}')}), 404


@app.route('/voice_connect/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def voice_connect_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    voice_connect_fn = video_id + "_zh.wav"
    voice_connect_path = os.path.join(output_path, voice_connect_fn)

    if os.path.exists(voice_connect_path):
        return send_from_directory(output_path, voice_connect_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Voice connect {voice_connect_fn} not found at {voice_connect_path}')}), 404


@app.route('/tts', methods=['POST'])
@pytvzhen_api_request_counter
@tts_request_counter
@tts_duration_histogram
@require_video_id_from_post_request
def tts(video_id):
    import time
    import json

    start_time = time.time()
    output_path = app.config['OUTPUT_PATH']

    data = request.get_json()
    video_id = data['video_id']
    srt_fn = f'{video_id}_zh_merged.srt'
    srt_path = os.path.join(output_path, srt_fn)
    tts_dir = os.path.join(output_path, video_id + "_zh_source")

    # Get TTS configuration
    tts_vendor = data.get('tts_vendor', 'edge')  # Default to edge for backward compatibility
    character = data.get('tts_character', '')
    tts_params = data.get('tts_params', {})

    # Set vendor for metrics
    request._tts_vendor = tts_vendor

    if not os.path.exists(srt_path):
        return jsonify({"message": log_warning_return_str(
            f'Chinese SRT {srt_fn} not found at {output_path}')}), 404

    if os.path.exists(tts_dir):
        # delete old tts dir
        shutil.rmtree(tts_dir)

    try:
        if tts_vendor == 'edge':
            tts_client = get_tts_client("edge", character)
        elif tts_vendor == 'openai':
            # Parse OpenAI parameters
            if isinstance(tts_params, str):
                try:
                    tts_params = json.loads(tts_params) if tts_params else {}
                except json.JSONDecodeError:
                    tts_params = {}

            voice = character or tts_params.get('voice', 'alloy')
            model = tts_params.get('model', 'tts-1')
            instructions = tts_params.get('instructions', None)

            tts_client = get_tts_client("openai", voice=voice, model=model, instructions=instructions)
        else:
            return jsonify({"message": log_warning_return_str(f"Unsupported TTS vendor: {tts_vendor}")}), 400

        tts_client.srt_to_voice(srt_path, tts_dir)

        duration = time.time() - start_time
        return jsonify({"message": log_info_return_str(
            f"TTS success using {tts_vendor} (took {duration:.2f}s)."),
            "video_id": video_id, "duration": duration}), 200
    except Exception as e:
        exception = e

    return jsonify({"message": log_warning_return_str(f"tts failed: {exception}")}), 500


@app.route('/tts/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def tts_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    tts_dir = os.path.join(output_path, video_id + "_zh_source")
    tts_zip_fn = video_id + "_zh_source.zip"
    tts_zip_path = os.path.join(output_path, tts_zip_fn)
    if not os.path.exists(tts_dir):
        return jsonify({"message": log_warning_return_str(
            f'Voice directory {tts_dir} not found at {output_path}')}), 404

    zipf = zipfile.ZipFile(tts_zip_path, 'w', zipfile.ZIP_DEFLATED)
    for root, dirs, files in os.walk(tts_dir):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, output_path)
            zipf.write(file_path, relative_path)

    zipf.close()
    return send_from_directory(output_path, tts_zip_fn, as_attachment=True)


@app.route('/video_preview', methods=['POST'])
@pytvzhen_api_request_counter
@require_video_id_from_post_request
def video_preview(video_id):
    output_path = app.config['OUTPUT_PATH']

    data = request.get_json()
    video_id = data['video_id']
    voice_volume = data.get('voice_volume', 1.0)  # 获取语音音量参数，默认为1.0
    background_music_volume = data.get('background_music_volume', 0.5)  # 获取背景音乐音量参数，默认为0.5
    voice_connect_path = os.path.join(output_path, video_id + "_zh.wav")
    audio_bg_path = os.path.join(output_path, f'{video_id}_bg.wav')
    video_save_path = os.path.join(output_path, f"{video_id}.mp4")
    video_fhd_save_path = os.path.join(output_path, f"{video_id}_fhd.mp4")
    video_out_path = os.path.join(output_path, f"{video_id}_preview.mp4")

    # 检查音频
    if (not os.path.exists(voice_connect_path)) or (not os.path.exists(audio_bg_path)):
        return jsonify({"message": log_warning_return_str(
            f'Chinese Voice {video_id + "_zh.wav"} not found at {output_path}')}), 404

    # 检查视频
    if (not os.path.exists(video_save_path)) and (not os.path.exists(video_fhd_save_path)):
        return jsonify({"message": log_warning_return_str(
            "No video found")}), 404

    # 选择最佳分辨率的视频
    if os.path.exists(video_fhd_save_path):
        video_source_path = video_fhd_save_path
    else:
        video_source_path = video_save_path

    blocking = data.get('blocking', False)

    # 生成视频预览
    if blocking:
        video_preview_task.apply_async(
            args=(video_source_path, voice_connect_path, audio_bg_path, video_out_path, voice_volume, background_music_volume)).get()
        return jsonify({"message": log_info_return_str(
            f"Video preview {video_id} successfully rendered.")}), 200

    task = video_preview_task.delay(video_source_path, voice_connect_path, audio_bg_path, video_out_path, voice_volume, background_music_volume)

    queue_length = get_queue_length('video_preview')
    return jsonify({
        "message": log_info_return_str(f"Submitted video preview task {task.id}."),
        "video_preview_task_id": task.id,
        'queue_length': queue_length
    }), 202


@app.route('/video_preview_status/<task_id>', methods=['GET'])
@pytvzhen_api_request_counter
def video_preview_status(task_id):
    task = video_preview_task.AsyncResult(task_id)
    queue_length = get_queue_length('video_preview')
    if task.state == 'PENDING':
        response = {
            'state': task.state,
            'status': f'Video preview task {task_id} pending...',
            'queue_length': queue_length
        }
    elif task.state != 'FAILURE':
        response = {
            'state': task.state,
            'status': str(task.info),
            'queue_length': queue_length
        }
    else:
        response = {
            'state': task.state,
            'status': str(task.info),
            'result': str(task.result),
            'queue_length': queue_length
        }
    return jsonify(response)


@app.route('/video_preview/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def video_preview_serve(video_id):
    output_path = app.config['OUTPUT_PATH']

    video_preview_fn = f"{video_id}_preview.mp4"
    video_preview_path = os.path.join(output_path, video_preview_fn)

    if os.path.exists(video_preview_path):
        return send_from_directory(output_path, video_preview_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(
        f'Video preview {video_preview_fn} not found at {video_preview_path}')}), 404


@app.route('/subtitles/<video_id>', methods=['GET'])
@pytvzhen_api_request_counter
def download_subtitles(video_id):
    """Download Chinese translated SRT file for editing"""
    output_path = app.config['OUTPUT_PATH']

    # Look for the Chinese merged SRT file
    srt_fn = f'{video_id}_zh_merged.srt'
    srt_path = os.path.join(output_path, srt_fn)

    if not os.path.exists(srt_path):
        return jsonify({"message": log_warning_return_str(
            f'Chinese SRT {srt_fn} not found at {output_path}')}), 404

    try:
        with open(srt_path, 'r', encoding='utf-8') as file:
            content = file.read()

        return content, 200, {
            'Content-Type': 'text/plain; charset=utf-8',
            'Content-Disposition': f'attachment; filename="{srt_fn}"'
        }
    except Exception as e:
        return jsonify({"message": log_warning_return_str(
            f"Failed to read subtitle file: {str(e)}")}), 500


@app.route('/subtitles/<video_id>', methods=['POST'])
@pytvzhen_api_request_counter
def upload_subtitles(video_id):
    """Upload modified Chinese SRT file"""
    output_path = app.config['OUTPUT_PATH']

    data = request.get_json()
    if not data or 'content' not in data:
        return jsonify({"message": log_warning_return_str(
            "No subtitle content provided")}), 400

    content = data['content']

    # Validate SRT content (basic check)
    if not content.strip():
        return jsonify({"message": log_warning_return_str(
            "Subtitle content cannot be empty")}), 400

    # Save to the Chinese merged SRT file
    srt_fn = f'{video_id}_zh_merged.srt'
    srt_path = os.path.join(output_path, srt_fn)

    try:
        # Create backup of original file
        if os.path.exists(srt_path):
            backup_path = srt_path + '.backup'
            shutil.copy2(srt_path, backup_path)

        # Write the new content
        with open(srt_path, 'w', encoding='utf-8') as file:
            file.write(content)

        return jsonify({
            "message": log_info_return_str(f"Subtitle file {srt_fn} updated successfully"),
            "video_id": video_id
        }), 200

    except Exception as e:
        return jsonify({"message": log_warning_return_str(
            f"Failed to save subtitle file: {str(e)}")}), 500


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
