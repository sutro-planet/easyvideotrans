import os

from flask import Flask, request, jsonify, render_template, send_from_directory
from pytube import YouTube

app = Flask(__name__)

app_path = os.path.abspath(__file__)
dir_path = os.path.dirname(app_path)
output_path = os.path.join(dir_path, "output")


def log_info_return_str(message):
    app.logger.info(message)
    return message

def log_error_return_str(message):
    app.logger.error(message)
    return message

def log_warning_return_str(message):
    app.logger.warning(message)
    return message


@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')


@app.route('/yt_download', methods=['POST'])
def yt_download():

    print(request)
    if not request.is_json:
        return jsonify({"message": "Missing JSON in request"}), 400

    data = request.get_json()

    if 'video_id' not in data:
        return jsonify({"message": "Missing 'video_id' in request"}), 400

    video_id = data['video_id']
    video_fn = f"{video_id}.mp4"
    video_save_path = os.path.join(output_path, video_fn)

    if os.path.exists(video_save_path):
        return jsonify({"message": log_info_return_str(f"Video already exists at {video_save_path}, skip downloading."), "video_id": video_id}), 200

    exception = None
    try:
        yt = YouTube(f'https://www.youtube.com/watch?v={video_id}', proxies=None)
        video  = yt.streams.filter(progressive=True).last()
        video.download(output_path=output_path, filename=video_fn)
        return jsonify({"message": log_info_return_str(f"Download video {video_id} to {video_save_path} successfully."), "video_id": video_id}), 200
    except Exception as e:
        exception = e

    return jsonify({"message": log_error_return_str(f'An error occurred while downloading video  {video_id} to {video_save_path}: {exception}')}), 500


@app.route('/yt/<video_id>', methods=['GET'])
def yt_serve(video_id):
    video_fn = f'{video_id}.mp4'

    if os.path.exists(os.path.join(output_path, video_fn)):
        return send_from_directory(output_path, video_fn, as_attachment=True)

    return jsonify({"message": log_warning_return_str(f'Video {video_fn} not found at {output_path}')}), 404
