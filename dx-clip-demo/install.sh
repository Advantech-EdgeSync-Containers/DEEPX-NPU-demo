#!/bin/bash

APP_TYPE="pyqt"
SCRIPT_DIR=$(realpath "$(dirname "$0")")
PROJECT_ROOT="${SCRIPT_DIR}"
VENV_PATH="${PROJECT_ROOT}/venv-${APP_TYPE}"

source ${SCRIPT_DIR}/scripts/color_env.sh

install_package_if_available() {
    local package_name="$1"

    echo "📦 Attempting to install the '$package_name' package."

    # Check if the package exists in the repository
    if apt-cache search "$package_name" | grep -q "^$package_name"; then
        echo "✅ The '$package_name' package exists in the repository. Proceeding with installation..."
        sudo apt-get update
        sudo apt-get install -y "$package_name"
        if [ $? -eq 0 ]; then
            echo "👍 The '$package_name' package was installed successfully."
        else
            echo "❌ An error occurred while installing the '$package_name' package."
        fi
    else
        echo "⚠️ The '$package_name' package does not exist in the repository. Skipping installation."
    fi
    echo "" # Add a blank line for better readability
}

check_virtualenv() {
    if [ -n "$VIRTUAL_ENV" ]; then
        venv_name=$(basename "$VIRTUAL_ENV")
        if [ "$venv_name" = "$APP_TYPE" ] || [ "$venv_name" = "$APP_TYPE-local" ]; then
            echo "✅ Virtual environment '$venv_name' is currently active."
            return 0
        else
            echo "⚠️ A different virtual environment '$venv_name' is currently active."
            return 1
        fi
    else
        echo "❌ No virtual environment is currently active."
        return 1
    fi
}

install_deps(){
    echo -e "=== install_deps() ${TAG_START:-[START]} ==="

    # --- Upgrade pip, wheel, and setuptools ---
    echo "Upgrading pip, wheel, and setuptools..."

    # Check for /etc/os-release to identify the OS
    if [ -f /etc/os-release ]; then
        # shellcheck source=/etc/os-release
        . /etc/os-release
    else
        echo "Cannot determine the operating system: /etc/os-release not found." >&2
        exit 1
    fi

    if [ "$ID" = "ubuntu" ]; then
        UBUNTU_VERSION=$(lsb_release -rs)
        echo "*** Ubuntu Version (${UBUNTU_VERSION}) detected. ***"

        if [ "$UBUNTU_VERSION" = "24.04" ]; then
            pip install --upgrade "setuptools<=70.0.0"
        elif [[ "$UBUNTU_VERSION" == "22.04" || "$UBUNTU_VERSION" == "20.04" || "$UBUNTU_VERSION" == "18.04" ]]; then
            pip install --upgrade pip wheel "setuptools<=70.0.0"
        else
            echo "Unsupported Ubuntu version: $UBUNTU_VERSION" >&2
            exit 1
        fi
    elif [ "$ID" = "debian" ]; then
        DEBIAN_VERSION_ID=${VERSION_ID}
        echo "*** Debian Version (${DEBIAN_VERSION_ID}) detected. ***"

        if [ "$DEBIAN_VERSION_ID" = "12" ]; then
            python3 -m pip install --upgrade pip wheel "setuptools<=70.0.0"
        else
            echo "Unsupported Debian version: $DEBIAN_VERSION_ID" >&2
            exit 1
        fi
    else
        # Handle other non-supported operating systems
        echo "This script currently supports Ubuntu and Debian 12 only."
        echo "Detected OS: $PRETTY_NAME" >&2
        exit 1
    fi

    echo "Upgrade complete."

    ### Pre-Requisite
    if [[ "$APP_TYPE" == "opencv" ]]; then
        echo "Running in OpenCV mode"
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update && sudo apt-get install -y python3 python3-dev python3-venv python3-tk
    elif [[ "$APP_TYPE" == "pyqt" ]]; then
        echo "Running in PyQT mode"
        sudo add-apt-repository -y ppa:deadsnakes/ppa
        sudo apt-get update && sudo apt-get install -y python3 python3-dev python3-venv libxcb-xinerama0
    else
        echo -e "${TAG_ERROR:-[ERROR]} APP_TYPE must be either 'opencv' or 'pyqt'." >&2
        exit 1
    fi

    ### Install dependencies for Demo APP
    if [[ "$APP_TYPE" == "opencv" ]]; then
        #### 3. Install packages (gstreamer, qt5 multimedia plugins for play mp3, mp4, gif files)
        pip install -r requirements.${APP_TYPE}.txt
        pip install ./assets/CLIP
    elif [[ "$APP_TYPE" == "pyqt" ]]; then
        #### 3. Install packages (gstreamer, qt5 multimedia plugins for play mp3, mp4, gif files)
        sudo apt-get install -y build-essential qtbase5-dev    # for source build on Ubuntu 20.04, Ubuntu 18.04
        sudo apt-get install -y libxcb-xinerama0 libxcb-cursor0 libxcb-icccm4 libxcb-keysyms1 libxcb-randr0 libxcb-render-util0 libxcb-xfixes0 libxcb-shape0 libxcb-sync1 libxkbcommon-x11-0 libxcb-xkb1
        sudo apt-get install -y libqt5multimedia5-plugins libpulse-mainloop-glib0
        sudo apt-get install -y python3-pyqt5 python3-pyqt5.qtmultimedia

        # Attempt to install the python3-pyqt5.sip package
        install_package_if_available "python3-pyqt5.sip"

        #### 4. Install pip packages
        pip install -r requirements.${APP_TYPE}.txt
        pip install ./assets/CLIP
    else
        echo -e "${TAG_ERROR:-[ERROR]} APP_TYPE must be either 'opencv' or 'pyqt'." >&2
        exit 1
    fi
    echo -e "=== install_deps() ${TAG_DONE:-[DONE]} ==="
}

activate_venv() {
    echo -e "=== activate_venv() ${TAG_START} ==="

    # activate venv
    source ${VENV_PATH}/bin/activate
    if [ $? -ne 0 ]; then
        echo -e "${TAG_ERROR} Activate venv failed! Please try installing again with the '--force' option."
        rm -rf "$VENV_PATH"
        echo -e "${TAG_ERROR} === ACTIVATE VENV FAIL ==="
        exit 1
    fi

    echo -e "=== activate_venv() ${TAG_DONE} ==="
}

main() {
    if check_virtualenv; then
        install_deps
    else
        if [ -d "$VENV_PATH" ]; then
            activate_venv
            install_deps
        else
            echo -e "${TAG_HINT}${COLOR_BRIGHT_BLUE_ON_BLACK} Virtual environment '${VENV_PATH}' is not exist.${COLOR_RESET}"
	    echo -e -n "${COLOR_BRIGHT_GREEN_ON_BLACK}  Would you like to setup now? (y/n): ${COLOR_RESET}"
            read -r answer
            if [[ "$answer" == "y" || "$answer" == "Y" ]]; then
                echo "Start Setup..."
                ${PROJECT_ROOT}/setup.sh && { echo -e "${TAG_DONE}} Setup Done."; main; } || { echo -e "${TAG_ERROR} Fail to setup..."; exit 1; }
            else
                echo -e "${TAG_HINT}${COLOR_BRIGHT_BLUE_ON_BLACK} Please run 'setup.sh' to set up and activate the environment first.${COLOR_RESET}"
            fi
        fi
    fi
}

# Function to display help message
show_help() {
    echo "Usage: $(basename "$0") [OPTIONS]"
    echo "Example: $0 --app_type=pyqt"
    echo "Options:"
    echo "  --app_type=<str>                     Set Application type (pyqt | opencv)"
    echo "  [--help]                             Show this help message"

    if [ "$1" == "error" ]; then
        echo "Error: Invalid or missing arguments."
        exit 1
    fi
    exit 0
}

# Parse arguments
for i in "$@"; do
    case $i in
        --app_type=*)
            APP_TYPE="${i#*=}"
            ;;
        --help)
            show_help
            ;;
        *)
            echo "Unknown option: $1"
            exit 1
          ;;
    esac
shift
done

# Check if APP_TYPE is valid
if [ "$APP_TYPE" != "pyqt" ] && [ "$APP_TYPE" != "opencv" ]; then
  show_help "error" "'--app_type' option is invalid. It must be set to either 'pyqt' or 'opencv'."
fi

main

exit 0

