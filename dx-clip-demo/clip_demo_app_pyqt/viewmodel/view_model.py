from PyQt5.QtCore import QObject

from clip_demo_app_pyqt.common.base import CombinedMeta, Base
from clip_demo_app_pyqt.model.model import Model


class ViewModel(QObject, Base, metaclass=CombinedMeta):
    def __init__(self, model: Model):
        QObject.__init__(self)
        Base.__init__(self)
        self._model = model