import time

from src.service.video_synthesis.video_preview import zhVideoPreview
from src.task_manager.celery_tasks import celery_app

from prometheus_client import Counter, Histogram
from celery.exceptions import SoftTimeLimitExceeded

# Define Prometheus metrics
VIDEO_PREVIEW_TASK_INVOKED = Counter(
    'video_preview_task_invoked_total', 'Total number of times video preview task is invoked')
VIDEO_PREVIEW_TASK_FAILED = Counter(
    'video_preview_task_failed_total', 'Total number of times video preview task failed')
VIDEO_PREVIEW_TASK_SOFT_TIMEOUT = Counter(
    'video_preview_task_soft_timeout_total', 'Total number of times video preview task failed due to soft timeout')
VIDEO_PREVIEW_TASK_DURATION = Histogram(
    'video_preview_task_duration_seconds', 'Duration of video preview task in seconds')


@celery_app.task(bind=True)
def video_preview_task(self, video_path, voice_path, audio_bg_path, video_out_path):
    print(f"Invoke video preview task {self.request.id}.")
    VIDEO_PREVIEW_TASK_INVOKED.inc()
    start_time = time.time()

    try:
        _ = zhVideoPreview(None, video_path, voice_path, audio_bg_path,
                           "暂时没有处理字幕文件，所以随便写", video_out_path)
    except SoftTimeLimitExceeded as soft_exception:
        VIDEO_PREVIEW_TASK_SOFT_TIMEOUT.inc()
        print(f"Invoke video preview task {self.request.id} failed with soft timeout: {soft_exception}")
    except Exception as exception:
        VIDEO_PREVIEW_TASK_FAILED.inc()
        print(f"Invoke video preview task {self.request.id} failed with exception: {exception}")
    finally:
        duration = time.time() - start_time
        VIDEO_PREVIEW_TASK_DURATION.observe(duration)
        print(f"Invoke video preview task {self.request.id} took {duration:.2f} seconds.")
