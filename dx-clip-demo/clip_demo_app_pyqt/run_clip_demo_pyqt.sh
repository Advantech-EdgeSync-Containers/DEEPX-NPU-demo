#!/bin/bash
cd ..

if gst-inspect-1.0 vaapidecodebin &>/dev/null; then
    echo "vaapidecodebin is exist"
    export QT5_LIB_PATH=$(python -c "import site; print(site.getsitepackages()[0])")/PyQt5/Qt5/lib
    export LD_LIBRARY_PATH=$QT5_LIB_PATH:$LD_LIBRARY_PATH
    echo "QT5_LIB_PATH: $QT5_LIB_PATH"
    echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"
else
    echo "vaapidecodebin not found"
fi

source ./venv-pyqt/bin/activate
python -m clip_demo_app_pyqt.dx_realtime_demo_pyqt "$@"
