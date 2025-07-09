
----------

# Installation Guide

This guide provides instructions for setting up and running the DeepX CLIP demo application.

----------

## Prerequisites

Before proceeding with the installation, ensure you have completed the following steps:

1.  **Download & Build `dx_rt`**: Obtain and build the DeepX Runtime.
    
2.  **Download & Build `dx_rt_npu_driver`**: Obtain and build the DeepX NPU Driver.
    

----------

### SDK Download

For the **SDK**, please contact the DeepX sales team at **salesteam@deepx.ai**.

----------

## Hardware and Software Requirements

Ensure your system meets the following specifications:

-   **CPU:** aarch64, x86_64, riscv64
    
-   **RAM:** 8GB RAM (16GB RAM or higher is recommended)
    
-   **Storage:** 4GB or higher available disk space
    
-   **OS:** Ubuntu 20.04 / 22.04 / 24.04 (x64 / aarch64)
    
-   **Hardware:** The system **must** support connection to an **M1 M.2** module with the **M.2 interface** on the host PC.
    

----------

## Installation Steps

### 1. Download Demo & Video/Model Assets

First, download the demo application and its associated assets.

```
wget http://cs.deepx.ai/_deepx_fae_archive/demo_application/clip_demo_rt_v263.tar.gz
```

This will create a directory structure similar to this:

```
└── clip_demo_rt_v263
    ├── assets
    │   ├── CLIP
    │   ├── data
    │   ├── demo_videos
    │   ├── dxnn
    │   └── onnx
    ├── clip_demo_app_opencv
    ├── clip_demo_app_pyqt
    │   ├── common
    │   ├── data
    │   ├── docs
    │   ├── lib
    │   ├── model
    │   ├── res
    │   ├── view
    │   └── viewmodel
    ├── install_dep
    │   ├── linux-amd64
    │   └── opi5plus
    └── scripts
        ├── aarch64
        ├── amd64
        └── x86_64_win
```

Next, download the `clip_assets.tar.gz` file:

```
wget http://cs.deepx.ai/_deepx_fae_archive/demo_application/clip_assets.tar.gz
```

**Decompress** `clip_assets.tar.gz` into the **`clip_demo_rt_v263/`** directory. After decompression, the `assets` directory should look like this:

```
assets
├── CLIP
│   ├── clip
│   ├── data
│   ├── notebooks
│   └── tests
├── data
│   └── MSRVTT_Videos
├── demo_videos
├── dxnn
└── onnx

```

----------

### 2. Install Demo Application

Navigate into the `clip_demo_rt_v263` directory and run the setup script. Replace `{architecture}` with your system's architecture (e.g., `amd64`, `aarch64`, `x86_64_win`).


```
cd clip_demo_rt_v263/ ./scripts/{architecture}/setup_clip_demo_app_pyqt.sh --dxrt_src_path=/path/to/your/dx_rt
```

----------

### 3. Execute Demo

To run the demo, first activate the virtual environment, then execute the demo script.

#### Activate Virtual Environment


```
source venv-pyqt/bin/activate
```

#### Execute Demo

Navigate to the application directory and run the demo script.


```
cd ~/clip_demo_rt_v263/clip_demo_app_pyqt
./run_demo.sh
```

You will then be prompted to select an AI demo to run:

```
1: Single Channel Demo
1-2: Single Channel Demo (Settings Mode)
1-3: Single Channel Demo (Camera Mode & Settings Mode)
2: Multi Channel Demo
2-2: Multi Channel Demo (Settings Mode)
2-3: Multi Channel Demo (Camera Mode & Settings Mode)
0: Default Demo
which AI demo do you want to run:(timeout:10s, default:0)
```


----------

## Troubleshooting Guide

This section addresses common issues you might encounter during the installation and execution of the DeepX CLIP demo.

----------

### Issue 1: `AttributeError: install_layout` during `dx-engine` installation

**Error Message:**

```
AttributeError: install_layout. Did you mean: 'install_platlib'?
      [end of output]

 note: This error originates from a subprocess, and is likely not a problem with pip.
 ERROR: Failed building wheel for dx-engine
Failed to build dx-engine
ERROR: Could not build wheels for dx-engine, which is required to install pyproject.toml-based projects
```

This error usually indicates an incompatibility between your `pip`, `setuptools`, or `wheel` versions and the project's build process.

**Solution:**

Upgrade your `pip`, `setuptools`, and `wheel` packages to their latest compatible versions.

Bash

```
python3.11 -m pip install --upgrade pip setuptools wheel
```

----------

### Issue 2: `ModuleNotFoundError: No module named 'clip'`

**Error Message:**

```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/deepx/clip_demo_rt_v263/clip_demo_app_pyqt/dx_realtime_demo_pyqt.py", line 65, in <module>
    main()
  File "/home/deepx/clip_demo_rt_v263/clip_demo_app_pyqt/dx_realtime_demo_pyqt.py", line 56, in main
    settings_window = SettingsView(args, success_cb)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/deepx/clip_demo_rt_v263/clip_demo_app_pyqt/view/settings_view.py", line 40, in __init__
    from clip_demo_app_pyqt.model.sentence_model import Sentence
  File "/home/deepx/clip_demo_rt_v263/clip_demo_app_pyqt/model/sentence_model.py", line 7, in <module>
    from clip_demo_app_pyqt.lib.clip.dx_text_encoder import TextVectorUtil
  File "/home/deepx/clip_demo_rt_v263/clip_demo_app_pyqt/lib/clip/dx_text_encoder.py", line 5, in <module>
    from clip.simple_tokenizer import SimpleTokenizer as ClipTokenizer
ModuleNotFoundError: No module named 'clip'

```

This error signifies that the `clip` Python module, a dependency for the demo application, is not installed or not accessible in your Python environment.

**Solution:**

Navigate to the `assets/CLIP` directory within your `clip_demo_rt_v263` folder and install the `clip` package from there.


```
cd ~/clip_demo_rt_v263/assets/CLIP
pip install .
```

After running this command, try executing the demo again.