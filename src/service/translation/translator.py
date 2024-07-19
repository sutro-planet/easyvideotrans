from abc import ABC, abstractmethod


class Translator(ABC):
    @abstractmethod
    def translate(self, content: list) -> list:
        pass
