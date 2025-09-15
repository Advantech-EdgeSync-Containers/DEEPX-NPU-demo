from clip_demo_app_pyqt.model.clip_model import ClipModel
from clip_demo_app_pyqt.viewmodel.sentence_view_model import SentenceViewModel
from clip_demo_app_pyqt.viewmodel.video_view_model import VideoViewModel


class ClipViewModel(SentenceViewModel, VideoViewModel):
    def __init__(self, model: ClipModel):
        SentenceViewModel.__init__(self, model)
        VideoViewModel.__init__(self, model)
