from __future__ import annotations
import math

from PyQt5.QtWidgets import QMainWindow, QVBoxLayout, QLabel, QLineEdit, QSpinBox, QCheckBox, QPushButton, QWidget, \
    QGridLayout, QComboBox, QGroupBox, QHBoxLayout
from clip_demo_app_pyqt.common.config.ui_config import UIConfig


class MergedVideoGridInfo:
    def __init__(self, center_end, center_size, center_start, grid_size, outer_channel_max):
        self.center_end = center_end
        self.center_size = center_size
        self.center_start = center_start
        self.grid_size = grid_size
        self.outer_channel_max = outer_channel_max


class SettingsView(QMainWindow):
    def __init__(self, args, success_cb):
        super().__init__()
        self.model = None
        self.view_model = None
        self.main_app = None

        # CLI arguments
        self.base_path = args.base_path
        self.max_words = args.max_words
        self.feature_framerate = args.feature_framerate
        self.slice_framepos = args.slice_framepos

        # app config setting
        self.number_of_channels = args.number_of_channels
        self.settings_mode = args.settings_mode
        self.camera_mode = args.camera_mode
        self.merge_central_grid = args.merge_central_grid
        self.video_fps_sync_mode = args.video_fps_sync_mode
        self.inference_engine_async_mode = args.inference_engine_async_mode

        # input data setting
        from clip_demo_app_pyqt.data.input_data import InputData
        from clip_demo_app_pyqt.model.sentence_model import Sentence

        self.input_data = InputData()
        self.video_path_lists = self.input_data.get_video_path_lists()
        self.sentence_list: list[Sentence] = self.input_data.get_sentence_list()

        self.success_cb = success_cb

        self.adjusted_video_path_lists: list = []
        self.merged_video_grid_info = None

        # UI config
        self.ui_config = UIConfig()

        self.setWindowTitle("Settings")
        self.setMinimumWidth(1000)

        # layout setup
        layout = QVBoxLayout()

        # features_path input
        self.features_path_label = QLabel("Features Path:")
        self.features_path_input = QLineEdit(self)
        self.features_path_input.setText(self.base_path)
        layout.addWidget(self.features_path_label)
        layout.addWidget(self.features_path_input)

        # number_of_channels input
        self.number_of_channels_label = QLabel("Number of Channels:")
        self.number_of_channels_input = QSpinBox(self)
        self.number_of_channels_input.setValue(self.number_of_channels)
        self.number_of_channels_input.setRange(1, 16)  # 1 ~ 16 채널로 제한
        layout.addWidget(self.number_of_channels_label)
        layout.addWidget(self.number_of_channels_input)

        # Show Percentage checkbox
        self.show_percent_checkbox = QCheckBox("Display Percentage", self)
        self.show_percent_checkbox.setChecked(self.ui_config.show_percent)
        layout.addWidget(self.show_percent_checkbox)

        # Show Score checkbox
        self.show_score_checkbox = QCheckBox("Display Score", self)
        self.show_score_checkbox.setChecked(self.ui_config.show_score)
        layout.addWidget(self.show_score_checkbox)

        # Settings Mode checkbox
        self.settings_mode_checkbox = QCheckBox("Settings(prompt) Mode", self)
        self.settings_mode_checkbox.setChecked(self.settings_mode)
        layout.addWidget(self.settings_mode_checkbox)

        # Camera Mode checkbox
        self.camera_mode_checkbox = QCheckBox("Camera Mode", self)
        self.camera_mode_checkbox.setChecked(self.camera_mode)
        self.camera_mode_checkbox.clicked.connect(self.__onclick_camera_mode_checkbox)
        layout.addWidget(self.camera_mode_checkbox)

        # Merge the Central Grid checkbox
        self.merge_central_grid_checkbox = QCheckBox("Merge the central grid", self)
        self.merge_central_grid_checkbox.setChecked(self.merge_central_grid)
        layout.addWidget(self.merge_central_grid_checkbox)

        # Video FPS Sync Mode checkbox
        self.video_fps_sync_mode_checkbox = QCheckBox("Video FPS Sync Mode", self)
        self.video_fps_sync_mode_checkbox.setChecked(self.video_fps_sync_mode)
        layout.addWidget(self.video_fps_sync_mode_checkbox)

        # Inference Engine RunAsync Mode checkbox
        self.inference_engine_async_mode_checkbox = QCheckBox("Inference RunAsync Mode", self)
        self.inference_engine_async_mode_checkbox.setChecked(self.inference_engine_async_mode)
        layout.addWidget(self.inference_engine_async_mode_checkbox)

        # Fullscreen Mode checkbox
        self.fullscreen_mode_checkbox = QCheckBox("Fullscreen Mode", self)
        self.fullscreen_mode_checkbox.setChecked(self.ui_config.fullscreen_mode)
        layout.addWidget(self.fullscreen_mode_checkbox)

        # Dark Theme checkbox
        self.dark_theme_checkbox = QCheckBox("Dark Theme", self)
        self.dark_theme_checkbox.setChecked(self.ui_config.dark_theme)
        layout.addWidget(self.dark_theme_checkbox)

        # Show FPS Label checkbox
        self.show_each_fps_label_checkbox = QCheckBox("Display FPS for each video", self)
        self.show_each_fps_label_checkbox.setChecked(self.ui_config.show_each_fps_label)
        layout.addWidget(self.show_each_fps_label_checkbox)

        # font setting grop - START
        font_setting_box = QGroupBox("Font Setting")
        font_setting_layout = QVBoxLayout()

        font_setting_sub1_layout = QHBoxLayout()
        font_setting_sub2_layout = QHBoxLayout()

        # Dropdown for fit/word_wrap options
        self.dynamic_font_mode_dropdown = QComboBox(self)
        self.dynamic_font_mode_dropdown.addItem("fit")
        self.dynamic_font_mode_dropdown.addItem("word_wrap")
        self.dynamic_font_mode_dropdown.addItem("fit + min")
        self.dynamic_font_mode_dropdown.addItem("fit + min + word_wrap")
        self.dynamic_font_mode_dropdown.setCurrentText("fit")  # 기본값 'fit'
        self.dynamic_font_mode_dropdown.currentTextChanged.connect(self.__on_layout_mode_change)
        font_setting_sub1_layout.addWidget(QLabel("Text Layout Mode:"))
        font_setting_sub1_layout.addWidget(self.dynamic_font_mode_dropdown)

        # Minimum Font Size input (enabled only for 'fit' option)
        self.min_font_size_label = QLabel("Minimum Font Size:")
        self.min_font_size_input = QSpinBox(self)
        self.min_font_size_input.setValue(self.ui_config.min_font_size)
        self.min_font_size_input.setRange(5, 10)
        self.min_font_size_input.setEnabled(False)
        font_setting_sub2_layout.addWidget(self.min_font_size_label)
        font_setting_sub2_layout.addWidget(self.min_font_size_input)

        font_setting_layout.addLayout(font_setting_sub1_layout)
        font_setting_layout.addLayout(font_setting_sub2_layout)

        font_setting_box.setLayout(font_setting_layout)
        layout.addWidget(font_setting_box)
        # font setting grop - END

        # Done button
        self.done_button = QPushButton("Done", self)
        self.done_button.clicked.connect(self.apply_settings)
        layout.addWidget(self.done_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def apply_settings(self):
        # Apply the values entered by the user
        self.base_path = self.features_path_input.text()

        # app config (using args)
        self.ui_config.num_channels = self.number_of_channels_input.value()
        self.ui_config.settings_mode = self.settings_mode_checkbox.isChecked()
        self.ui_config.camera_mode = self.camera_mode_checkbox.isChecked()
        self.ui_config.producer_video_fps_sync_mode = self.video_fps_sync_mode_checkbox.isChecked()

        # add config (hard-coded)
        self.ui_config.show_percent = self.show_percent_checkbox.isChecked()
        self.ui_config.show_score = self.show_score_checkbox.isChecked()
        self.ui_config.show_each_fps_label = self.show_each_fps_label_checkbox.isChecked()
        self.ui_config.fullscreen_mode = self.fullscreen_mode_checkbox.isChecked()
        self.ui_config.dark_theme = self.dark_theme_checkbox.isChecked()
        self.ui_config.merge_central_grid = self.merge_central_grid_checkbox.isChecked()
        self.ui_config.inference_engine_async_mode = self.inference_engine_async_mode_checkbox.isChecked()
        self.ui_config.dynamic_font_mode = self.dynamic_font_mode_dropdown.currentText()
        self.ui_config.min_font_size = self.min_font_size_input.value()

        # adjust video_grid_info, video_path_lists and num_channels
        if self.ui_config.merge_central_grid:
            self.merged_video_grid_info = self.__adjust_video_grid_info(self.ui_config, self.ui_config.num_channels,
                                                                        self.ui_config.camera_mode)

        [self.adjusted_video_path_lists, self.ui_config.num_channels] = self.__adjust_video_path_lists(
            self.video_path_lists, self.ui_config.num_channels, self.ui_config.camera_mode,
            self.merged_video_grid_info)

        # Close the settings window and start the main app
        self.close()
        self.start_main_app()

    def start_main_app(self):
        self.success_cb(self)

    def __on_layout_mode_change(self, text):
        if "min" in text:
            self.min_font_size_input.setEnabled(True)
        else:
            self.min_font_size_input.setEnabled(False)
            

    @staticmethod
    def __adjust_video_path_lists(video_path_lists, number_of_channels, camera_mode, merged_video_grid_info):
        result_num_of_channels = number_of_channels

        if number_of_channels <= 1:     # single channel
            result_video_path_lists = SettingsView.__video_path_lists_for_single_ch(video_path_lists)

            if camera_mode:
                result_video_path_lists[0] = ["/dev/video0"]
        else:      # multi channel
            merge_central_grid = merged_video_grid_info is not None
            if camera_mode:
                number_of_video_grid = number_of_channels - 1
            else:
                # If merging the center grid, repeat playback of all 16 videos in the center grid
                if merge_central_grid:
                    number_of_video_grid = number_of_channels - 1
                else:
                    number_of_video_grid = number_of_channels

            if merged_video_grid_info is not None:
                result_num_of_channels = merged_video_grid_info.outer_channel_max + 1

            result_video_path_lists = video_path_lists[:number_of_video_grid]

            if len(video_path_lists) > number_of_video_grid:
                residue_video_path_lists = video_path_lists[number_of_video_grid:]
                idx = 0
                for item in residue_video_path_lists:
                    calc_idx = idx % number_of_video_grid
                    result_video_path_lists[calc_idx] = result_video_path_lists[calc_idx] + item
                    idx += 1

            if camera_mode:
                result_video_path_lists.append(["/dev/video0"])
            else:
                # If merging the center grid, repeat playback of all 16 videos in the center grid
                if merge_central_grid:
                    result_video_path_lists.append(SettingsView.__video_path_lists_for_single_ch(video_path_lists)[0])

        return [result_video_path_lists, result_num_of_channels]

    @staticmethod
    def __video_path_lists_for_single_ch(video_path_lists):
        video_path_lists_for_single = []
        enriched_path_list = []
        for path_list in video_path_lists:
            for path in path_list:
                if not str(path).startswith("rtsp"):
                    enriched_path_list.append(path)
        video_path_lists_for_single.append(enriched_path_list)
        return video_path_lists_for_single

    @staticmethod
    def __adjust_video_grid_info(ui_config: UIConfig, num_channels: int,
                                 camera_mode: int) -> None or MergedVideoGridInfo:
        num_grid_channels = num_channels - 1 if camera_mode else num_channels
        if num_grid_channels <= 1:
            return None

        # Dynamically set the grid size
        grid_size = int(math.ceil(math.sqrt(num_grid_channels)))

        # Adjust to even numbers for grids of size 3x3 or larger
        if grid_size > 3 and grid_size % 2 != 0:
            grid_size += 1  # 짝수로 맞추기

        # Calculate central start position and size (e.g., 1x1 for 3x3, 2x2 central area for 4x4 and larger)
        center_start = grid_size // 2 - grid_size // 4
        center_size = grid_size // 2 if grid_size > 3 else 1
        center_end = center_start + center_size
        outer_channel_max = num_channels - center_size ** 2
        ui_config.num_channels = outer_channel_max + 1
        return MergedVideoGridInfo(center_end, center_size, center_start, grid_size, outer_channel_max)

    def __onclick_camera_mode_checkbox(self):
        # for usability
        if self.camera_mode_checkbox.isChecked():
            self.merge_central_grid_checkbox.setChecked(True)
