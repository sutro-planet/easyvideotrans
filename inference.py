import os
import time
from pathlib import Path
import numpy as np
import soundfile as sf
import librosa
import torch
from functools import wraps
import threading
from workloads.task_scheduler import TaskScheduler, TaskStatus

from flask import Flask, request, jsonify
from prometheus_flask_exporter import PrometheusMetrics
from prometheus_client import Summary, Histogram, Gauge

from workloads.lib.separator import Separator
from workloads.lib import spec_utils, nets
from workloads.lib.audio_processing.transcribe_audio import transcribe_audio_en
from workloads.lib.srt import srt_sentense_merge

# Initialize the TaskScheduler
task_scheduler = TaskScheduler()

# Start TaskScheduler in a background thread
scheduler_thread = threading.Thread(target=task_scheduler.start, daemon=True)
scheduler_thread.start()

# Initialize the Flask app
app = Flask(__name__)

# Integrate Prometheus metrics
metrics = PrometheusMetrics(app)
metrics.info("app_info", "EasyVideoTrans GPU Workloads Processing API", version="1.0.0")

# Custom Prometheus metrics
INFERENCE_DURATION = Summary("inference_duration_seconds", "Time spent on inference")
TRANSCRIBE_DURATION = Summary("transcribe_duration_seconds", "Time spent on transcribe")
AUDIO_FILE_SIZE = Histogram(
    "audio_file_size_bytes",
    "Size of input audio files",
    buckets=[
        1024,
        2048,
        4096,
        8192,
        16384,
        32768,
        65536,
        131072,
        262144,
        524288,
        1048576,
        2097152,
        4194304,
        8388608,
    ],
)
CURRENT_INFERENCE = Gauge("current_inference", "Number of ongoing inferences")

# Model setup from https://github.com/tsurumeso/vocal-remover/tree/develop
MODEL_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "workloads/pretrained_models"
)
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "baseline.pth")

model = nets.CascadedNet(n_fft=2048, hop_length=1024, nout=32, nout_lstm=128)
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.load_state_dict(torch.load(DEFAULT_MODEL_PATH, map_location=device))
model.to(device)
separator = Separator(model, device, batchsize=4, cropsize=256, postprocess=False)

# Setup input / output configurations
INPUT_DIR = "workloads/static/outputs"
OUTPUT_DIR = "workloads/static/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def load_spectrogram(file_path):
    X, sample_rate = librosa.load(
        file_path, sr=44100, mono=False, dtype=np.float32, res_type="kaiser_fast"
    )

    if X.ndim == 1:
        # mono to stereo
        X = np.asarray([X, X])

    x_spec = spec_utils.wave_to_spectrogram(X, hop_length=1024, n_fft=2048)
    return x_spec, sample_rate


@app.route("/")
def index():
    """
    Health check endpoint.
    """
    return jsonify({"message": "Speech Separation API is running."}), 200


def require_filename_points_to_existing_file(func):
    @wraps(func)
    def decorated_func(*args, **kwargs):

        if not request.is_json:
            return jsonify({"message": "Missing JSON in request"}), 400

        data = request.get_json()
        if not data or "file_name" not in data:
            return (
                jsonify(
                    {
                        "error": "Invalid request. Please provide 'file_name' in the JSON payload."
                    }
                ),
                400,
            )

        # Get the file path from the payload
        file_name = data["file_name"]
        file_path = os.path.join(INPUT_DIR, file_name)

        if not os.path.exists(file_path):
            return jsonify({"error": f"File not found: {file_path}"}), 404

        return func(file_path, *args, **kwargs)

    return decorated_func


def require_output_filenames(func):
    @wraps(func)
    def decorated_func(file_path, *args, **kwargs):
        data = request.get_json()

        if "output_filenames" not in data:
            return (
                jsonify(
                    {
                        "error": "Invalid request. Please provide 'output_filenames' in the JSON payload."
                    }
                ),
                400,
            )

        output_filenames = data["output_filenames"]
        output_filepaths = [os.path.join(OUTPUT_DIR, name) for name in output_filenames]

        return func(file_path, output_filepaths, *args, **kwargs)

    return decorated_func


def perform_separation(file_path: str):
    """Task function for audio separation"""
    file_stem_name = Path(file_path).stem
    file_size = os.path.getsize(file_path)
    AUDIO_FILE_SIZE.observe(file_size)
    try:
        CURRENT_INFERENCE.inc()
        start_time = time.time()

        x_spec, sample_rate = load_spectrogram(file_path)
        app.logger.info(f"Done loading sound file: {file_path}")

        y_spec, v_spec = separator.separate_tta(x_spec)

        background_wave_fn = f"{file_stem_name}_bg.wav"
        voice_wave_fn = f"{file_stem_name}_no_bg.wav"
        background_wave_path = os.path.join(OUTPUT_DIR, background_wave_fn)
        voice_wave_path = os.path.join(OUTPUT_DIR, voice_wave_fn)

        wave = spec_utils.spectrogram_to_wave(y_spec)
        sf.write(background_wave_path, wave.T, int(sample_rate))
        app.logger.info(f"Done inversed stft for background")

        wave = spec_utils.spectrogram_to_wave(v_spec)
        sf.write(voice_wave_path, wave.T, int(sample_rate))
        app.logger.info(f"Done inversed stft for vocal")

        duration = time.time() - start_time
        INFERENCE_DURATION.observe(duration)

        return {
            "message": "Separation successful",
            "files": [background_wave_fn, voice_wave_fn],
            "inference_duration_seconds": duration,
            "input_audio_size_bytes": file_size,
        }
    finally:
        CURRENT_INFERENCE.dec()


@app.route("/audio_sep", methods=["POST"])
@require_filename_points_to_existing_file
def submit_audio_separation(file_path):
    """Submit audio separation task to the scheduler"""
    try:
        # Submit task with 30 minute timeout and 2 retries
        task_id = task_scheduler.add_task(
            func=perform_separation,
            timeout=300,  # 5 minutes
            max_retry=1,
            args=(file_path,),
        )

        return (
            jsonify({"message": "Task submitted successfully", "task_id": task_id}),
            202,
        )  # 202 Accepted

    except Exception as e:
        return jsonify({"error": f"Failed to submit task: {str(e)}"}), 500


@app.route("/audio_sep_status", methods=["GET"])
def get_audio_separation_status():
    """Get the status of an audio separation task"""
    task_id = request.args.get("task_id")

    if not task_id:
        return jsonify({"error": "task_id parameter is required"}), 400

    try:
        task_result = task_scheduler.get_task_result(task_id)
        if task_result.status == TaskStatus.NOT_FOUND:
            return jsonify({"error": "Task not found"}), 404

        response = {
            "task_id": task_id,
            "status": task_result.status,
            "data": (
                task_result.output
                if task_result.status == TaskStatus.FINISHED
                else None
            ),
            "error": (
                task_result.err_message
                if task_result.status == TaskStatus.FAILED
                else None
            ),
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get task status: {str(e)}"}), 500


def perform_audio_transcribe(file_path: str, output_filepaths: list):
    """Task function for audio transcription"""
    try:
        CURRENT_INFERENCE.inc()
        start_time = time.time()

        en_srt_path, en_srt_merged_path = output_filepaths
        transcribe_audio_en(
            app.logger,
            path=file_path,
            modelName="medium",
            language="en",
            srtFilePathAndName=en_srt_path,
        )
        srt_sentense_merge(app.logger, en_srt_path, en_srt_merged_path)

        duration = time.time() - start_time
        TRANSCRIBE_DURATION.observe(duration)

        return {
            "message": "Transcribe successful",
            "output_files": [os.path.basename(p) for p in output_filepaths],
            "transcribe_duration_seconds": duration,
        }
    finally:
        CURRENT_INFERENCE.dec()


@app.route("/audio_transcribe", methods=["POST"])
@require_filename_points_to_existing_file
@require_output_filenames
def audio_transcribe(file_path, output_filepaths):
    """Submit audio transcribe task to the scheduler"""
    try:
        # Submit task with 1 hour timeout and 1 retry
        task_id = task_scheduler.add_task(
            func=perform_audio_transcribe,
            timeout=3600,  # 1 hour
            max_retry=1,
            args=(file_path, output_filepaths),
        )

        return (
            jsonify(
                {
                    "message": "Transcription task submitted successfully",
                    "task_id": task_id,
                }
            ),
            202,
        )  # 202 Accepted

    except Exception as e:
        return jsonify({"error": f"Failed to submit transcription task: {str(e)}"}), 500


@app.route("/audio_transcribe_status", methods=["GET"])
def get_audio_transcribe_status():
    """Get the status of an audio transcription task"""
    task_id = request.args.get("task_id")

    if not task_id:
        return jsonify({"error": "task_id parameter is required"}), 400

    try:
        task_result = task_scheduler.get_task_result(task_id)
        if task_result.status == TaskStatus.NOT_FOUND:
            return jsonify({"error": "Task not found"}), 404

        response = {
            "task_id": task_id,
            "status": task_result.status.value,
            "data": (
                task_result.output
                if task_result.status == TaskStatus.FINISHED
                else None
            ),
            "error": (
                task_result.err_message
                if task_result.status == TaskStatus.FAILED
                else None
            ),
        }
        return jsonify(response), 200

    except Exception as e:
        return jsonify({"error": f"Failed to get task status: {str(e)}"}), 500


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8199)
