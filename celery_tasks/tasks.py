from celery_tasks import celery_app
from chattts import generate_audio
from work_space import zhVideoPreview


@celery_app.task(bind=True)
def chattts_task(self, text: str, spk_emb_text: str, file_name: str, temperature: float = 0.3, top_P: float = 0.7, top_K: int = 20):
    print(f"Invoke ChatTTS task {self.request.id}.")
    generate_audio(text, spk_emb_text, file_name, temperature, top_P, top_K)


@celery_app.task(bind=True)
def video_preview_task(self, video_path, voice_path, audio_bg_path, video_out_path):
    print(f"Invoke video preview task {self.request.id}.")
    _ = zhVideoPreview(None, video_path, voice_path, audio_bg_path,
                       "暂时没有处理字幕文件，所以随便写", video_out_path)
