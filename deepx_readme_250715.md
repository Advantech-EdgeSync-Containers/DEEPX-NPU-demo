
![deepx](./../mkdocs/img/deepx.png) 
**Deploying CLIP Applications with DEEPX DX-M1 on Edge Devices**

# DEEPX Overview

**DEEPX - Powering the Edge with Smarter AI Chips**  

**DEEPX** is a leading AI semiconductor company focused on developing ultra-efficient on-device AI solutions. With proprietary NPUs (Neural Processing Units), **DEEPX** enables high performance, reduced power consumption, and cost efficiency across applications in smart cameras, autonomous systems, factories, smart cities, consumer electronics, and AI servers. **DEEPX** is moving rapidly from sample evaluation to mass production to support global deployment.

---

# DX-M1 Accelerator Overview

**DX-M1** is **DEEPX** edge AI accelerator, built with proprietary NPU architecture to deliver powerful inference with low power draw.

## Key Features  

- **Exceptional Power Efficiency**: Up to 25 TOPS at only 3–5W  
- **Integrated DRAM**: High-speed internal memory for smooth multi-model execution  
- **XPU Compatibility**: Works with x86, ARM, and other mainstream CPUs  
- **Cost-Optimized Design**: Minimal SRAM footprint ensures affordability without sacrificing performance  

## Use Cases

- **Smart Camera**: Real-time edge AI analytics  
- **Edge & Storage Servers**: Compact AI compute modules  
- **Autonomous Robotics**: Embedded control and perception  
- **Industrial System**: Factory automation and monitoring  


---

# Deploying CLIP at the Edge

As multimodal AI models like CLIP (Contrastive Language–Image Pretraining) gain traction, edge deployment is becoming increasingly relevant. CLIP enables systems to understand the relationship between images and text, powering use cases like image captioning, visual search, and zero-shot classification.  

Here are real-world applications of CLIP on edge devices, optimized for NPU (Neural Processing Unit) acceleration. The focus is on how to architect these pipelines for efficient and scalable inference at the edge.  

## Image-to-Text Matching with CLIP

![CLIP-Based Visual-to-Text Matching](./../mkdocs/img/fig1.png){ width=700px }


This figure illustrates a CLIP-based approach for generating textual descriptions from visual input. An image—such as a bird near a feeder—is encoded by the NPU, which runs the image encoder component of the CLIP model.
Meanwhile, a predefined list of candidate captions (e.g., “A photo of a bird”, “A photo of a bird sitting near a bird feeder”) is pre-encoded using the text encoder and stored.
When a real-time image is received (via wired or wireless transfer), the system compares its image embedding against the pre-calculated text embeddings. Each comparison produces a similarity score (e.g., T₁, T₂, T₃) between 0 and 1, indicating how closely each caption matches the image.
The system then applies a user-defined threshold to filter and return the most relevant sentence that best describes the visual content.

## Text-to-Image Retrieval with CLIP

![CLIP-Based Text-to-Image Retrieval](./../mkdocs/img/fig2.png){ width=700px }

This figure illustrates a typical use case of CLIP for text-guided image retrieval. A user-provided query—such as “image with fruits without flowers”—is processed by the CPU, which runs the text encoder.
At the same time, a collection of candidate images is processed by the NPU, which executes the image encoder. Since CLIP is composed of two parallel encoders—one for text and one for images—this deployment distributes the workload across CPU and NPU accordingly: the CPU handles text, while the NPU accelerates image processing.
The system computes similar scores between the text embedding and each image embedding. The image with the highest score is selected and returned as the most relevant result.

---

# DEEPX CLIP Demo: How to Set Up and Run Multimodal AI at the Edge 

If you’re looking to deploy a real-time, CLIP-based visual-language application on embedded hardware, **DEEPX** has you covered. This guide walks you through setting up and running the **DEEPX VLM (Video-Language Model) CLIP Demo** on the **DEEPX M1** module — a compact, high-efficiency NPU accelerator.

## Prerequisite

Before getting started, ensure the following components are prepared.  
**1.** **Build `dx_rt`**: The **DEEPX** runtime library  
**2.** **Build `dx_rt_npu_driver`**: The **DEEPX** NPU Driver for hardware access  

**NOTE.** For access to **DEEPX SDK** components, contact the **DEEPX Sales Team** at **salesteam@deepx.ai**.  

## HW & SW System Requirement   

To run the CLIP demo effectively, your system should meet the following minimum specs.
-  **CPU:** aarch64, x86_64  
-  **RAM:** 8GB (16GB or higher recommended)  
-  **Storage:** 4GB or higher available disk space  
-  **OS:** Ubuntu 20.04 / 22.04 / 24.04 (x64 / aarch64)  
-  **Hardware:** The system **must** support connection to an **DEEPX M1** module with the **M.2 interface** on the host PC.  

## Installation Guide 

### Step 1. Download the Demo and Assets

**(1)**	Download the demo package
```
wget http://cs.deepx.ai/_deepx_fae_archive/demo_application/clip_demo_rt_v295.tar.gz
```

This will extract a directory with the following structure.  
```
└── clip_demo_rt_v295
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

**(2)** Extract the demo package
```
tar -xvzf clip_assets_copyright.tar.gz -C clip_demo_rt_v295/
```

After extraction, your directory structure should look like.
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

### Step 2. Install the Demo Application

**(1)**	Navigate into the demo directory and run the setup script.  
Replace `{architecture}` with your target platform (e.g., `amd64`, `x86_64_win`).
```
cd clip_demo_rt_v295/ ./scripts/{architecture}/setup_clip_demo_app_pyqt.sh --app_type=pyqt --arch_type={arch} --dxrt_src_path=/path/to/your/dx_rt
```

### Step 3. Run the Demo

**(1)**	Activate virtual environment  
```
source venv-pyqt/bin/activate
```

**(2)**	Launch the demo  
Navigate to the application directory and run the demo script.
```
cd clip_demo_rt_v295/ ./run_demo.sh --app_type=pyqt
```

**(3)**	Select an AI demo mode from the terminal prompt  
```
1: Single Channel Demo
1-2: Single Channel Demo (Settings Mode)
1-3: Single Channel Demo (Camera Mode & Settings Mode)
2: Multi Channel Demo
2-2: Multi Channel Demo (Settings Mode)
2-3: Multi Channel Demo (Camera Mode & Settings Mode)
0: Default Demo
which AI demo do you want to run: (timeout:10s, default:0)
```

## Demo Setting UI 

Once the app launches, you’ll see a settings window where you can configure.  
- Features Path  
- Number of Channels  
- Display Options (FPS, Dark/Light theme)  
- Font and Layout  

Click Done to apply the settings and start the demo.  

![Demo Settings UI](./../mkdocs/img/fig3.png){ width=700px }


## Troubleshooting Guide 

### Issue 1: `install_layout` Error 

**Error**
```
AttributeError: install_layout. Did you mean: 'install_platlib'?
      [end of output]

 note: This error originates from a subprocess, and is likely not a problem with pip.
 ERROR: Failed building wheel for dx-engine
Failed to build dx-engine
ERROR: Could not build wheels for dx-engine, which is required to install pyproject.toml-based projects
```

**Cause**  
Version mismatch between `pip`, `setuptools`, or `wheel`.

**Solution**
```
python3.11 -m pip install --upgrade pip setuptools wheel
```

### Issue 2: `ModuleNotFoundError`: No module named 'clip'`

**Error**
```
Traceback (most recent call last):
  File "<frozen runpy>", line 198, in _run_module_as_main
  File "<frozen runpy>", line 88, in _run_code
  File "/home/deepx/clip_demo_rt_v295/clip_demo_app_pyqt/dx_realtime_demo_pyqt.py", line 65, in <module>
    main()
  File "/home/deepx/clip_demo_rt_v295/clip_demo_app_pyqt/dx_realtime_demo_pyqt.py", line 56, in main
    settings_window = SettingsView(args, success_cb)
                      ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "/home/deepx/clip_demo_rt_v295/clip_demo_app_pyqt/view/settings_view.py", line 40, in __init__
    from clip_demo_app_pyqt.model.sentence_model import Sentence
  File "/home/deepx/clip_demo_rt_v295/clip_demo_app_pyqt/model/sentence_model.py", line 7, in <module>
    from clip_demo_app_pyqt.lib.clip.dx_text_encoder import TextVectorUtil
  File "/home/deepx/clip_demo_rt_v295/clip_demo_app_pyqt/lib/clip/dx_text_encoder.py", line 5, in <module>
    from clip.simple_tokenizer import SimpleTokenizer as ClipTokenizer
ModuleNotFoundError: No module named 'clip'
```

**Cause**  
The `clip` Python module is not installed in the environment.  

**Solution**  
```
cd clip_demo_rt_v295/assets/CLIP
pip install .
```

**NOTE.** Re-run the demo after installation.  

### Issue 3:`ModuleNotFoundError`: No module named `clip`

**Error**  
```
qt.qpa.plugin: Could not load the Qt platform plugin "xcb" in "" even though it was found.
This application failed to start because no Qt platform plugin could be initialized. Reinstalling the application may fix this problem.

```

**Cause**  
The system already has Qt libraries installed (e.g., `in /usr/lib/ or /lib/x86_64-linux-gnu/`)  
PyQt5 is installed in a local user directory (e.g., `~/.local/1`) or inside a virtual environment.  

**Solution**  
```
unset QT_PLUGIN_PATH
unset LD_LIBRARY_PATH
```


## Visualization Example: Real-Time CLIP in Action 
 
![Multichannel CLIP Inference on Edge Device](./../mkdocs/img/video1.gif){ width=700px }

This demo shows the system running real-time image-text matching across multiple video feeds using CLIP.  

**Key Highlights**  
- **Model**: CLIP (image encoder on NPU, text embeddings preloaded)  
- **Inference**: 16 channels concurrently  
-	**Overlay**: Semantic text output per channel, customizable layout and FPS display  

This demo is a powerful demonstration of multimodal AI on low-power hardware, ideal for smart surveillance, industrial vision, or embedded AI applications.

---

# Partnership with Advantech

**DEEPX** NPUs are embedded into Advantech’s industrial PCs.  

- Ready-to-deploy Edge AI with ultra-fast, real-time processing  
- All-in-one AI platform supporting instant multi-model inference  
- Scalable and cost-effective AIoT solutions for real-world deployment  

**Container Quick Start Guide**
For container quick start, including docker-compose file, and more, please refer to Advantech EdgeSync Container Repository


---
