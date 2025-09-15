#!/bin/bash
SCRIPT_DIR=$(realpath "$(dirname "$0")")
DX_AS_PATH=$(realpath -s "${SCRIPT_DIR}")

# color env settings
source ${DX_AS_PATH}/scripts/color_env.sh
source ${DX_AS_PATH}/scripts/common_util.sh

pushd "$DX_AS_PATH" >&2

OUTPUT_DIR="$DX_AS_PATH/archives"
UBUNTU_VERSION=""

USE_VOLUME=0
INTERNAL_MODE=0

# Function to display help message
show_help() {
    echo -e "Usage: ${COLOR_CYAN}$(basename "$0") --ubuntu_version=<version>${COLOR_RESET} [OPTIONS]"
    echo -e ""
    echo -e "${COLOR_BOLD}Required:${COLOR_RESET}"
    echo -e "  ${COLOR_GREEN}--ubuntu_version=<version>${COLOR_RESET}     Specify Ubuntu version (ex> 24.04)"
    echo -e ""
    echo -e "${COLOR_BOLD}Optional:${COLOR_RESET}"
    echo -e "  ${COLOR_GREEN}[--use-volume]${COLOR_RESET}                 Mount the workspace directory to the container"
    echo -e "                                   - Setup of dx-clip-demo will be skipped. "
    echo -e "                                   - You'll need to set it up after the container is running."
    echo -e "                                   - This option helps to reduce the final Docker image size."
    echo -e "  ${COLOR_GREEN}[--driver_update]${COLOR_RESET}              Install 'dx_rt_npu_linux_driver' in the host environment"
    echo -e "  ${COLOR_GREEN}[--no-cache]${COLOR_RESET}                   Build Docker images freshly without cache"
    echo -e "  ${COLOR_GREEN}[--help]${COLOR_RESET}                       Show this help message"
    echo -e ""
    echo -e "${COLOR_BOLD}Examples:${COLOR_RESET}"
    echo -e "  ${COLOR_YELLOW}$0 --ubuntu_version=24.04${COLOR_RESET}"
    echo -e "  ${COLOR_YELLOW}$0 --ubuntu_version=24.04 --driver_update${COLOR_RESET}"
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

docker_build_impl()
{
    local target=$1
    local config_file_args=${2:--f docker/docker-compose.yml}
    local no_cache_arg=""

    if [ ${INTERNAL_MODE} -eq 1 ]; then
        config_file_args="${config_file_args} -f docker/docker-compose.internal.yml"
    fi

    if [ "$NO_CACHE" = "y" ]; then
        no_cache_arg="--no-cache"
    fi

    # Build Docker image
    export COMPOSE_BAKE=true
    export UBUNTU_VERSION=${UBUNTU_VERSION}
    export USE_VOLUME=${USE_VOLUME}
    if [ ! -n "${XAUTHORITY}" ]; then
        print_colored_v2 "INFO" "XAUTHORITY env is not set. so, try to set automatically."
        DUMMY_XAUTHORITY="/tmp/dummy"
        touch ${DUMMY_XAUTHORITY}
        export XAUTHORITY=${DUMMY_XAUTHORITY}
        export XAUTHORITY_TARGET=${DUMMY_XAUTHORITY}
        
    else
        print_colored_v2 "INFO" "XAUTHORITY(${XAUTHORITY}) is set"
        export XAUTHORITY_TARGET="/tmp/.docker.xauth"
    fi

    CMD="docker compose ${config_file_args} build ${no_cache_arg} dx-${target}"
    echo "${CMD}"

    ${CMD} || { print_colored_v2 "ERROR" "docker build 'dx-${target}' failed. "; exit 1; }
}

docker_build_dx-clip-demo()
{
    local docker_compose_args="-f docker/docker-compose.yml"
    docker_build_impl "clip-demo" "${docker_compose_args}"
}

install_dx_rt_npu_linux_driver() 
{
    CMD="./dx-runtime/install.sh --target=dx_rt_npu_linux_driver"
    echo "${CMD}"

    ${CMD}
}

check_docker_compose_command() {
    check_docker_compose || {
        local message="Docker compose command not found."
        local hint_message="Please install docker compose first. Visit https://docs.docker.com/compose/install"
        local origin_cmd=""
        local suggested_action_cmd="${DX_AS_PATH}/scripts/install_docker.sh"
        local suggested_action_message="Do you want to install docker compose now?"
        local message_type="WARNING"

        handle_cmd_interactive "$message" "$hint_message" "$origin_cmd" "$suggested_action_cmd" "$suggested_action_message" "$message_type" || {
            show_help "error" "(Hint) User declined to install docker compose. Please install docker compose first. Visit https://docs.docker.com/compose/install"
        }
    }
}

main() {
    # check docker compose command
    check_docker_compose_command

    # usage
    if [ -z "$UBUNTU_VERSION" ]; then
        show_help "error" "--ubuntu_version option does not exist."
    else
        print_colored_v2 "INFO" "UBUNTU_VERSSION($UBUNTU_VERSION) is set."
        if [ "$DRIVER_UPDATE" = "y" ]; then
            print_colored_v2 "INFO" "DRIVER_UPDATE($DRIVER_UPDATE) is set."
        fi
        if [ "$NO_CACHE" = "y" ]; then
            print_colored_v2 "INFO" "NO_CACHE($NO_CACHE) is set."
        fi
    fi

    echo "Archiving dx-clip-demo"
    ${DX_AS_PATH}/scripts/archive_git_repos.sh || { print_colored_v2 "ERROR" "Archiving dx-clip-demo failed.\n${TAG_INFO} ${COLOR_BRIGHT_YELLOW_ON_BLACK}Please try running 'git submodule update --init --recursive --force' and then try again.${COLOR_RESET}"; exit 1; }
    docker_build_dx-clip-demo
    if [ "$DRIVER_UPDATE" = "y" ]; then
        install_dx_rt_npu_linux_driver
    fi

    # remove archives
    # if [[ -d "$OUTPUT_DIR" ]]; then
    #     echo "Removing archive directory: $OUTPUT_DIR"
    #     rm -rf "$OUTPUT_DIR"
    # fi
}

# parse args
for i in "$@"; do
    case "$1" in
        --ubuntu_version=*)
            UBUNTU_VERSION="${1#*=}"
            ;;
        --use-volume)
            USE_VOLUME=1
            ;;
        --driver_update)
            DRIVER_UPDATE=y
            ;;
        --no-cache)
            NO_CACHE=y
            ;;
        --help)
            show_help
            exit 0
            ;;
        --internal)
            INTERNAL_MODE=1
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
