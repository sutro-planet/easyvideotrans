import logging
from datetime import datetime


class Logger:
    _instance = None

    def __new__(cls, log_path=None):
        if not cls._instance:
            cls._instance = super().__new__(cls)
            cls._instance.log_path = log_path
            # create a log path if it's none
            if log_path is None:
                cls._instance.log_path = "data/logs" + datetime.now().strftime("%Y%m%d%H%M") + ".log"
            cls._instance._logger = cls._instance._create_logger(cls._instance)
        return cls._instance

    @staticmethod
    def _create_logger(self):
        logger = logging.getLogger("name")
        logger.setLevel(logging.DEBUG)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')

        file_handler = logging.FileHandler(self.log_path)
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)

        logger.addHandler(file_handler)

        return logger

    @property
    def logger(self):
        return self._logger
