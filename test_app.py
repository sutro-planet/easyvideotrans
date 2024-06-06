import os
import unittest
import tempfile

from app import app
from app import url_rule_to_base


class PytvzhenUnitTest(unittest.TestCase):

    def test_video_url_rule_to_base_succeeds(self):
        assert url_rule_to_base("/videos/<video_id>") == "/videos"
        assert url_rule_to_base("/audio/<video_id>") == "/audio"
        assert url_rule_to_base("/audio_no_bg/<video_id>") == "/audio_no_bg"
        assert url_rule_to_base("/audio_bg/<video_id>") == "/audio_bg"
        assert url_rule_to_base("/srt_en/<video_id>") == "/srt_en"
        assert url_rule_to_base("/srt_en_merged/<video_id>") == "/srt_en_merged"
        assert url_rule_to_base("/srt_en/<video_id>") == "/srt_en"
        assert url_rule_to_base("/srt_zh_merged/<video_id>") == "/srt_zh_merged"
        assert url_rule_to_base("/voice_connect_log/<video_id>") == "/voice_connect_log"
        assert url_rule_to_base("/voice_connect/<video_id>") == "/voice_connect"
        assert url_rule_to_base("/tts/<video_id>") == "/tts"
        assert url_rule_to_base("/video_preview/<video_id>") == "/video_preview"

    def test_video_url_rule_to_base_succeeds_with_prefix(self):
        assert url_rule_to_base("/api/video_preview/<video_id>") == "/api/video_preview"


class PytvzhenAPITest(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        app.config['OUTPUT_PATH'] = self.test_dir
        app.config['DEBUG'] = True

        self.app = app.test_client()
        self.app.testing = True

    def test_download_yt_video_with_valid_video_id(self):
        print("download to " + self.test_dir)
        response = self.app.post("/yt_download", json={'video_id': 'VwhT-P3pLJs'})
        assert response.status_code == 200
        assert os.path.isfile(os.path.join(self.test_dir, 'VwhT-P3pLJs.mp4'))

    def tearDown(self):
        for root, dirs, files in os.walk(self.test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))


if __name__ == '__main__':
    unittest.main()
