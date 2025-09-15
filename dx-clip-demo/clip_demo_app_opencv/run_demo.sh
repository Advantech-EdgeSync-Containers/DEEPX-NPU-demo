#!/bin/bash

echo "0: Multi Channel"
echo "1: Single Channel"
echo "2: Single Channel (Camera mode)"

read -t 10 -p "which AI demo do you want to run:(timeout:10s, default:0)" select

case $select in
        0)./run_clip_multi_demo.sh;;
        1)./run_clip_single_demo.sh;;
        2)./run_clip_single_demo_camera_mode.sh;;
        *)./run_clip_multi_demo.sh;;
esac

