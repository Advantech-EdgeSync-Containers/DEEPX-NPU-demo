#!/bin/bash

echo "1: Single Channel Demo"
echo "1-2: Single Channel Demo (Settings Mode)"
echo "1-3: Single Channel Demo (Camera Mode & Settings Mode)"
echo "2: Multi Channel Demo"
echo "2-2: Multi Channel Demo (Settings Mode)"
echo "2-3: Multi Channel Demo (Camera Mode & Settings Mode)"
echo "0: Default Demo"

read -t 10 -p "which AI demo do you want to run:(timeout:10s, default:0)" select

case $select in
        1)./run_clip_demo_pyqt.sh --number_of_channels 1;;
        1-2)./run_clip_demo_pyqt.sh --number_of_channels 1 --settings_mode 1;;
        1-3)./run_clip_demo_pyqt.sh --number_of_channels 1 --settings_mode 1 --camera_mode 1 --merge_central_grid 1;;
        2)./run_clip_demo_pyqt.sh --number_of_channels 16;;
        2-2)./run_clip_demo_pyqt.sh --number_of_channels 16 --settings_mode 1;;
        2-3)./run_clip_demo_pyqt.sh --number_of_channels 16 --settings_mode 1 --camera_mode 1 --merge_central_grid 1;;
        *)./run_clip_demo_pyqt.sh;;
esac
