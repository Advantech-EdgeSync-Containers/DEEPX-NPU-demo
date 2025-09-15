#!/bin/bash

SCRIPT_DIR=$(realpath "$(dirname "$0")")

# Global variables for script configuration
APP_TYPE="pyqt"
CLEAN_VENV=0
CLEAN_ASSETS=0
CLEAN_DOWNLOAD=0
CLEAN_WORKSPACE=0

# color env settings
source ${SCRIPT_DIR}/scripts/color_env.sh
source ${SCRIPT_DIR}/scripts/common_util.sh

pushd $SCRIPT_DIR

# Function to display help message
show_help() {
  print_colored_v2 "YELLOW" "Usage: $(basename "$0") [OPTIONS]"
  print_colored_v2 "YELLOW" "Example 1) $0 --app_type=pyqt --all" 
  print_colored_v2 "YELLOW" "Example 2) $0 --app_type=pyqt --venv"
  print_colored_v2 "YELLOW" "Example 3) $0 --app_type=opencv --assets"
  print_colored_v2 "GREEN" "Options:"
  print_colored_v2 "GREEN" "  --all                          Clean assets and venv files"
  print_colored_v2 "GREEN" "  [--app_type=<str>]             Set Application type (pyqt | opencv, default: pyqt)"
  print_colored_v2 "GREEN" "  [--assets]                     Clean assets files"
  print_colored_v2 "GREEN" "  [--venv]                       Clean venv files"
  print_colored_v2 "GREEN" "  [--download]                   Clean downloaded files"
  print_colored_v2 "GREEN" "  [--workspace]                  Clean all files include workspace"

  print_colored_v2 "GREEN" "  [--help]                       Show this help message"

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

clean_target_path() {
  print_colored_v2 "DEBUG" "Clean $1..."

  local target_path=$1
  local target_real_dir=$(readlink -f "${target_path}")

  CMD="rm -rf ${target_venv_dir} ${target_path}"

  print_colored_v2 "YELLOW" "${CMD}"
  ${CMD} || { print_colored_v2 "ERROR" "Could not clean files for '$CMD'. Please try again with 'sudo'."; exit 1;}

  print_colored_v2 "DEBUG" "Clean $1 done."
}

clean_assets() {
  print_colored_v2 "INFO" "Clean assets..."

  clean_target_path "./assets"

  print_colored_v2 "INFO" "Clean assets done."
}

clean_venv() {
  print_colored_v2 "INFO" "Clean venv ($1)..."

  local target_app_type=$1
  local venv_path="./venv-${target_app_type}"
  clean_target_path "${venv_path}"

  print_colored_v2 "INFO" "Clean venv done."
}

clean_download() {
  print_colored_v2 "INFO" "Clean download..."

  clean_target_path "./download"

  print_colored_v2 "INFO" "Clean venv done."
}

clean_workspace() {
  print_colored_v2 "INFO" "Clean workspace..."

  clean_assets
  clean_venv "pyqt"
  clean_venv "opencv"
  clean_download
  clean_target_path "../workspace"
  clean_target_path "../workspace-local"

  print_colored_v2 "INFO" "Clean venv done."
}


main() {
  if [ $CLEAN_ASSETS -eq 1 ]; then
    clean_assets
  fi

  if [ $CLEAN_VENV -eq 1 ]; then
    clean_venv "$APP_TYPE"
  fi

  if [ $CLEAN_DOWNLOAD -eq 1 ]; then
    clean_download
  fi

  if [ $CLEAN_WORKSPACE -eq 1 ]; then
    clean_workspace
  fi
}

# Parse arguments
for i in "$@"; do
  case $i in
    --app_type=*)
      APP_TYPE="${i#*=}"
      ;;
    --all)
      CLEAN_VENV=1
      CLEAN_ASSETS=1
      ;;
    --venv)
      CLEAN_VENV=1
      ;;
    --assets)
      CLEAN_ASSETS=1
      ;;
    --download)
      CLEAN_DOWNLOAD=1
      ;;
    --workspace)
      CLEAN_WORKSPACE=1
      ;;
    --verbose)
      ENABLE_DEBUG_LOGS=1
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

main

popd
