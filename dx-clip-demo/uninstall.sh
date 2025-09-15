#!/bin/bash
SCRIPT_DIR=$(realpath "$(dirname "$0")")
PROJECT_ROOT=$(realpath "$SCRIPT_DIR")
DOWNLOAD_DIR="$SCRIPT_DIR/download"
PROJECT_NAME=$(basename "$SCRIPT_DIR")
VENV_PATH="$PROJECT_ROOT/venv-$PROJECT_NAME"

pushd "$PROJECT_ROOT" >&2

# color env settings
source ${PROJECT_ROOT}/scripts/color_env.sh
source ${PROJECT_ROOT}/scripts/common_util.sh

ENABLE_DEBUG_LOGS=0

show_help() {
    echo -e "Usage: ${COLOR_CYAN}$(basename "$0") [OPTIONS]${COLOR_RESET}"
    echo -e ""
    echo -e "Options:"
    echo -e "  ${COLOR_GREEN}[-v|--verbose]${COLOR_RESET}                        Enable verbose (debug) logging"
    echo -e "  ${COLOR_GREEN}[-h|--help]${COLOR_RESET}                           Display this help message and exit"
    echo -e ""
    
    if [ "$1" == "error" ] && [[ ! -n "$2" ]]; then
        print_colored_v2 "ERROR" "Invalid or missing arguments."
        exit 1
    elif [ "$1" == "error" ] && [[ -n "$2" ]]; then
        print_colored_v2 "ERROR" "$2"
        exit 1
    elif [[ "$1" == "warn" ]] && [[ -n "$2" ]]; then
        print_colored_v2 "WARNING" "$2"
        return 0
    fi
    exit 0
}

uninstall_common_files() {
    print_colored_v2 "INFO" "Uninstalling common files..."
    delete_symlinks "$DOWNLOAD_DIR"
    delete_symlinks "$PROJECT_ROOT"
    delete_symlinks "${VENV_PATH}"
    delete_symlinks "${VENV_PATH}-local"
    delete_dir "${VENV_PATH}"
    delete_dir "${VENV_PATH}-local"
    delete_dir "${DOWNLOAD_DIR}" 
}

uninstall_project_specific_files() {
    print_colored_v2 "INFO" "Uninstalling ${PROJECT_NAME} specific files..."

    data_file_path="${PROJECT_ROOT}/clip_demo_app_pyqt/data/data.json"
    if [ ! -f "$data_file_path" ]; then
        echo -e "${TAG_SKIP} File does not exist, not deleting: ${data_file_path}"
    else
        local message="Data file found at ${data_file_path}. It may contain user-specific data. Do you want to delete it?"
        local hint_msg="If you choose not to delete it now, you can manually delete it later if needed."
        local origin_cmd="" # no need to run origin command
        local suggested_action_cmd="delete_path \"${data_file_path}\""
        local suggested_action_message="Would you like to delete it now?"
        local message_type="WARNING"
        local default_input="N"

        handle_cmd_interactive "$message" "$hint_msg" "$origin_cmd" "$suggested_action_cmd" "$suggested_action_message" "$message_type" "$default_input" || {
            if [ $? -eq 5 ]; then
                echo -e "${TAG_SKIP} Skipping to delete data.json aborted by user."
            else
                echo -e "${TAG_ERROR} Uninstalling ${PROJECT_NAME} failed!"
                exit 1
            fi
        }
    fi
}

main() {
    print_colored_v2 "INFO" "Uninstalling ${PROJECT_NAME} ..."

    # Remove symlinks from DOWNLOAD_DIR and PROJECT_ROOT for 'Common' Rules
    uninstall_common_files

    # Uninstall the project specific files
    uninstall_project_specific_files

    print_colored_v2 "SUCCESS" "[OK] Uninstalling ${PROJECT_NAME} done"
}

# parse args
for i in "$@"; do
    case "$1" in
        -v|--verbose)
            ENABLE_DEBUG_LOGS=1
            ;;
        -h|--help)
            show_help
            ;;
        *)
            show_help "error" "Invalid option '$1'"
            ;;
    esac
    shift
done

main

popd >&2

exit 0
