# Other Config Settings
There are config values defined as follows that cannot be changed at runtime through the `Settings View` UI but can be modified in the `source code`.

```python
class UIConfig:
    ...
    # sentence(text) processing settings
    number_of_alarms = 2
    sentence_list_scroll_area_min_height = 150
    sentence_list_scroll_area_fixed_width = 450

    # video processing settings
    consumer_queue_size = 1
    consumer_num_of_inference_per_sec = 3
    consumer_max_np_array_similarity_queue = 5
    producer_video_fps_sync_mode = False
    consumer_video_fps_sync_mode = False
    producer_video_frame_skip_interval = 0  # 1st to 4th frames are processed, and the 5th frame is skipped when set to 5.
    max_producer_worker = 16
    max_consumer_worker = 4

    # Add Sentence Dialog
    sentence_input_min_width = 400
    score_settings_single_step = 0.005
    score_settings_decimals = 3

    # Clip View
    base_video_area_ratio = 0.65
    fullscreen_mode_negative_padding = 400
```

## Description of Other Configs

1. **number_of_alarms**
    - An alarm is displayed when the similarity score between the video (image) and the sentence (text) exceeds the threshold. `number_of_alarms` sets the maximum number of alarms to be displayed in this case (e.g., if set to 1, only the sentence with the highest similarity score above the threshold is shown).
   
2. The following config values are related to the `Sentence List` UI:
    - sentence_list_scroll_area_min_height 
        - The minimum vertical size of the scroll area in the Sentence List. 
    - sentence_list_scroll_area_fixed_width 
        - The fixed horizontal size of the scroll area in the Sentence List.

3. The following config values are related to the video processing settings: 
    - consumer_queue_size 
        - The maximum Queue size for the `VideoConsumer`.
    - consumer_num_of_inference_per_sec 
        - The number of frames processed per second (embedding generation frequency) by the `VideoConsumer`.
    - consumer_max_np_array_similarity_queue
        - The maximum size of the Queue used by the `VideoConsumer` for calculating the arithmetic mean of the similarity scores between video (image) and sentence (text). For example, if set to 5, the similarity scores for the current frame and the previous 4 frames are summed and averaged.     
    - producer_video_fps_sync_mode
        - Forces the frame processing speed of the `VideoProducer` to match the video FPS.
    - consumer_video_fps_sync_mode
        - Forces the frame processing speed of the `VideoConsumer` to match the video FPS.
    - producer_video_frame_skip_interval
        - Specifies the interval for skipping frame processing by the `VideoProducer`. For example, if set to 5, frames 1–4 are processed, and the 5th frame is skipped.
    - max_producer_worker
        - Specifies the maximum number of workers in the Thread Pool for the `VideoProducer`. 
    - max_consumer_worker
        - max_consumer_worker: Specifies the maximum number of workers in the Thread Pool for the `VideoConsumer`.
            - Note: The `ThreadPoolExecutor` for `VideoProducer` and `VideoConsumer` is used in the `__init__()` constructor of `ClipView`.
                - **clip_demo_app_pyqt/view/clip_view.py** 
                ```python
                class ClipView(Base, QMainWindow, metaclass=CombinedMeta):
                    def __init__(self, view_model: ClipViewModel, ui_config: UIConfig, base_path, adjusted_video_path_lists):
                        ...
                        self.__producer_thread_pool_executor = ThreadPoolExecutor(max_workers=self.ui_config.max_producer_worker)
                        self.__consumer_thread_pool_executor = ThreadPoolExecutor(max_workers=self.ui_config.max_consumer_worker)
                ```

4. The following config values are related to the `Sentence Dialog` UI:
    - sentence_input_min_width: The minimum width of the input field in the Sentence addition dialog.
    - score_settings_single_step: The minimum increment for the value change in the score setting spinner.
    - score_settings_decimals: The number of decimal places for the score setting.
   
5. The following config values are related to the `ClipView` UI:
    - base_video_area_ratio: The ratio of the `Video area` compared to the `Sentence List area`.
    - fullscreen_mode_negative_padding: The amount of padding subtracted from the height when running in `Fullscreen Mode` (to prevent screen clipping).
