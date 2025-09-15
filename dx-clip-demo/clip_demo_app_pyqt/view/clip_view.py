import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import List

import qdarkstyle
from PyQt5.QtCore import Qt, QObject, QEvent, QUrl, QTimer
from PyQt5.QtGui import QPixmap, QFont, QColor, QMovie, QFontMetrics
from PyQt5.QtMultimedia import QMediaPlayer, QMediaContent
from PyQt5.QtMultimediaWidgets import QVideoWidget
from PyQt5.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QMainWindow, QLineEdit, \
    QHBoxLayout, QGridLayout, QDialog, QScrollArea, QDoubleSpinBox, QGroupBox, QCheckBox, QComboBox, QFileDialog, \
    QSizePolicy
from overrides import overrides
from pyqttoast import ToastPreset, ToastPosition, Toast

from clip_demo_app_pyqt.common.base import CombinedMeta, Base
from clip_demo_app_pyqt.common.constants import *
from clip_demo_app_pyqt.data.input_data import InputData
from clip_demo_app_pyqt.model.sentence_model import Sentence
from clip_demo_app_pyqt.view.settings_view import MergedVideoGridInfo
from clip_demo_app_pyqt.viewmodel.clip_view_model import ClipViewModel
from clip_demo_app_pyqt.common.config.ui_config import UIHelper, UIConfig
from clip_demo_app_pyqt.view.multithreading.clip_video_consumer import ClipVideoConsumer
from clip_demo_app_pyqt.view.multithreading.video_producer import VideoProducer
from clip_demo_app_pyqt.view.multithreading.video_worker import VideoWorker


class CustomToastPosition(Enum):
    MIDDLE_LEFT = 98
    MIDDLE_RIGHT = 99


class VideoToast(QDialog):
    def __init__(self, title, media_path, position, parent=None):
        super().__init__(parent)
        self.__duration = 5000
        self.__parent = parent
        self.__media_path = media_path
        self.__position = position

        self.setWindowTitle(title)
        self.setFixedSize(360, 360)

        self.__layout = QVBoxLayout(self)

        self.__file_extension = os.path.splitext(media_path)[1].lower()
        if self.__file_extension == ".gif":
            self.__init_gif_player(media_path)
        else:
            self.__init_video_player(media_path)

        # Timer for hiding the notification after set duration
        self.__duration_timer = QTimer(self)
        self.__duration_timer.setSingleShot(True)
        self.__duration_timer.timeout.connect(self.hide)

        self.__set_dialog_position()

    def __init_gif_player(self, media_path):
        """
        Initialize the dialog to use QMovie for GIF playback.
        """
        if media_path == "":
            return

        self.__video_label = QLabel(self)
        self.__video_label.setAlignment(Qt.AlignCenter)
        self.__layout.addWidget(self.__video_label)

        self.__movie = QMovie(media_path)
        self.__video_label.setMovie(self.__movie)

        # Close dialog when GIF playback finishes
        self.__movie.finished.connect(self.close)

    def __init_video_player(self, media_path):
        """
        Initialize the dialog to use QMediaPlayer for video playback.
        """
        if media_path == "":
            return

        self.video_widget = QVideoWidget(self)
        self.__layout.addWidget(self.video_widget)

        self.__player = QMediaPlayer(self)
        self.__player.setVideoOutput(self.video_widget)
        self.__player.setMedia(QMediaContent(QUrl.fromLocalFile(os.path.abspath(media_path))))

        # Close dialog when video playback finishes
        self.__player.mediaStatusChanged.connect(self.handle_media_status)

    def __set_dialog_position(self):
        screen = self.screen().availableGeometry()
        width = screen.width()
        height = screen.height()
        dialog_width = self.width()
        dialog_height = self.height()

        if self.__position == ToastPosition.TOP_RIGHT:
            x = width - dialog_width
            y = 0
        elif self.__position == ToastPosition.TOP_MIDDLE:
            x = (width - dialog_width) // 2
            y = 0
        elif self.__position == ToastPosition.TOP_LEFT:
            x = 0
            y = 0
        elif self.__position == ToastPosition.BOTTOM_RIGHT:
            x = width - dialog_width
            y = height - dialog_height
        elif self.__position == ToastPosition.BOTTOM_MIDDLE:
            x = (width - dialog_width) // 2
            y = height - dialog_height
        elif self.__position == ToastPosition.BOTTOM_LEFT:
            x = 0
            y = height - dialog_height
        elif self.__position == CustomToastPosition.MIDDLE_RIGHT:
            x = width - dialog_width
            y = (height - dialog_height) // 2
        elif self.__position == ToastPosition.CENTER:
            x = (width - dialog_width) // 2
            y = (height - dialog_height) // 2
        elif self.__position == CustomToastPosition.MIDDLE_LEFT:
            x = 0
            y = (height - dialog_height) // 2

        self.move(x, y)

    def show(self):
        """
        Display the VideoToast and start playback.
        """
        if self.__media_path != "":
            if self.__file_extension == ".gif":  # If using QMovie
                self.__movie.start()
            else:  # If using QMediaPlayer
                self.__player.play()
        super(VideoToast, self).show()

        # Start duration timer
        if self.__duration != 0:
            self.__duration_timer.start(self.__duration)

    def handle_media_status(self, status):
        """
        Close the dialog when video playback ends.
        """
        if status == QMediaPlayer.EndOfMedia:
            self.close()

    def closeEvent(self, event):
        """
        Stop playback when the dialog is closed.
        """
        if self.__file_extension == ".gif" and self.__movie:
            self.__movie.stop()
        elif self.__player:
            self.__player.stop()
        event.accept()

        if self.__parent:
            self.__parent.is_opened_media_alert = False

    def setDuration(self, duration: int):
        """
        Set the duration of the toast
        :param duration: duration in milliseconds
        """
        self.__duration = duration

    def hide(self):
        """Start hiding process of the toast notification"""
        if self.__duration != 0:
            self.__duration_timer.stop()
            self.close()


class LoadingOverlay(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background-color: rgba(0, 0, 0, 128);")
        self.setAttribute(Qt.WA_TransparentForMouseEvents, False)
        self.label = QLabel("Loading...", self)
        self.label.setStyleSheet("color: white; font-size: 16px;")

    def resizeEvent(self, event):
        self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self.label.move(self.width() // 2 - self.label.width() // 2, self.height() // 2 - self.label.height() // 2)
        super().resizeEvent(event)


class AddSentenceDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Add Sentence")
        self.setModal(True)

        # sentence input
        self.sentence_input = QLineEdit(self)
        self.sentence_input.setMinimumWidth(parent.ui_config.sentence_input_min_width)
        self.sentence_input.setPlaceholderText("Please enter a sentence.")

        # Score Settings
        # score settings input
        decimals = UIConfig.score_settings_decimals
        single_step = UIConfig.score_settings_single_step

        score_settings_box = QHBoxLayout()
        score_min_label = QLabel("Min:", self)
        input_data = InputData()
        self.score_min_input = QDoubleSpinBox(self)
        self.score_min_input.setDecimals(decimals)
        self.score_min_input.setValue(input_data.get_default_sentence_score_min())
        self.score_min_input.setSingleStep(single_step)

        score_max_label = QLabel("Max:", self)
        self.score_max_input = QDoubleSpinBox(self)
        self.score_max_input.setDecimals(decimals)
        self.score_max_input.setValue(input_data.get_default_sentence_score_max())
        self.score_max_input.setSingleStep(single_step)

        score_threshold_label = QLabel("Threshold:", self)
        self.score_threshold_input = QDoubleSpinBox(self)
        self.score_threshold_input.setDecimals(decimals)
        self.score_threshold_input.setValue(input_data.get_default_sentence_score_threshold())
        self.score_threshold_input.setSingleStep(single_step)

        score_settings_box.addWidget(score_min_label)
        score_settings_box.addWidget(self.score_min_input)
        score_settings_box.addWidget(score_max_label)
        score_settings_box.addWidget(self.score_max_input)
        score_settings_box.addWidget(score_threshold_label)
        score_settings_box.addWidget(self.score_threshold_input)

        alarm_settings_box = QHBoxLayout()
        self.alarm_checkbox = QCheckBox("On", self)
        self.alarm_title_input = QLineEdit(self)
        self.alarm_title_input.setMinimumWidth(parent.ui_config.alarm_title_input_min_width)
        self.alarm_title_input.setPlaceholderText("Alarm Title")
        self.alarm_color_combobox = QComboBox(self)
        self.alarm_color_combobox.addItems(COLOR_DICT.keys())
        self.alarm_position_combobox = QComboBox(self)
        self.alarm_position_combobox.addItems(POSITION_DICT.keys())
        self.alarm_position_combobox.setCurrentText("BOTTOM_MIDDLE")

        alarm_settings_box.addWidget(self.alarm_checkbox)
        alarm_settings_box.addWidget(self.alarm_title_input)
        alarm_settings_box.addWidget(self.alarm_color_combobox)
        alarm_settings_box.addWidget(self.alarm_position_combobox)

        media_alarm_settings_box = QVBoxLayout()

        media_alarm_settings = QHBoxLayout()
        self.media_alarm_checkbox = QCheckBox("On", self)
        self.media_alarm_title_input = QLineEdit(self)
        self.media_alarm_title_input.setPlaceholderText("Media Alarm Title")
        self.media_alarm_position_combobox = QComboBox(self)
        self.media_alarm_position_combobox.addItems(POSITION_DICT.keys())
        self.media_alarm_position_combobox.setCurrentText("CENTER")
        self.media_select_button = QPushButton("Select Media File")
        self.media_alarm_media_path_input = QLineEdit(STR_SELECTED_FILE_WILL_BE_DISPLAYED)
        self.media_alarm_media_path_input.setEnabled(False)

        media_alarm_settings.addWidget(self.media_alarm_checkbox)
        media_alarm_settings.addWidget(self.media_alarm_title_input)
        media_alarm_settings.addWidget(self.media_alarm_position_combobox)
        media_alarm_settings_box.addLayout(media_alarm_settings)
        media_alarm_settings_box.addWidget(self.media_select_button)
        media_alarm_settings_box.addWidget(self.media_alarm_media_path_input)

        # Layout configuration
        settings_box = QVBoxLayout()

        ui_sentence_box = QGroupBox("Sentence Settings")
        ui_sentence_layout = QVBoxLayout()
        ui_sentence_layout.addWidget(self.sentence_input)
        ui_sentence_box.setLayout(ui_sentence_layout)
        settings_box.addWidget(ui_sentence_box)

        ui_score_box = QGroupBox("Score Settings")
        ui_score_layout = QVBoxLayout()
        ui_score_layout.addLayout(score_settings_box)
        ui_score_box.setLayout(ui_score_layout)
        settings_box.addWidget(ui_score_box)

        ui_alarm_box = QGroupBox("Alarm Settings")
        ui_alarm_layout = QVBoxLayout()
        ui_alarm_layout.addLayout(alarm_settings_box)
        ui_alarm_box.setLayout(ui_alarm_layout)
        settings_box.addWidget(ui_alarm_box)

        ui_media_alarm_box = QGroupBox("Media Alarm Settings")
        ui_media_alarm_layout = QVBoxLayout()
        ui_media_alarm_layout.addLayout(media_alarm_settings_box)
        ui_media_alarm_box.setLayout(ui_media_alarm_layout)
        settings_box.addWidget(ui_media_alarm_box)

        # Add Cancel and Submit buttons
        button_box = QHBoxLayout()
        cancel_button = QPushButton("Cancel", self)
        submit_button = QPushButton("Submit", self)
        button_box.addWidget(cancel_button)
        button_box.addWidget(submit_button)

        settings_box.addLayout(button_box)
        self.setLayout(settings_box)

        # Connect button actions
        cancel_button.disconnect()
        cancel_button.clicked.connect(self.reject)
        submit_button.disconnect()
        submit_button.clicked.connect(self.accept)
        self.media_select_button.disconnect()
        self.media_select_button.clicked.connect(self.__open_file_dialog)

        # Connect sentence input enter key event
        self.sentence_input.disconnect()
        self.sentence_input.returnPressed.connect(self.accept)  # enter key
        self.score_min_input.disconnect()
        self.score_min_input.installEventFilter(self)
        self.score_max_input.disconnect()
        self.score_max_input.installEventFilter(self)
        self.score_threshold_input.disconnect()
        self.score_threshold_input.installEventFilter(self)

    def __open_file_dialog(self):
        # Check if base_path is valid
        initial_path = "" if self.parent is None or self.parent.base_path is None else os.path.join(
            self.parent.base_path, "media")

        # Open file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select File",                # Dialog title
            initial_path,
            "Gif Files (*.gif)"
#            "All Files (*);;"
#            "MP3 Files (*.mp3);;MP4 Files (*.mp4);;AVI Files (*.avi);;MOV Files (*.mov);;"
#            "FLV Files (*.flv);;WMV Files (*.wmv);;MKV Files (*.mkv);;WEBM Files (*.webm)"
# Filter
        )

        if file_path:
            self.media_alarm_media_path_input.setText(f"{file_path}")
        else:
            self.media_alarm_media_path_input.setText(STR_NO_FILE_SELECTED)

    def eventFilter(self, obj: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                self.accept()
                return True
        return super().eventFilter(obj, event)

    def get_sentence_input_text(self):
        return self.sentence_input.text()

    def get_score_min_input_value(self):
        return self.score_min_input.value()

    def get_score_max_input_value(self):
        return self.score_max_input.value()

    def get_score_threshold_input_value(self):
        return self.score_threshold_input.value()

    def get_alarm_checked(self) -> bool:
        return self.alarm_checkbox.isChecked()

    def get_alarm_title_input_text(self) -> str:
        return self.alarm_title_input.text()

    def get_alarm_position(self) -> int:
        return POSITION_DICT[self.alarm_position_combobox.currentText()]

    def get_alarm_color(self) -> str:
        return COLOR_DICT[self.alarm_color_combobox.currentText()]

    def get_media_alarm_checked(self) -> bool:
        return self.media_alarm_checkbox.isChecked()

    def get_media_alarm_title_input_text(self) -> str:
        return self.media_alarm_title_input.text()

    def get_media_alarm_media_path_label_text(self) -> str:
        if self.media_alarm_media_path_input.text() == STR_NO_FILE_SELECTED:
            return ""
        elif self.media_alarm_media_path_input.text() == STR_SELECTED_FILE_WILL_BE_DISPLAYED:
            return ""
        else:
            return self.media_alarm_media_path_input.text()

    def get_media_alarm_position(self) -> int:
        return POSITION_DICT[self.media_alarm_position_combobox.currentText()]


class ModifySentenceDialog(AddSentenceDialog):
    def __init__(self, sentence, score_min, score_max, score_threshold,
                 alarm, alarm_title, alarm_position, alarm_color,
                 media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position,
                 parent=None):
        super().__init__(parent)
        self.setWindowTitle("Modify Sentence")

        # set previous sentence data
        self.sentence_input.setText(sentence.get_text())
        self.score_min_input.setValue(score_min)
        self.score_max_input.setValue(score_max)
        self.score_threshold_input.setValue(score_threshold)

        self.alarm_checkbox.setChecked(alarm)
        self.alarm_title_input.setText(alarm_title)
        self.alarm_position_combobox.setCurrentText(POSITION_DICT_REVERSE[alarm_position])
        self.alarm_color_combobox.setCurrentText(COLOR_DICT_REVERSE[alarm_color])

        self.media_alarm_checkbox.setChecked(media_alarm)
        self.media_alarm_title_input.setText(media_alarm_title)
        self.media_alarm_media_path_input.setText(media_alarm_media_path)
        self.media_alarm_position_combobox.setCurrentText(POSITION_DICT_REVERSE[media_alarm_position])


class ClipView(Base, QMainWindow, metaclass=CombinedMeta):
    def __init__(self, view_model: ClipViewModel, ui_config: UIConfig, base_path, adjusted_video_path_lists,
                 adjusted_video_grid_info):
        QMainWindow.__init__(self)
        QObject.__init__(self)
        self.root_layout = None
        self.prev_app_layout_container = None
        self.prev_app_layout = None
        self.is_opened_dialog = False
        self.is_opened_media_alert = False

        self.loading_overlay = LoadingOverlay(self)
        self.loading_overlay.hide()

        self.__fps_lock = threading.Lock()
        self.__view_model = view_model

        self.base_path = base_path
        self.adjusted_video_path_lists = adjusted_video_path_lists
        self.adjusted_video_grid_info: MergedVideoGridInfo = adjusted_video_grid_info
        self.ui_config = ui_config

        # self.ui_helper = UIHelper(self, self.ui_config, window_w=1920, window_h=1080)
        self.ui_helper = UIHelper(self, self.ui_config, window_w=1920, window_h=1080)

        self.setWindowTitle("Video Processing App")

        if self.ui_config.dark_theme:
            self.setStyleSheet(qdarkstyle.load_stylesheet_pyqt5())

        # List for calculating overall FPS
        self.each_fps_info_list = []

        # Widget initialization
        self.each_fps_label_list: List[QLabel] = []
        self.video_label_list: List[QLabel] = []
        self.sentence_output_layout_list: List[QVBoxLayout] = []

        self.sentence_list_label = QLabel("[Sentence List]")

        self.sentence_list_layout = QVBoxLayout()
        self.sentence_widget = QWidget()
        self.sentence_widget.setLayout(self.sentence_list_layout)

        self.sentence_list_scroll_area = QScrollArea()
        self.sentence_list_scroll_area.setWidget(self.sentence_widget)
        self.sentence_list_scroll_area.setWidgetResizable(True)
        self.sentence_list_scroll_area.setMinimumHeight(self.ui_config.sentence_list_scroll_area_min_height)
        self.sentence_list_scroll_area.setMinimumWidth(self.ui_config.sentence_list_scroll_area_min_width)
                                            
        # QLabel initialization (FPS display)
        self.overall_fps_label = QLabel("FPS: N/A", self)
        self.overall_fps_label.setAlignment(Qt.AlignRight)

        # QPushButton initialization (start and stop video)
        self.show_settings_button = QPushButton("Settings", self)
        self.resume_button = QPushButton("Resume", self)
        self.pause_button = QPushButton("Pause", self)

        self.show_settings_button.setCheckable(True)
        self.show_settings_button.setChecked(self.ui_config.settings_mode)

        self.show_percentage_button = QPushButton("Percent", self)
        self.show_percentage_button.setCheckable(True)
        self.show_percentage_button.setChecked(self.ui_config.show_percent)

        self.show_score_button = QPushButton("Score", self)
        self.show_score_button.setCheckable(True)
        self.show_score_button.setChecked(self.ui_config.show_score)

        self.alarm_only_on_camera_ch_button = QPushButton("Alarm only on camera")
        self.alarm_only_on_camera_ch_button.setCheckable(True)
        self.alarm_only_on_camera_ch_button.setChecked(self.ui_config.alarm_only_on_camera_ch)

        self.camera_switch_button = QPushButton("Camera ON")
        self.camera_switch_button.setCheckable(True)
        self.camera_switch_button.setChecked(self.ui_config.camera_switch)

        # QPushButton initialization (text add and delete)
        self.add_button = QPushButton("Add", self)
        self.reset_button = QPushButton("Reset", self)
        self.clear_button = QPushButton("Clear", self)

        # Connect button events
        self.resume_button.disconnect()
        self.resume_button.clicked.connect(self.resume)
        self.pause_button.disconnect()
        self.pause_button.clicked.connect(self.pause)
        self.show_settings_button.disconnect()
        self.show_settings_button.clicked.connect(self.__toggle_settings)
        self.show_percentage_button.disconnect()
        self.show_percentage_button.clicked.connect(self.__toggle_percent)
        self.show_score_button.disconnect()
        self.show_score_button.clicked.connect(self.__toggle_score)
        self.alarm_only_on_camera_ch_button.disconnect()
        self.alarm_only_on_camera_ch_button.clicked.connect(self.__toggle_alarm_only_on_camera_ch)
        self.camera_switch_button.disconnect()
        self.camera_switch_button.clicked.connect(self.__toggle_camera_switch)

        self.add_button.disconnect()
        self.add_button.clicked.connect(self.open_add_sentence_dialog)
        self.reset_button.disconnect()
        self.reset_button.clicked.connect(self.reset_text_list)
        self.clear_button.disconnect()
        self.clear_button.clicked.connect(self.clear_text_list)

        # Connect sentence input updated event
        self.__view_model.get_sentence_list_updated_signal().connect(self.refresh_sentence_list)

        self.__layout_setup()

        # Producer & Consumer config
        self.__producer_futures = []
        self.__consumer_futures = []
        self.__producer_thread_pool_executor = ThreadPoolExecutor(max_workers=self.ui_config.max_producer_worker)
        self.__consumer_thread_pool_executor = ThreadPoolExecutor(max_workers=self.ui_config.max_consumer_worker)

        self.__video_worker_list: List[VideoWorker] = []
        self.__running_video_worker = False
        self.__pause_video_worker = False
        self.__setup_video_worker_list()

        self.start()
        self.refresh_sentence_list()

        self.resize(self.ui_helper.video_area_w, self.ui_helper.video_area_h)

        if self.ui_config.fullscreen_mode:
            self.showFullScreen()
        
        # init for video resize resolution
        self._refresh_video_size()

    def show_loading(self):
        if self.loading_overlay:
            self.loading_overlay.show()

    def hide_loading(self):
        if self.loading_overlay:
            self.loading_overlay.hide()

    @overrides()
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._refresh_video_size()

    def _refresh_video_size(self):
        if self.__video_worker_list:
            for video_worker in self.__video_worker_list:
                ratio = 0.90
                new_size = self.video_label_list[video_worker.get_channel_idx()].size()
                video_worker.get_video_producer().set_video_label_size(
                    (int(round(new_size.width() * ratio)), int(round(new_size.height() * ratio))))

    def __setup_video_worker_list(self):
        for channel_idx in range(self.ui_config.num_channels):
            sentence_list_updated_signal = self.__view_model.get_sentence_list_updated_signal()
            video_producer = VideoProducer(
                channel_idx,
                self.base_path,
                self.adjusted_video_path_lists[channel_idx],
                self.ui_helper.video_size,
                self.ui_config.producer_video_fps_sync_mode,
                self.ui_config.producer_video_frame_skip_interval,
                sentence_list_updated_signal,
            )

            [scaled_video_frame_updated_signal, video_source_changed_signal] = video_producer.get_video_frame_updated_signal()
            scaled_video_frame_updated_signal.connect(self.update_scaled_video_frame)

            video_consumer = ClipVideoConsumer(channel_idx, self.ui_config.number_of_alarms,
                                               video_source_changed_signal,
                                               sentence_list_updated_signal,
                                               self.ui_config.consumer_num_of_inference_per_sec,
                                               self.ui_config.consumer_max_np_array_similarity_queue,
                                               self.ui_config.consumer_video_fps_sync_mode,
                                               self.ui_config.inference_engine_async_mode,
                                               self.__view_model)

            video_consumer.get_update_each_fps_signal().connect(self.update_each_fps)
            video_consumer.get_update_overall_fps_signal().connect(self.update_overall_fps)
            video_consumer.get_update_sentence_output_signal().connect(self.update_sentence_output)
            video_consumer.get_clear_sentence_output_signal().connect(self.clear_sentence_output)

            video_worker = VideoWorker(channel_idx, video_producer, video_consumer)
            self.__video_worker_list.append(video_worker)

    def __layout_setup(self):
        # 루트 위젯과 레이아웃을 한 번만 생성
        if not hasattr(self, "root_widget"):
            self.top_panel_layout = QVBoxLayout()
            self.top_panel_layout.addLayout(self.generate_control_ui())
            self.description_widget = self.generate_description_box(content_type="image")
            # self.logo_widget = self.generate_logo_box()

            if self.ui_helper.is_portrait:
                self.main_panel_layout = QVBoxLayout()
                self.main_panel_layout.setContentsMargins(0, 0, 0, 0)
                self.main_panel_layout.setSpacing(0)
                self.main_panel_layout.addWidget(self.description_widget)
                # self.main_panel_layout.addWidget(self.logo_widget)
                self.main_panel_layout.addLayout(self.top_panel_layout)
            else:
                self.main_panel_layout = QHBoxLayout()

            self.main_panel_layout.addLayout(self.generate_video_box())

            self.root_widget = QWidget()
            self.root_layout = QVBoxLayout(self.root_widget)

            if self.ui_helper.is_portrait:
                self.root_layout.setContentsMargins(0, 0, 0, 0)
                self.root_layout.setSpacing(0)
                self.settings_box_widget = self.generate_settings_box(fixed_height=500)

                self.root_layout.addLayout(self.main_panel_layout)
                self.root_layout.addWidget(self.settings_box_widget)
            else:
                self.settings_box_widget = self.generate_settings_box()

                self.root_layout.addLayout(self.top_panel_layout)
                self.main_panel_layout.addWidget(self.settings_box_widget)
                self.root_layout.addLayout(self.main_panel_layout)

            self.setCentralWidget(self.root_widget)

        # settings_mode에 따라 settings_box의 표시 여부만 조정
        self.settings_box_widget.setVisible(self.ui_config.settings_mode)

    def __toggle_settings(self):
        # settings_mode 토글
        self.ui_config.settings_mode = not self.ui_config.settings_mode
        # 레이아웃 업데이트
        self.__layout_setup()

    def generate_settings_box(self, fixed_height=-1):
        # settings layout
        # [Sentence List]
        # [add] | [clr]
        # --------------------------------
        # [sentence list area]
        # ...
        # --------------------------------
        settings_box = QVBoxLayout()
        input_control_box = QHBoxLayout()
        input_control_box.addWidget(self.add_button)
        input_control_box.addWidget(self.reset_button)
        input_control_box.addWidget(self.clear_button)
        settings_box.addLayout(input_control_box)
        settings_box.addWidget(self.sentence_list_label)
        settings_box.addWidget(self.sentence_list_scroll_area)

        settings_box_widget = QWidget()
        if fixed_height != -1:
            settings_box_widget.setFixedHeight(fixed_height)
        settings_box_widget.setLayout(settings_box)

        return settings_box_widget

    def generate_control_ui(self):
        # [resume] or [pause] | [fps info] | [exit]
        control_box = QHBoxLayout()

        ui_toggle_box = QGroupBox("UI Setting")
        ui_toggle_layout = QHBoxLayout()
        ui_toggle_layout.addWidget(self.show_percentage_button)
        ui_toggle_layout.addWidget(self.show_score_button)
        ui_toggle_layout.addWidget(self.alarm_only_on_camera_ch_button)
        if self.ui_config.camera_mode:
            ui_toggle_layout.addWidget(self.camera_switch_button)
        ui_toggle_box.setLayout(ui_toggle_layout)
        control_box.addWidget(ui_toggle_box)

        fps_box = QGroupBox("FPS info")
        fps_layout = QHBoxLayout()
        fps_layout.addWidget(self.overall_fps_label)
        fps_box.setLayout(fps_layout)
        control_box.addWidget(fps_box)

        app_control_box = QGroupBox("App Control")
        app_control_layout = QHBoxLayout()
        app_control_layout.addWidget(self.show_settings_button)
        app_control_layout.addWidget(self.resume_button)
        app_control_layout.addWidget(self.pause_button)

        if self.ui_config.fullscreen_mode:
            exit_button = QPushButton("Exit", self)
            exit_button.disconnect()
            exit_button.clicked.connect(self.close_application)
            app_control_layout.addWidget(exit_button)

        app_control_box.setLayout(app_control_layout)
        control_box.addWidget(app_control_box)

        return control_box

    @staticmethod
    def generate_logo_box():
        image_label = QLabel()
        pixmap = QPixmap("clip_demo_app_pyqt/res/LGUP_BI.svg")
        image_label.setPixmap(pixmap)
        image_label.setScaledContents(True)
        image_label.setFixedSize(140, 45)
        return image_label

    @staticmethod
    def generate_description_box(content_type="image"):
        if content_type == "image":
            image_label = QLabel()
            pixmap = QPixmap("clip_demo_app_pyqt/res/LGUP_top_banner.png")

            # QLabel 크기를 부모 위젯 (description_widget)에 맞게 자동 조정
            image_label.setPixmap(pixmap)
            image_label.setScaledContents(True)  # 이미지가 QLabel 크기에 맞게 자동 조정
            image_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)  # 부모 위젯 크기를 따름

            # 레이아웃 설정 (여백과 간격을 없앰)
            description_box = QVBoxLayout()
            description_box.setContentsMargins(0, 0, 0, 0)
            description_box.setSpacing(0)
            description_box.addWidget(image_label)

            # 최상위 위젯 설정
            description_widget = QWidget()
            description_widget.setFixedSize(1080, 420)  # 원하는 크기로 고정
            description_widget.setLayout(description_box)

            return description_widget
        else:
            title_font = QFont()
            title_font.setBold(True)
            title_font.setPointSize(46)

            detail_font = QFont()
            detail_font.setPointSize(18)

            description_box = QVBoxLayout()

            description_title_label = QLabel("On-Device Vision AI")
            description_title_label.setFont(title_font)

            description_text = (
                "· Using low power(<5W) & High performance NPU\n"
                "· Enhanced Privacy - Sensitive Data stay on the device, ensure maximum security.\n"
                "· Contextual Scene understanding with vision-language model\n"
                "· Easy to make new surveillance scenario setup with prompt typing"
            )
            description_detail_label = QLabel(description_text)
            description_detail_label.setFont(detail_font)
            description_detail_label.setWordWrap(True)

            description_box.addWidget(description_title_label)
            description_box.addWidget(description_detail_label)

            description_widget = QWidget()
            description_widget.setFixedHeight(420)
            description_widget.setStyleSheet("background-color: hotpink; color: white; line-height: 1.5;")
            description_widget.setLayout(description_box)
        return description_widget

    def generate_video_box(self):
        if self.ui_config.num_channels == 1:
            return self.__generate_single_channel_video_box()
        elif self.ui_config.num_channels >= 2:
            # case of multi-channel
            return self.__generate_multi_channel_video_box()
        else:
            raise RuntimeError("num_channels value is not correct")

    def __generate_single_channel_video_box(self):
        # case of single-channel
        [video_layout, sentence_output_layout, video_label] = self.__generate_video_box_impl(
            self.ui_helper.large_font, self.ui_helper.large_font_line_height, self.ui_helper.large_font_bottom_padding)
        self.video_label_list.append(video_label)
        self.sentence_output_layout_list.append(sentence_output_layout)
        return video_layout

    def __generate_multi_channel_video_box(self):
        if self.ui_config.merge_central_grid:
            return self.__generate_video_grid_layout_for_merge_central_grid()
        else:
            return self.__setup_video_grid_layout()

    def __generate_video_grid_layout_for_merge_central_grid(self):
        video_grid_layout = QGridLayout()
        grid = self.adjusted_video_grid_info

        outer_channel_idx = 0
        for row in range(grid.grid_size):
            for col in range(grid.grid_size):
                # Skip the central area
                if grid.center_start <= row < grid.center_end and grid.center_start <= col < grid.center_end:
                    continue

                if outer_channel_idx >= grid.outer_channel_max:
                    break

                # Create outer channel layout
                [video_layout, sentence_output_layout, video_label] = self.__generate_video_box_impl(
                    self.ui_helper.small_font, self.ui_helper.small_font_line_height,
                    self.ui_helper.small_font_bottom_padding)

                video_grid_layout.addLayout(video_layout, row, col)
                self.sentence_output_layout_list.append(sentence_output_layout)
                self.video_label_list.append(video_label)
                outer_channel_idx += 1

        # Central camera channel layout
        [merged_center_grid_layout, merged_center_grid_sentence_output_layout,
         merged_center_grid_label] = self.__generate_video_box_impl(
            self.ui_helper.large_font, self.ui_helper.large_font_line_height,
            self.ui_helper.large_font_bottom_padding, border_color="yellow")

        # Add camera layout to the central area
        video_grid_layout.addLayout(merged_center_grid_layout, grid.center_start, grid.center_start,
                                    grid.center_size, grid.center_size)
        self.sentence_output_layout_list.append(merged_center_grid_sentence_output_layout)
        self.video_label_list.append(merged_center_grid_label)
        return video_grid_layout

    def __setup_video_grid_layout(self):
        video_grid_layout = QGridLayout()
        for i in range(self.ui_config.num_channels):
            border_color = "gray"
            if i+1 == self.ui_config.num_channels and self.ui_config.camera_mode:
                border_color = "yellow"

            [video_layout, sentence_output_layout, video_label] = self.__generate_video_box_impl(
                self.ui_helper.small_font, self.ui_helper.small_font_line_height,
                self.ui_helper.small_font_bottom_padding, border_color=border_color)

            video_grid_layout.addLayout(video_layout, i // self.ui_helper.grid_cols, i % self.ui_helper.grid_cols)

            self.sentence_output_layout_list.append(sentence_output_layout)
            self.video_label_list.append(video_label)
        return video_grid_layout

    def __generate_video_box_impl(self, font, font_line_height, font_bottom_padding, border_color="gray"):
        video_layout = QVBoxLayout()
        video_layout.setSpacing(0)

        video_label = QLabel(self)
        video_label.setAlignment(Qt.AlignCenter)
        video_label.setStyleSheet("border: 1px solid " + border_color + "; padding: 0px; border-radius: 5px;")
        video_label.setContentsMargins(0, 0, 0, 0)
        video_layout.addWidget(video_label)

        if self.ui_config.show_each_fps_label:
            each_fps_label = QLabel("FPS: N/A", self)
            each_fps_label.setFont(font)
            each_fps_label.setFixedHeight(font_line_height)
            each_fps_label.setAlignment(Qt.AlignRight)
            self.each_fps_label_list.append(each_fps_label)
            video_layout.addWidget(each_fps_label)
        self.each_fps_info_list.append({"dxnn_fps": -1, "sol_fps": -1})  # for calculate overall fps

        sentence_output_area, sentence_output_layout = self.__generate_sentence_output_area_impl(font_line_height, font_bottom_padding)
        video_layout.addWidget(sentence_output_area)
        return [video_layout, sentence_output_layout, video_label]

    def __generate_sentence_output_area_impl(self, font_line_height, font_bottom_padding):
        sentence_output_layout = QVBoxLayout()
        sentence_output_layout.setSpacing(0)
        sentence_output_layout.setContentsMargins(0, 0, 0, 0)
        sentence_output_widget = QWidget()
        sentence_output_widget.setLayout(sentence_output_layout)

        sentence_output_area = QScrollArea()
        sentence_output_area.setContentsMargins(0, 0, 0, 0)
        sentence_output_area.setWidget(sentence_output_widget)
        sentence_output_area.setWidgetResizable(True)
        sentence_output_area.setFixedHeight(
            font_line_height * self.ui_config.number_of_alarms + font_bottom_padding)
        sentence_output_area.setMinimumWidth(self.ui_helper.video_size[0])  # 너비 설정
        sentence_output_area.setAlignment(Qt.AlignCenter)
        sentence_output_area.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        sentence_output_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        return sentence_output_area, sentence_output_layout

    def worker_impl(self, channel_idx: int, worker_type: str, payload):
        video_worker = self.__video_worker_list[channel_idx]
        if worker_type == 'producer':
            payload = video_worker.get_video_producer().capture_frame()
            if payload is None:
                time.sleep(0.001)  # Adding a small sleep to avoid busy-waiting
                pass

            return payload
        elif worker_type == 'consumer':
            if payload is None:
                time.sleep(0.001)  # Adding a small sleep to avoid busy-waiting
                return channel_idx

            [channel_idx, frame, fps] = payload
            video_worker.get_video_consumer().process(channel_idx, frame, fps)
            return channel_idx
        else:
            raise RuntimeError('invalid type in worker_impl()')

    def start(self):
        self.__running_video_worker = True
        # start producer
        timer = threading.Timer(0.001, self.start_producer_worker)  # Thread separation and recursive repetition
        timer.start()

        # start consumer
        timer = threading.Timer(0.001, self.start_consumer_worker)  # Thread separation and recursive repetition
        timer.start()

        self.resume_button.hide()

    def start_producer_worker(self, worker_type='producer'):
        if self.__running_video_worker:
            if self.__pause_video_worker:
                timer = threading.Timer(0.1, self.start_producer_worker)  # Thread separation and recursive repetition
                timer.start()
                return

            video_channels = list(range(self.ui_config.num_channels))

            for channel_idx in video_channels:
                future = self.__producer_thread_pool_executor.submit(self.worker_impl, channel_idx, worker_type, None)
                self.__producer_futures.append(future)

            for future in as_completed(self.__producer_futures):
                try:
                    payload = future.result()
                    if payload is None:
                        break

                    logging.debug(payload)
                    [channel_idx, _, _] = payload
                    self.__video_worker_list[channel_idx].push_queue(payload)
                except Exception as e:
                    logging.error(f"Error processing video: {e}")

            self.__producer_futures.clear()

            timer = threading.Timer(0.001, self.start_producer_worker)
            timer.start()

    def start_consumer_worker(self, worker_type='consumer'):
        if self.__running_video_worker:
            if self.__pause_video_worker:
                timer = threading.Timer(0.1, self.start_consumer_worker)
                timer.start()
                return

            # if self.__consumer_queue.empty():
            for video_worker in self.__video_worker_list:
                payload = video_worker.pop_queue()
                if payload is not None:
                    [channel_idx, _, _] = payload
                    future = self.__consumer_thread_pool_executor.submit(self.worker_impl, channel_idx, worker_type, payload)
                    self.__consumer_futures.append(future)

            for future in as_completed(self.__consumer_futures):
                try:
                    channel_idx = future.result()
                    logging.debug("consumer worker task done, channel_idx: ", channel_idx)

                except Exception as e:
                    logging.error(f"Error processing video: {e}")

            # print("self.__consumer_futures clear() : ", len(self.__consumer_futures))
            self.__consumer_futures.clear()

            timer = threading.Timer(0.001, self.start_consumer_worker)    # Thread separation and recursive repetition
            timer.start()

    def resume(self):
        self.__pause_video_worker = False
        self.resume_button.hide()

        for video_worker in self.__video_worker_list:
            video_worker.get_video_producer().resume()
            video_worker.get_video_consumer().resume()

        self.pause_button.show()

    def pause(self):
        self.__pause_video_worker = True
        self.pause_button.hide()

        for video_worker in self.__video_worker_list:
            video_worker.get_video_producer().pause()
            video_worker.get_video_consumer().pause()

        self.resume_button.show()

    def __toggle_percent(self):
        self.ui_config.show_percent = self.show_percentage_button.isChecked()

    def __toggle_score(self):
        self.ui_config.show_score = self.show_score_button.isChecked()

    def __toggle_alarm_only_on_camera_ch(self):
        self.ui_config.alarm_only_on_camera_ch = self.alarm_only_on_camera_ch_button.isChecked()

    def __toggle_camera_switch(self):
        self.ui_config.camera_switch = self.camera_switch_button.isChecked()

        # camera switch changed
        if self.ui_config.camera_mode:
            for video_worker in self.__video_worker_list:
                video_producer = video_worker.get_video_producer()
                video_consumer = video_worker.get_video_consumer()
                if video_producer.is_camera_source():
                    if self.ui_config.camera_switch:
                        video_producer.resume()
                        video_consumer.resume()
                    else:
                        video_producer.pause()
                        video_consumer.pause()

    def update_scaled_video_frame(self, channel_idx: int, qt_img):
        self.video_label_list[channel_idx].setPixmap(QPixmap.fromImage(qt_img))

    def clear_sentence_output(self, idx: int):
        sentence_output_layout = self.sentence_output_layout_list[idx]
        while sentence_output_layout.count():
            item = sentence_output_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                self.clear_layout(item.layout())

    def __adjust_font_size_to_fit(self, label, max_width, min_font_size=None):
        font = label.font()
        font_metrics = QFontMetrics(font)

        while font_metrics.horizontalAdvance(label.text()) > max_width and font.pointSize() > 1:
            if min_font_size is not None and font.pointSize() <= min_font_size:
                print("breaked!!!")
                break
            font.setPointSize(font.pointSize() - 1)
            label.setFont(font)
            font_metrics = QFontMetrics(font)

    def update_sentence_output(self, idx: int, text: str, progress: int, score: float,
                               alarm: bool, alarm_title: str, alarm_position: int, alarm_color: str,
                               media_alarm: bool, media_alarm_title: str, media_alarm_media_path: str,
                               media_alarm_position: int):
        prefix_str = ""
        if self.ui_config.show_percent:
            prefix_str += "[" + str(progress) + "%]"

        if self.ui_config.show_score:
            prefix_str += "[" + "{:.{}f}".format(score, self.ui_config.score_settings_decimals) + "]"

        # sentence_output box layout
        # [prefix]|[__text]
        sentence_output_box = QHBoxLayout()
        sentence_output_box.setSpacing(0)
        sentence_output_box.setContentsMargins(0, 0, 0, 0)

        is_camera_source = self.__video_worker_list[idx].get_video_producer().is_camera_source()
        is_single_channel = self.ui_config.num_channels == 1
        is_merged_center_grid = (self.adjusted_video_grid_info is not None) and (self.ui_config.num_channels == idx + 1)

        if is_camera_source or is_single_channel or is_merged_center_grid:
            font = self.ui_helper.large_font
            prefix_text_fixed_width = self.ui_helper.large_font_prefix_text_fixed_width
        else:
            font = self.ui_helper.small_font
            prefix_text_fixed_width = self.ui_helper.small_font_prefix_text_fixed_width

        if prefix_str != "":
            # prefix
            prefix_label = QLabel(prefix_str, self)
            prefix_label.setFont(font)
            prefix_label.setFixedWidth(prefix_text_fixed_width)
            # prefix_label.setStyleSheet("border: 1px solid red; padding: 0px;")
            prefix_label.setContentsMargins(0, 0, 0, 0)
            prefix_label.setAlignment(Qt.AlignTop)
            sentence_output_box.addWidget(prefix_label)

        # sentence_output
        sentence_output_label = QLabel(text, self)
        sentence_output_label.setFont(font)
        sentence_output_label.setMinimumWidth(self.ui_helper.video_size[0])  # 너비 설정

        # sentence_output_label.setStyleSheet("border: 1px solid green; padding: 0px;")
        sentence_output_label.setContentsMargins(0, 0, 0, 0)
        sentence_output_label.setAlignment(Qt.AlignTop)
        sentence_output_box.addWidget(sentence_output_label)

        self.sentence_output_layout_list[idx].addLayout(sentence_output_box)

        # adjust font size
        if "fit" in self.ui_config.dynamic_font_mode:  # 너비 기준으로 자동 사이즈 조정
            parent_widget = sentence_output_box.parentWidget()
            if parent_widget:
                if "min" in self.ui_config.dynamic_font_mode:
                    self.__adjust_font_size_to_fit(sentence_output_label, parent_widget.width(), self.ui_config.min_font_size)
                else:
                    self.__adjust_font_size_to_fit(sentence_output_label, parent_widget.width())
        
        if "word_wrap" in self.ui_config.dynamic_font_mode: # 줄바꿈 허용
            sentence_output_label.setWordWrap(True)
        

        # TODO: send data to server refer to below
        # self.send_event_to_server(alarm_title, text, idx, score)

        if self.ui_config.alarm_only_on_camera_ch and is_camera_source is False:
            # skip to show alarm when video channel is not camera source
            return

        if alarm and not self.is_opened_dialog and Toast.getQueuedCount() <= 9:
            self.show_toast(prefix_str + text, title=alarm_title, duration=2000, preset=ToastPreset.WARNING,
                            position=ToastPosition(alarm_position), color=alarm_color,
                            font_size=self.ui_config.sentence_alarm_font_size)

        if media_alarm and not self.is_opened_dialog and not self.is_opened_media_alert:
            self.show_media_toast(media_alarm_title, media_alarm_media_path, ToastPosition(media_alarm_position))

    def send_event_to_server(self, message_type, message, channel, score):
        import requests
        import xml.etree.ElementTree as ET
        from datetime import datetime

        root = ET.Element("EventMessages")

        utc_now = datetime.utcnow().replace(tzinfo=None)
        utc_now_str = utc_now.isoformat()

        ET.SubElement(root, "UTCtime").text = utc_now_str
        ET.SubElement(root, "AlarmTitle").text = message_type
        ET.SubElement(root, "AlarmText").text = message
        ET.SubElement(root, "ChannelID").text = str(channel)
        ET.SubElement(root, "Score").text = str(score)

        tree = ET.ElementTree(root)

        xml_data = ET.tostring(root, encoding='utf-8', method='xml')
        headers = {
            'Content-Type': 'text/xml; charset=utf-8'
        }
        url = 'http://example.com/api'  # 서버 URL

        # TODO: send example
        print("=== SEND EVENT TO SERVER EXAM === \n" + xml_data.decode('utf-8'))
        response = requests.post(url, data=xml_data, headers=headers)
        print("서버 응답 코드:", response.status_code)
        print("서버 응답 내용:", response.text)

    def show_toast(self, text, title="Info", duration=3000, preset=ToastPreset.WARNING,
                   position=ToastPosition.BOTTOM_MIDDLE, color="#E8B849", font_size=9, media_path=None):
        Toast.setMaximumOnScreen(3)
        toast = Toast(self)
        toast.setDuration(duration)
        toast.setTitle(title)
        toast.setText(text + "          ")
        toast.applyPreset(preset)
        Toast.setPosition(position)

        # should be called after applyPreset()
        toast.setTitleFont(QFont('Arial', font_size, QFont.Weight.Bold))
        toast.setTextFont(QFont('Arial', font_size))
        toast.setIconColor(QColor(color))
        toast.setDurationBarColor(QColor(color))

        toast.show()

    def show_media_toast(self, title, media_path, position=ToastPosition.CENTER):
        self.is_opened_media_alert = True
        video_toast = VideoToast(title, media_path, position, self)
        video_toast.show()


    @staticmethod
    def __round_down_float(val: float, exp="0.000", rounding=ROUND_HALF_UP):
        return float(Decimal(val).quantize(Decimal(exp), rounding=rounding))

    def open_add_sentence_dialog(self):
        self.is_opened_dialog = True
        dialog = AddSentenceDialog(self)
        result = dialog.exec()
        if result == QDialog.Accepted:
            sentence = dialog.get_sentence_input_text()
            score_min = self.__round_down_float(dialog.get_score_min_input_value())
            score_max = self.__round_down_float(dialog.get_score_max_input_value())
            score_threshold = self.__round_down_float(dialog.get_score_threshold_input_value())
            alarm = dialog.get_alarm_checked()
            alarm_title = dialog.get_alarm_title_input_text()
            alarm_position = dialog.get_alarm_position()
            alarm_color = dialog.get_alarm_color()
            media_alarm = dialog.get_media_alarm_checked()
            media_alarm_title = dialog.get_media_alarm_title_input_text()
            media_alarm_media_path = dialog.get_media_alarm_media_path_label_text()
            media_alarm_position = dialog.get_media_alarm_position()

            self.add_sentence(sentence, score_min, score_max, score_threshold,
                              alarm, alarm_title, alarm_position, alarm_color,
                              media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position)
            self.is_opened_dialog = False
        elif result == QDialog.Rejected:
            self.is_opened_dialog = False

    def open_modify_sentence_dialog(self, index):
        # 현재 문장 정보를 가져와 ModifySentenceDialog 열기
        sentence: Sentence = self.__view_model.get_sentence_list()[index]
        score_min = sentence.get_score_min()
        score_max = sentence.get_score_max()
        score_threshold = sentence.get_score_threshold()
        alarm = sentence.get_alarm()
        alarm_title = sentence.get_alarm_title()
        alarm_position = sentence.get_alarm_position()
        alarm_color = sentence.get_alarm_color()
        media_alarm = sentence.get_media_alarm()
        media_alarm_title = sentence.get_media_alarm_title()
        media_alarm_media_path = sentence.get_media_alarm_media_path()
        media_alarm_position = sentence.get_media_alarm_position()

        dialog = ModifySentenceDialog(sentence, score_min, score_max, score_threshold,
                                      alarm, alarm_title, alarm_position, alarm_color,
                                      media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position,
                                      self)
        result = dialog.exec()
        self.is_opened_dialog = True
        if result == QDialog.Accepted:
            updated_sentence = dialog.get_sentence_input_text()
            updated_min = self.__round_down_float(dialog.get_score_min_input_value())
            updated_max = self.__round_down_float(dialog.get_score_max_input_value())
            updated_threshold = self.__round_down_float(dialog.get_score_threshold_input_value())
            updated_alarm = dialog.get_alarm_checked()
            updated_alarm_title = dialog.get_alarm_title_input_text()
            updated_alarm_position = dialog.get_alarm_position()
            updated_alarm_color = dialog.get_alarm_color()
            updated_media_alarm = dialog.get_media_alarm_checked()
            updated_media_alarm_title = dialog.get_media_alarm_title_input_text()
            updated_media_alarm_media_path = dialog.get_media_alarm_media_path_label_text()
            updated_media_alarm_position = dialog.get_media_alarm_position()
            self.modify_sentence(updated_sentence, updated_min, updated_max, updated_threshold,
                                 updated_alarm, updated_alarm_title, updated_alarm_position, updated_alarm_color,
                                 updated_media_alarm, updated_media_alarm_title, updated_media_alarm_media_path,
                                 updated_media_alarm_position, index)
            self.is_opened_dialog = False
        elif result == QDialog.Rejected:
            self.is_opened_dialog = False

    def refresh_sentence_list(self):
        while self.sentence_list_layout.count():
            item = self.sentence_list_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                self.clear_layout(item.layout())

        sentence_list = self.__view_model.get_sentence_list()

        for idx, sentence in enumerate(sentence_list):
            # sentence box layout
            # [del]|[sentence]
            sentence_box = QHBoxLayout()

            mod_button = QPushButton("M", self)
            mod_button.setFixedWidth(20)
            mod_button.clicked.connect(lambda _, i=idx: self.open_modify_sentence_dialog(i))
            sentence_box.addWidget(mod_button)

            del_button = QPushButton("D", self)
            del_button.setFixedWidth(20)
            del_button.clicked.connect(lambda _, i=idx: self.delete_sentence(i))
            sentence_box.addWidget(del_button)

            sentence_toggle_checkbox = QCheckBox("", self)
            sentence_toggle_checkbox.setChecked(not sentence.get_disabled())
            sentence_toggle_checkbox.clicked.connect(lambda _, i=idx: self.toggle_sentence(i))
            sentence_toggle_checkbox.setFixedWidth(40)
            sentence_box.addWidget(sentence_toggle_checkbox)

            sentence_label = QLabel(sentence.get_text(), self)
            sentence_box.addWidget(sentence_label)

            sentence_alarm_checkbox = QCheckBox("Toast", self)
            sentence_alarm_checkbox.setChecked(sentence.get_alarm())
            sentence_alarm_checkbox.clicked.connect(lambda _, i=idx: self.toggle_alarm(i))
            sentence_alarm_checkbox.setFixedWidth(40)
            sentence_alarm_checkbox.setStyleSheet("font-size: 9px;")
            sentence_box.addWidget(sentence_alarm_checkbox)

            sentence_media_alarm_checkbox = QCheckBox("Media", self)
            sentence_media_alarm_checkbox.setChecked(sentence.get_media_alarm())
            sentence_media_alarm_checkbox.clicked.connect(lambda _, i=idx: self.toggle_media_alarm(i))
            sentence_media_alarm_checkbox.setFixedWidth(60)
            
            sentence_media_alarm_checkbox.setStyleSheet("font-size: 9px;")
            sentence_box.addWidget(sentence_media_alarm_checkbox)

            self.sentence_list_layout.addLayout(sentence_box)

        self.hide_loading()

    def clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
            elif item.layout() is not None:
                self.clear_layout(item.layout())

    def add_sentence(self, sentence, score_min, score_max, score_threshold,
                     alarm, alarm_title, alarm_position, alarm_color,
                     media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position):
        if len(sentence) == 0:
            self.show_toast("Please enter a sentence and press the Add button.")
            return

        self.show_loading()
        self.__view_model.insert_sentence(sentence, score_min, score_max, score_threshold,
                                          alarm, alarm_title, alarm_position, alarm_color,
                                          media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position)

    def delete_sentence(self, index):
        self.show_loading()
        self.__view_model.pop_sentence(index)

    def toggle_sentence(self, index):
        self.show_loading()
        self.__view_model.toggle_sentence(index)

    def toggle_alarm(self, index):
        self.show_loading()
        self.__view_model.toggle_alarm(index)

    def toggle_media_alarm(self, index):
        self.show_loading()
        self.__view_model.toggle_media_alarm(index)

    def modify_sentence(self, sentence, score_min, score_max, score_threshold,
                        alarm, alarm_title, alarm_position, alarm_color,
                        media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position, index):
        self.show_loading()
        self.__view_model.update_sentence(sentence, score_min, score_max, score_threshold,
                                          alarm, alarm_title, alarm_position, alarm_color,
                                          media_alarm, media_alarm_title, media_alarm_media_path, media_alarm_position,
                                          index)

    def reset_text_list(self):
        self.show_loading()
        self.__view_model.reset_sentence()

    def clear_text_list(self):
        self.show_loading()
        self.__view_model.clear_sentence()

    def update_overall_fps(self):
        with self.__fps_lock:
            if len(self.each_fps_info_list) > 0:
                sum_overall_dxnn_fps = 0
                sum_overall_sol_fps = 0
                for each_fps in self.each_fps_info_list:
                    sum_overall_dxnn_fps += each_fps["dxnn_fps"]
                    sum_overall_sol_fps += each_fps["sol_fps"]

                overall_dxnn_fps = sum_overall_dxnn_fps / len(self.each_fps_info_list)
                overall_sol_fps = sum_overall_sol_fps / len(self.each_fps_info_list)

                self.overall_fps_label.setText(
                    f" NPU FPS: {overall_dxnn_fps:.2f}, APP FPS: {overall_sol_fps:.2f} ")

    def update_each_fps(self, channel_idx, dxnn_fps, sol_fps):
        with self.__fps_lock:
            if self.ui_config.show_each_fps_label:
                self.each_fps_label_list[channel_idx].setText(f" NPU FPS: {dxnn_fps:.2f}, APP FPS: {sol_fps:.2f} ")

            self.each_fps_info_list[channel_idx]["dxnn_fps"] = dxnn_fps
            self.each_fps_info_list[channel_idx]["sol_fps"] = sol_fps

    @overrides
    def closeEvent(self, event):
        self.__running_video_worker = False

        for video_worker in self.__video_worker_list:
            video_worker.get_video_producer().stop()
            video_worker.get_video_consumer().stop()

        # self.__thread_pool_executor.shutdown(wait=True)
        self.__producer_thread_pool_executor.shutdown(wait=True)
        self.__consumer_thread_pool_executor.shutdown(wait=True)

        for future in self.__producer_futures:
            if not future.done():
                future.cancel()

        for future in self.__consumer_futures:
            if not future.done():
                future.cancel()

        super().closeEvent(event)

    def close_application(self):
        self.close()
