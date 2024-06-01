import os
import unittest
import tempfile

from app import app


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
