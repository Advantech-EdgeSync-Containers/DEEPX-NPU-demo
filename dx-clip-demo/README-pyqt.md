# Environment Setup

## CLIP DEMO using PyQT5 UI Framework

---
### Pre-Requisite
#### Get assets (input videos and prebuilt CLIP AI model) files
Download the asset files using setup.sh. These files are provided separately and are not included in the distributed source code.

When running setup.sh, you must specify app_type and dxrt_src_path as arguments.
Running setup.sh will automatically download the asset files and set up a Python virtual environment (venv).
`./setup.sh --app_type=<app_type> --dxrt_src_path=<path_to_dxrt>`
```bash
# exam
./setup.sh --app_type=pyqt --dxrt_src_path=/deepx/dx_rt
```

File structure in `./assets/`:
```
assets
├── CLIP
│   ├── build
│   ├── clip
│   ├── clip.egg-info
│   ├── CLIP.png
│   ├── data
│   ├── hubconf.py
│   ├── LICENSE
│   ├── MANIFEST.in
│   ├── model-card.md
│   ├── notebooks
│   ├── README.md
│   ├── requirements.txt
│   ├── setup.py
│   └── tests
├── data
│   ├── MSRVTT_JSFUSION_test.csv
│   └── MSRVTT_Videos
├── demo_videos
│   ├── burning_car.mov
│   ├── crowded_subway_platform.mov
│   ├── elderly_woman_fallen_indoor.mov
│   ├── kitchen_stove_fire.mov
│   └── men_fighting_indoors.mov
├── dxnn
│   ├── clip_vit_250331.dxnn
└── onnx
    ├── embedding_f32_op14_clip4clip_msrvtt_b128_ep5.onnx
    ├── textual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx
    └── visual_f32_op14_clip4clip_msrvtt_b128_ep5.onnx
```

---
### Setup Demo
#### 1. Run setup script 
Depending on the application runtime environment, an automated setup script can be used as shown below. For more details, please refer to the script's specifics.

Using setup.sh, the script automatically detects the amd64 and aarch64 environments, downloads the assets files, and sets up the application runtime environment.

However, for Windows, you need to run either setup_clip_demo_app_pyqt.bat or setup_clip_demo_app_opencv.bat.

##### for Linux amd64
```
./scripts/setup_clip_demo_app.sh --app_type=pyqt --arch_type=amd64 --dxrt_src_path=<path_to_dxrt>
```

##### for Linux aarch64 (OrangePi 5+ Ubuntu 22.04 OS)
- for Linux aarch64 
```
./scripts/setup_clip_demo_app.sh --app_type=pyqt --arch_type=aarch64 --dxrt_src_path=<path_to_dxrt>
```

##### for Windows
```
.\scripts\x86_64_win\setup_clip_demo_app_pyqt.bat
```

### Execute Demo
#### 1. Activate python virtual environments
##### for Linux
```bash
source venv-pyqt/bin/activate
```
##### for Windows
```
venv-pyqt\bin\activate.bat
```

##### 2. Run command
```bash
python -m clip_demo_app_pyqt.dx_realtime_demo_pyqt
```

##### 3. Setting options
1. **Assets Path**:
    - You can change the assets directory path.
2. **Number of Channels (Single/Multi-channel Mode)**:
    - You can switch from a single channel to up to 16 channels by adjusting the `Number of Channels` setting.
3. **Display Percentage**:
    - Set whether to display the percentage of the similarity value for the matching sentence.
4. **Display Score**:
    - Set whether to display the score of the similarity value for the matching sentence.
5. **Settings Mode**:
    - Enable or disable the input Settings UI, where you can add, delete, or clear all sentences.
6. **Camera Mode**:
    - **Single-channel Mode**: Enable the camera mode to replace the video with the one from the device-connected camera.
    - **Multi-channel Mode**: Enable the camera mode to add the video from the device-connected camera to the channels.
7. **Merge the central grid**:
    - In video grid screens such as 3x3 and 4x4, merge multiple grids in the center into one larger display.
    - Previous videos playing in the merged grid are redistributed to the channels in other grids.
    - **Camera Mode: ON**: The camera video plays in the merged central grid.
    - **Camera Mode: OFF**: All sample videos (16 total) are played in a loop in the merged central grid.
8. **Video FPS Sync Mode**:
    - **ON**: Check the original fps information of the video and force the input to be processed at the original fps speed of the video.
    - **OFF**: Process video input at the maximum speed available on the hardware. (However, if Camera Mode is ON, input is processed at the original video fps speed.)
9. **Fullscreen Mode**:
    - Set the app to fullscreen mode or windowed mode.
10. **Dark Theme**:
    - Set whether to apply the dark theme.
11. **Display FPS for each video**:
    - In Multi-channel mode, you can set whether to display the current FPS for each channel.
12. Font Settings
  - **Text Layout Mode**  
    - **fit**: Adjusts the font size to fit within the text box area. (Ensures all text is visible, even if there are multiple lines, but the font may become very small.)  
    - **word_wrap**: Keeps the font size unchanged and wraps text onto new lines. (If there are multiple lines, some text may require scrolling to view.)  
    - **fit + min**: Same as **fit**, but the font size will not go below the specified **Minimum Font Size**. (If the text is too long, it may be truncated.)  
    - **fit + min + word_wrap**: Same as **fit + min**, but prevents text from being cut off by enabling line wrapping. (If there are multiple lines, some text may require scrolling to view.)  

  - **Minimum Font Size**: Limits how much the font size can be reduced when `Text Layout Mode` includes `min`.  
