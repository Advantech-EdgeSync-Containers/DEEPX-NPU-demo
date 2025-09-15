# RELEASE_NOTES

## v1.0.0 / 2025-07-23
### 1. Changed
- None
### 2. Fixed
- None
### 3. Added
- **Initial version release of DX-Runtime (DX-RT).** This core runtime software facilitates executing `.dxnn` models on DEEPX NPU hardware. It offers direct NPU interaction via firmware and device drivers, leveraging PCIe for high-speed data transfer. DX-RT provides C/C++ and Python APIs for application-level inference control, a complete runtime environment (including model loading, I/O buffer management, inference execution, and real-time hardware monitoring), an integrated inference workflow from input/pre-processing (using OpenCV) to post-processing and display, and configurable Inference Options to specify target devices and resources for optimized execution.


---

# DX-Runtime v1.0.0 Release Notes

**v1.0.0 / 2025-07-28**

---

### 1. Changed
* None

### 2. Fixed
* None

### 3. Added
* **Initial version release of DX-Runtime (DX-RT).** This is the core runtime software for executing `.dxnn` models on DEEPX NPU hardware.
* **Direct NPU Interaction:** DX-RT directly interacts with DEEPX NPU through firmware and device drivers, utilizing PCIe for high-speed data transfer.
* **C/C++ and Python APIs:** Provides APIs for application-level inference control, enabling flexible integration into various projects.
* **Complete Runtime Environment:** Offers comprehensive features including model loading, I/O buffer management, inference execution, and real-time hardware monitoring.
* **Integrated Inference Workflow:** Supports an end-to-end inference flow from input/pre-processing (using OpenCV) to post-processing and display.
* **Configurable Inference Options:** Allows configuration of InferenceOption to specify target devices and available resources for optimized execution.

---