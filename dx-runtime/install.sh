#!/bin/bash
SCRIPT_DIR=$(realpath "$(dirname "$0")")
RUNTIME_PATH=$(realpath -s "${SCRIPT_DIR}")
RT_PATH="${RUNTIME_PATH}/dx_rt"

# Default VENV_PATH, can be overridden by --venv_path option
VENV_PATH_DEFAULT="${RUNTIME_PATH}/venv-dx-runtime"
VENV_PATH="${VENV_PATH_DEFAULT}" # Initialize with default

ENABLE_DEBUG_LOGS=0

# Global variables for script configuration
MIN_PY_VERSION="3.8.10"

# color env settings
source ${RUNTIME_PATH}/scripts/color_env.sh
source ${RUNTIME_PATH}/scripts/common_util.sh

function show_help() {
    print_colored "Usage: $(basename "$0") OPTIONS(--all | --target=<module_name>) [--help]" "YELLOW"
    print_colored "Example 1) $0 --all" "YELLOW"
    print_colored "Example 2) $0 --target=dx_rt_npu_linux_driver" "YELLOW"
    print_colored "Example 3) $0 --target=dx_rt --venv_path=/opt/my_runtime_venv --venv-reuse" "YELLOW"
    print_colored "Options:" "GREEN"
    print_colored "  --all                          : Install all dx-runtime modules (without firmware)" "GREEN"
    print_colored "  --target=<module_name>         : Install specify target dx-runtime module (ex> dx_fw | dx_rt_npu_linux_driver | dx_rt | dx_app | dx_stream)" "GREEN"
    print_colored "  [--use-ort=<y|n>]              : set 'USE_ORT' build option to 'ON or OFF' (default: y)" "GREEN"
    print_colored "  [--sanity-check=<y|n>]         : turn SanityCheck ON or OFF for dx_rt (default: y)" "GREEN"
    print_colored "  [--driver-source-build]        : build NPU driver from source if set (default: install via DKMS)" "GREEN"
    print_colored "  [--venv_path=<PATH>]           : Specify the path for the virtual environment (default: ${VENV_PATH_DEFAULT})" "GREEN"
    print_colored "  [-f, --venv-force-remove]      : Force remove existing virtual environment at --venv_path before creation." "GREEN"
    print_colored "  [-r, --venv-reuse]             : Reuse existing virtual environment at --venv_path if it's valid, skipping creation." "GREEN"
    print_colored "  [--verbose]                    : Enable verbose (debug) logging." "GREEN"
    print_colored "  [--help]                       : Show this help message" "GREEN"

    if [ "$1" == "error" ] && [[ ! -n "$2" ]]; then
        print_colored "Invalid or missing arguments." "ERROR"
        exit 1
    elif [ "$1" == "error" ] && [[ -n "$2" ]]; then
        print_colored "$2" "ERROR"
        exit 1
    elif [[ "$1" == "warn" ]] && [[ -n "$2" ]]; then
        print_colored "$2" "WARNING"
        return 0
    fi
    exit 0
}

function install_dx_rt_npu_linux_driver_via_source_build() {
    sudo apt update && sudo apt-get -y install pciutils kmod build-essential make linux-headers-6.11.0-17-generic
    
    pushd "$SCRIPT_DIR/dx_rt_npu_linux_driver"
    # if .gitmodules file is exist, submodule init and update.
    if [ -f .gitmodules ]; then
        git submodule update --init --recursive
    fi
    popd
    
    pushd "$SCRIPT_DIR/dx_rt_npu_linux_driver/modules"

    sudo ./build.sh -c uninstall
    ./build.sh
    yes n | sudo ./build.sh -c install
    sudo modprobe dx_dma
    lsmod | grep dx

    popd
}

function install_dx_rt_npu_linux_driver_via_dkms() {
    local deb_pattern="$SCRIPT_DIR/dx_rt_npu_linux_driver/release/latest/dxrt-driver-dkms*.deb"

    if compgen -G "$deb_pattern" > /dev/null; then
        pushd "$SCRIPT_DIR/dx_rt_npu_linux_driver/release/latest" > /dev/null
        sudo apt install -y ./dxrt-driver-dkms*.deb
        popd > /dev/null
    else
        print_colored "DKMS package not found. Switching to source build installation." "WARNING"
        install_dx_rt_npu_linux_driver_via_source_build
    fi
}

function install_dx_rt_npu_linux_driver() {
    DX_RT_DRIVER_INCLUDED=1

    if [ "${USE_DRIVER_SOURCE_BUILD}" = "y" ]; then
        install_dx_rt_npu_linux_driver_via_source_build
    else
        install_dx_rt_npu_linux_driver_via_dkms
    fi
}

function set_use_ort() {
    pushd "${RUNTIME_PATH}/dx_rt"
    CMAKE_FILE="cmake/dxrt.cfg.cmake"

    if [ "${USE_ORT}" = "y" ]; then
        sed -i 's/option(USE_ORT *"Use ONNX Runtime" *OFF)/option(USE_ORT "Use ONNX Runtime" ON)/' "$CMAKE_FILE"
        print_colored "USE_ORT option has been set to ON in dx_rt/$CMAKE_FILE" "INFO"
    else
        sed -i 's/option(USE_ORT *"Use ONNX Runtime" *ON)/option(USE_ORT "Use ONNX Runtime" OFF)/' "$CMAKE_FILE"
        print_colored "USE_ORT option is set to '${USE_ORT}'. so, USE_ORT option has been set to OFF in dx_rt/$CMAKE_FILE" "INFO"
    fi 

    popd
}

function sanity_check() {
    echo "--- sanity check... ---"

    if [ "${USE_SANITY_CHECK}" = "y" ]; then
        ${RUNTIME_PATH}/scripts/sanity_check.sh
        if [ $? -ne 0 ]; then
            print_colored "Sanity Check failed. Exiting." "ERROR"
            exit 1
        fi
    else
        print_colored "Skipped to Sanity Check..." "WARNING"
    fi
}

function install_dx_rt() {
    DX_RT_INCLUDED=1
    set_use_ort

    pushd "$SCRIPT_DIR/dx_rt"
    if [ "${USE_ORT}" = "y" ]; then
        ./install.sh --all
    else
        ./install.sh --dep
    fi
    ./build.sh --clean
    popd
}

function install_dx_rt_python_api() {
    print_colored_v2 "INFO" "=== Setup 'dx_engine' Python API... ==="

    . "${VENV_PATH}/bin/activate" && \
    pushd "${RT_PATH}/python_package" && \
    pip install . && \
    popd
    if [ $? -ne 0 ]; then
        print_colored_v2 "ERROR" "Python and Virual environment setup failed. Exiting."
        exit 1
    fi
    print_colored_v2 "INFO" "[OK] Setup 'dx_engine' Python API"
}

function install_dx_app() {
    DX_APP_INCLUDED=1

    pushd "$SCRIPT_DIR/dx_app"
    ./install.sh --all
    ./build.sh --clean
    popd
}

function install_dx_stream() {
    pushd "$SCRIPT_DIR/dx_stream"
    ./install.sh
    ./build.sh --install
    # gst-inspect-1.0 dxstream
    popd
}

function install_dx_fw() {
    if [ ! -f "$SCRIPT_DIR/dx_fw/m1/latest/mdot2/fw.bin" ]; then
        echo "Error: firmware file not found!"
        exit 1
    fi
    if ! command -v dxrt-cli &> /dev/null; then
        echo "Error: 'dxrt-cli' not found!"
        exit 1
    fi
    dxrt-cli -g "$SCRIPT_DIR/dx_fw/m1/latest/mdot2/fw.bin"
    dxrt-cli -u "$SCRIPT_DIR/dx_fw/m1/latest/mdot2/fw.bin"
    echo "It is recommended to power off completely and reboot after the firmware update."
}

function install_python() {
    print_colored "--- install python... ---" "INFO"

    local INSTALL_PY_CMD_ARGS=""

    if [ -n "$VENV_PATH" ]; then
        INSTALL_PY_CMD_ARGS+=" --venv_path=$VENV_PATH"
    fi
    
    if [ "${VENV_FORCE_REMOVE}" = "y" ]; then
        INSTALL_PY_CMD_ARGS+=" --venv-force-remove"
    fi

    if [ "${VENV_REUSE}" = "y" ]; then
        INSTALL_PY_CMD_ARGS+=" --venv-reuse"
    fi

    # Pass the determined VENV_PATH and new options to install_python_and_venv.sh
    INSTALL_PY_CMD="${RUNTIME_PATH}/scripts/install_python_and_venv.sh ${INSTALL_PY_CMD_ARGS}"
    echo "CMD: ${INSTALL_PY_CMD}"
    ${INSTALL_PY_CMD}
    if [ $? -ne 0 ]; then
        print_colored "Python and Virtual environment setup failed. Exiting." "ERROR"
        exit 1
    fi

    print_colored "[OK] Completed to install python" "INFO"
}

function host_reboot() {
    print_colored "The 'dx_rt_npu_linux_driver' has been installed." "INFO"
    print_colored "To complete the installation, the system must be restarted."
    echo -e -n "${COLOR_BRIGHT_GREEN_ON_BLACK}  Would you like to reboot now? (y/n): ${COLOR_RESET}"
    read -r answer
    if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
        echo "Start reboot..."
        sudo reboot now
    fi
}

function show_information_message() {
    if [[ ${DX_RT_INCLUDED} -eq 1 || ${DX_APP_INCLUDED} -eq 1 ]]; then
        print_colored "To activate the virtual environment, run:" "HINT"
        print_colored "  source ${VENV_PATH}/bin/activate " "HINT"
    fi

    if [ ${DX_RT_DRIVER_INCLUDED} -eq 1 ]; then
        host_reboot
    fi
}

DX_RT_INCLUDED=0
DX_APP_INCLUDED=0
DX_RT_DRIVER_INCLUDED=0

TARGET_PKG=""
USE_ORT="y"
USE_SANITY_CHECK="y"
USE_COMPILED_VERSION_CHECK="y" # This variable is not used in the provided script, kept for consistency.

# variables for venv options
USE_DRIVER_SOURCE_BUILD="n"
VENV_PATH_ARG="" # Stores user-provided venv path
VENV_FORCE_REMOVE="n"
VENV_REUSE="n"

# parse args
for i in "$@"; do
    case "$1" in
        --all)
            TARGET_PKG=all
            shift # past argument
            ;;
        --target=*)
            TARGET_PKG="${1#*=}"
            shift # past argument=value
            ;;
        --use-ort=*)
            USE_ORT="${1#*=}"
            shift # past argument=value
            ;;
        --sanity-check=*)
            USE_SANITY_CHECK="${1#*=}"
            shift # past argument=value
            ;;
        --driver-source-build)
            USE_DRIVER_SOURCE_BUILD="y"
            shift # past argument
            ;;
        --venv_path=*)
            VENV_PATH="${1#*=}"
            shift # past argument=value
            ;;
        -f|--venv-force-remove)
            VENV_FORCE_REMOVE="y"
            shift # past argument
            ;;
        -r|--venv-reuse)
            VENV_REUSE="y"
            shift # past argument
            ;;
        --verbose)
            ENABLE_DEBUG_LOGS=1
            shift # Consume argument
            ;;
        --help) 
            show_help
            ;;
        *)
            show_help "error" "Invalid option '$1'"
            ;;
    esac
done


case $TARGET_PKG in
    dx_rt_npu_linux_driver)
        print_colored "Installing dx_rt_npu_linux_driver..." "INFO"
        install_dx_rt_npu_linux_driver
        show_information_message
        print_colored "[OK] Installing dx_rt_npu_linux_driver" "INFO"
        ;;
    dx_rt)
        print_colored "Installing dx_rt..." "INFO"
        install_python # This now calls install_python_and_venv.sh with correct args
        install_dx_rt
        install_dx_rt_python_api
        sanity_check
        show_information_message
        print_colored "[OK] Installing dx_rt" "INFO"
        ;;
    dx_app)
        print_colored "Installing dx_app..." "INFO"
        install_python # This now calls install_python_and_venv.sh with correct args
        install_dx_rt_python_api
        install_dx_app
        show_information_message
        print_colored "[OK] Installing dx_app" "INFO"
        ;;
    dx_stream)
        print_colored "Installing dx_stream..." "INFO"
        install_dx_stream
        show_information_message
        print_colored "[OK] Installing dx_stream" "INFO"
        ;;
    dx_fw)
        print_colored "Installing dx_fw..." "INFO"
        install_dx_fw
        show_information_message
        print_colored "[OK] Installing dx_fw" "INFO"
        ;;
    all)
        print_colored "Installing all runtime modules..." "INFO"
        install_python # This now calls install_python_and_venv.sh with correct args
        install_dx_rt
        install_dx_rt_python_api
        install_dx_app
        install_dx_stream
        install_dx_rt_npu_linux_driver
        sanity_check
        show_information_message
        print_colored "[OK] Installing all runtime modules" "INFO"
        ;;
    *)
        show_help "error" "The '--all' option was not specified, or the '--target' option is invalid. Target packages will not be installed."
        ;;
esac
