#!/bin/bash

SCRIPT_DIR=$(realpath "$(dirname "$0")")
PROJECT_ROOT="${SCRIPT_DIR}"

# Global variables for script configuration
APP_TYPE="pyqt"

# Default values
DXRT_SRC_PATH=$(realpath "${PROJECT_ROOT}/../dx-runtime/dx_rt/")
DOCKER_VOLUME_PATH=${DOCKER_VOLUME_PATH}

# color env settings
source ${SCRIPT_DIR}/scripts/color_env.sh
source ${SCRIPT_DIR}/scripts/common_util.sh

pushd $PROJECT_ROOT

# Function to display help message
show_help() {
  print_colored_v2 "YELLOW" "Usage: $(basename "$0") [OPTIONS]"
  print_colored_v2 "YELLOW" "Example 1) $0"
  print_colored_v2 "YELLOW" "Example 2) $0 --app_type=opencv"
  print_colored_v2 "YELLOW" "Example 3) $0 --app_type=pyqt --dxrt_src_path=${DXRT_SRC_PATH}"
  print_colored_v2 "YELLOW" "Example 4) $0 --app_type=opencv --dxrt_src_path=${DXRT_SRC_PATH}"
  print_colored_v2 "YELLOW" "Example 5) $0 --app_type=pyqt --docker_volume_path=/deepx/workspace"
  print_colored_v2 "GREEN" "Options:"
  print_colored_v2 "GREEN" "  [--app_type=<str>]              Set Application type (pyqt | opencv, default: pyqt)"
  print_colored_v2 "GREEN" "  [--dxrt_src_path=<path>]        Set DXRT source path (default: ${DXRT_SRC_PATH})"
  print_colored_v2 "GREEN" "  [--docker_volume_path=<path>]   Set Docker volume path (required in container mode)"
  print_colored_v2 "GREEN" "  [--help]                        Show this help message"

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

main() {
  # Check if running in a container
  if grep -qE "/docker|/lxc|/containerd" /proc/1/cgroup || [ -f /.dockerenv ]; then
    CONTAINER_MODE=true
    print_colored_v2 "INFO" "(container mode detected)"
    
    if [ -z "$DOCKER_VOLUME_PATH" ]; then
        show_help "error" "--docker_volume_path must be provided in container mode."
        show_help "error"
        exit 1
    fi

    SETUP_CLIP_ASSET_ARGS="--output=${ASSET_PATH} --symlink_target_path=${DOCKER_VOLUME_PATH}/res/clip"
    SETUP_CLIP_VIDEO_ARGS="--output=${VIDEO_PATH} --symlink_target_path=${DOCKER_VOLUME_PATH}/res/videos"
    VENV_SYMLINK_TARGET_PATH="${DOCKER_VOLUME_PATH}/venv/clip/${APP_TYPE}"
    VENV_SYMLINK_TARGET_PATH_ARGS="--venv_symlink_target_path=${VENV_SYMLINK_TARGET_PATH}"
  else
    print_colored_v2 "INFO" "(host mode detected)"
    WORKSPACE_PATH="../workspace-local"
    SETUP_CLIP_ASSET_ARGS="--output=${ASSET_PATH} --symlink_target_path=${WORKSPACE_PATH}/res/clip"
    SETUP_CLIP_VIDEO_ARGS="--output=${VIDEO_PATH} --symlink_target_path=${WORKSPACE_PATH}/res/videos"
    VENV_SYMLINK_TARGET_PATH="${WORKSPACE_PATH}/venv/clip/${APP_TYPE}-local"
    VENV_SYMLINK_TARGET_PATH_ARGS="--venv_symlink_target_path=${VENV_SYMLINK_TARGET_PATH}"
  fi

  print_colored_v2 "INFO" "ASSET_PATH: ${ASSET_PATH}"
  ASSET_REAL_PATH=$(readlink -f "$ASSET_PATH")
  # Check and set up assets
  if [ ! -d "$ASSET_REAL_PATH" ]; then
    print_colored_v2 "INFO" "Assets directory not found. Running setup assets script... ($ASSET_REAL_PATH)"
    ./setup_clip_assets.sh $SETUP_CLIP_ASSET_ARGS || { print_colored_v2 "ERROR" "Setup assets script failed."; rm -rf $ASSET_PATH; exit 1; }
  else
    print_colored_v2 "INFO" "Assets directory found. ($ASSET_REAL_PATH)"
  fi

  print_colored_v2 "INFO" "VIDEO_PATH: ${VIDEO_PATH}"
  VIDEO_REAL_PATH=$(readlink -f "$VIDEO_PATH")
  # Check and set up assets
  if [ ! -d "$VIDEO_REAL_PATH" ]; then
    print_colored_v2 "INFO" "Video directory not found. Running setup assets script... ($VIDEO_REAL_PATH)"
    ./setup_clip_videos.sh $SETUP_CLIP_VIDEO_ARGS || { print_colored_v2 "ERROR" "Setup assets script failed."; rm -rf $VIDEO_PATH; exit 1; }
  else
    print_colored_v2 "INFO" "Video directory found. ($VIDEO_REAL_PATH)"
  fi

  print_colored_v2 "INFO" "VENV_PATH: ${VENV_PATH}"
  VENV_REAL_PATH=$(readlink -f "$VENV_PATH")


  # Check and set up virtual environment
  if [ ! -f "$VENV_REAL_PATH/bin/activate" ]; then
    print_colored_v2 "INFO" "Virtual environment not found. Running setup script... ($VENV_REAL_PATH)"
    RUN_SETUP_CMD="./scripts/setup_clip_demo_app.sh --app_type=${APP_TYPE} --venv_path=${VENV_PATH} --dxrt_src_path=${DXRT_SRC_PATH} ${VENV_SYMLINK_TARGET_PATH_ARGS}"
    print_colored_v2 "YELLOW" "CMD : $RUN_SETUP_CMD"
    
    $RUN_SETUP_CMD || { print_colored_v2 "YELLOW" "Setup script failed."; rm -rf $VENV_PATH; exit 1; }
  else
    print_colored_v2 "YELLOW" "Virtual environment found. ($VENV_REAL_PATH)"
  fi

}

# Parse arguments
for i in "$@"; do
  case $i in
    --app_type=*)
      APP_TYPE="${i#*=}"
      ;;
    --dxrt_src_path=*)
      DXRT_SRC_PATH="${i#*=}"
      ;;
    --docker_volume_path=*)
      DOCKER_VOLUME_PATH="${i#*=}"
      ;;
    --help)
      show_help
      ;;
    *)
      show_help "error" "Unknown option: $1"
      ;;
  esac
shift
done

# Check if APP_TYPE is valid
if [ "$APP_TYPE" != "pyqt" ] && [ "$APP_TYPE" != "opencv" ]; then
  show_help "error" "'--app_type' option is invalid. It must be set to either 'pyqt' or 'opencv'."
fi

# Check if DXRT_SRC_PATH exists
if [ ! -d "$DXRT_SRC_PATH" ]; then
  show_help "error" "'--dxrt_src_path($DXRT_SRC_PATH)' option does not exist. please set path."
fi

ASSET_PATH=./assets
VIDEO_PATH=./assets/demo_videos
VENV_PATH="./venv-${APP_TYPE}"
CONTAINER_MODE=false

main

popd
