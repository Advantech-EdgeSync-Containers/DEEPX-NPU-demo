from abc import ABCMeta

from PyQt5.QtCore import QObject


class Base(metaclass=ABCMeta):
    def __init__(self):
        pass


class CombinedMeta(type(QObject), type(Base)):
    pass
