#!/bin/bash

SCRIPT_DIR=$(realpath "$(dirname "$0")")
pushd $SCRIPT_DIR

APP_TYPE="pyqt"

# Function to display help message
show_help() {
  echo "Usage: $(basename "$0") [OPTIONS]"
  echo "Options:"
  echo "  [--app_type=<str>]           Set Application type (pyqt | opencv, default: pyqt)"
  echo "  --help                       Show this help message"

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
      shift
      ;;
    --help)
      show_help
      ;;
    *)
      # Unknown option
      ;;
  esac
done

# Check if APP_TYPE is valid
if [ "$APP_TYPE" != "pyqt" ] && [ "$APP_TYPE" != "opencv" ]; then
  echo "Error: APP_TYPE ($APP_TYPE) is invalid. It must be set to either 'pyqt' or 'opencv'."
  show_help "error"
fi

check_valid_dir_or_symlink() {
    local path="$1"
    if [ -d "$path" ] || { [ -L "$path" ] && [ -d "$(readlink -f "$path")" ]; }; then
        return 0
    else
        return 1
    fi
}

if check_valid_dir_or_symlink "./assets" && check_valid_dir_or_symlink "./assets/demo_videos"; then
    print_colored "Models and Videos directory already exists. Skipping download." "INFO"
else
    print_colored "Models and Videos not found. Downloading now via setup.sh..." "INFO"
    ./setup.sh
fi

# Run the demo application
pushd clip_demo_app_${APP_TYPE}
./run_demo.sh
popd

popd
