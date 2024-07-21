from src.service.video_synthesis.video_preview import zhVideoPreview
from src.task_manager.celery_tasks import celery_app


@celery_app.task(bind=True)
def video_preview_task(self, video_path, voice_path, audio_bg_path, video_out_path):
    print(f"Invoke video preview task {self.request.id}.")
    _ = zhVideoPreview(None, video_path, voice_path, audio_bg_path,
                       "暂时没有处理字幕文件，所以随便写", video_out_path)
