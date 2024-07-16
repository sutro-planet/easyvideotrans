import os
from abc import ABC, abstractmethod

YOUTUBE_DOWNLOAD_PATH = "../../data/input_videos/youtube"


class Downloader(ABC):
    @abstractmethod
    def download(self, url):
        pass

    @abstractmethod
    def clean_up(self):
        pass


class YoutubeDownloader(Downloader):
    def __init__(self, logger=None):
        # Initialize any necessary resources or state
        directory = os.path.dirname(YOUTUBE_DOWNLOAD_PATH)
        if not os.path.exists(directory):
            os.makedirs(directory)
        self.logger = logger

    def download(self, url):
        # Implement downloading logic for YouTube videos
        print(f"Downloading video from YouTube: {url}")
        # Example: Use a library like youtube_dl to download videos

    def clean_up(self):
        # Implement clean-up logic if needed
        print("Cleaning up resources used by YouTube downloader")
        # Example: Close connections or release resources
