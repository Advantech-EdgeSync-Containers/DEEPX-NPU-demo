from abc import abstractmethod

from clip_demo_app_pyqt.common.base import Base


class Singleton(Base):
    _instances = {}

    def __new__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super(Singleton, cls).__new__(cls)
            cls._instances[cls] = instance
            instance._initialized = False  # 초기화 플래그 추가
        return cls._instances[cls]

    def __init__(self, *args, **kwargs):
        super().__init__()
        if not self._initialized:
            self.initialize(*args, **kwargs)
            self._initialized = True

    @abstractmethod
    def initialize(self, *args, **kwargs):
        pass
