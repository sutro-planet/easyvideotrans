import asyncio
import os
import unittest
import tempfile
import hashlib
from app import app
from app import url_rule_to_base

from src.service.tts.edge_tts import EdgeTTSClient
from src.service.tts.openai_tts import OpenAITTSClient
from src.service.tts import get_tts_client


class EasyVideoTransUnitTest(unittest.TestCase):

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

    async def success_coroutine(self, delay):
        await asyncio.sleep(delay)
        return f"coroutine completed after {delay} seconds"

    async def exception_coroutine(self, delay):
        await asyncio.sleep(delay)
        raise Exception(f"coroutine throws exception after {delay} seconds")

    def test_edge_tts_run_convert_srt_to_voice_edge_coroutines(self):
        coroutines = [self.success_coroutine(1), self.success_coroutine(2)]
        assert EdgeTTSClient._run_convert_srt_to_voice_edge_coroutines(coroutines) == 0

    def test_edge_tts_run_convert_srt_to_voice_edge_coroutines_cancel_pending_tasks_on_exception(self):
        coroutines = [self.success_coroutine(1), self.success_coroutine(2), self.exception_coroutine(3),
                      self.success_coroutine(4), self.success_coroutine(5)]
        assert EdgeTTSClient._run_convert_srt_to_voice_edge_coroutines(coroutines) == 2

    def test_tts_client_factory_edge(self):
        client = get_tts_client("edge", character="zh-CN-XiaoyiNeural")
        assert isinstance(client, EdgeTTSClient)
        assert client.character == "zh-CN-XiaoyiNeural"

    def test_tts_client_factory_openai(self):
        # Mock the OpenAI client to avoid requiring API key during test
        import unittest.mock
        with unittest.mock.patch('src.service.tts.openai_tts.OpenAI'), \
             unittest.mock.patch('src.service.tts.openai_tts.os.environ.get', return_value='fake-api-key'):
            client = get_tts_client("openai", voice="alloy", model="tts-1")
            assert isinstance(client, OpenAITTSClient)
            assert client.voice == "alloy"
            assert client.model == "tts-1"

    def test_tts_client_factory_openai_with_character(self):
        # Test that character parameter maps to voice for OpenAI
        import unittest.mock
        with unittest.mock.patch('src.service.tts.openai_tts.OpenAI'), \
             unittest.mock.patch('src.service.tts.openai_tts.os.environ.get', return_value='fake-api-key'):
            client = get_tts_client("openai", character="nova")
            assert isinstance(client, OpenAITTSClient)
            assert client.voice == "nova"

    def test_tts_client_factory_unknown_vendor(self):
        try:
            get_tts_client("unknown_vendor")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "Unknown TTS vendor" in str(e)


class EasyVideoTransAPITest(unittest.TestCase):

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

        app.config['OUTPUT_PATH'] = self.test_dir
        app.config['DEBUG'] = True

        self.app = app.test_client()
        self.app.testing = True

    def test_download_yt_video_with_valid_video_id(self):
        response = self.app.post("/yt_download", json={'video_id': 'VwhT-P3pLJs'})
        assert response.status_code == 200
        assert os.path.isfile(os.path.join(self.test_dir, 'VwhT-P3pLJs.mp4'))

    def test_download_yt_video_too_long(self):
        # video zv-TS_mEHE4 has length 1:13:17
        response = self.app.post("/yt_download", json={'video_id': "zv-TS_mEHE4"})
        assert response.status_code == 400, "should not be able to download long video"
        assert "Video duration is too long." in response.get_json()["message"]

    def test_download_yt_video_invalid_id(self):
        response = self.app.post("/yt_download", json={'video_id': "video-90097"})
        assert response.status_code == 500, "An error occurred while downloading video"

    def test_download_yt_video_pytube_issue(self):
        # https://stackoverflow.com/questions/71883661/pytube-error-get-throttling-function-name-could-not-find-match-for-multiple
        response = self.app.post("/yt_download", json={'video_id': 'SrvXsYxbgC4'})
        assert response.status_code != 500, "Pytube fix not applied, see https://github.com/pytube/pytube/pull/1312"
        assert response.status_code == 200

    def test_download_yt_thumbnail(self):
        response = self.app.post("/yt_thumbnail", json={'video_id': 'SrvXsYxbgC4'})
        expected_fn = os.path.join(self.test_dir, 'SrvXsYxbgC4_thumbnail.png')

        assert response.status_code == 200
        assert os.path.isfile(expected_fn), "thumbnail not downloaded and cached on server side"

        returned_sha = hashlib.sha256(response.data).hexdigest()

        with open(expected_fn, 'rb', buffering=0) as f:
            expected_sha = hashlib.sha256(f.read()).hexdigest()
            assert returned_sha == expected_sha, f"thumbnail doesn't match, expected {expected_sha} actual {returned_sha}"

    def tearDown(self):
        for root, dirs, files in os.walk(self.test_dir, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))


if __name__ == '__main__':
    unittest.main()
