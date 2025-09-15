from pyqttoast import ToastPosition

COLOR_DICT = {
    "GREEN": '#3E9141',
    "YELLOW": '#E8B849',
    "RED": '#BA2626',
    "BLUE": '#007FFF'
}

COLOR_DICT_REVERSE = {
    '#3E9141': "GREEN",
    '#E8B849': "YELLOW",
    '#BA2626': "RED",
    '#007FFF': "BLUE"
}

POSITION_DICT = {
    ToastPosition.BOTTOM_LEFT.name: ToastPosition.BOTTOM_LEFT.value,
    ToastPosition.BOTTOM_MIDDLE.name: ToastPosition.BOTTOM_MIDDLE.value,
    ToastPosition.BOTTOM_RIGHT.name: ToastPosition.BOTTOM_RIGHT.value,
    ToastPosition.TOP_LEFT.name: ToastPosition.TOP_LEFT.value,
    ToastPosition.TOP_MIDDLE.name: ToastPosition.TOP_MIDDLE.value,
    ToastPosition.TOP_RIGHT.name: ToastPosition.TOP_RIGHT.value,
    ToastPosition.CENTER.name: ToastPosition.CENTER.value
}

POSITION_DICT_REVERSE = {
    ToastPosition.BOTTOM_LEFT.value: ToastPosition.BOTTOM_LEFT.name,
    ToastPosition.BOTTOM_MIDDLE.value: ToastPosition.BOTTOM_MIDDLE.name,
    ToastPosition.BOTTOM_RIGHT.value: ToastPosition.BOTTOM_RIGHT.name,
    ToastPosition.TOP_LEFT.value: ToastPosition.TOP_LEFT.name,
    ToastPosition.TOP_MIDDLE.value: ToastPosition.TOP_MIDDLE.name,
    ToastPosition.TOP_RIGHT.value: ToastPosition.TOP_RIGHT.name,
    ToastPosition.CENTER.value: ToastPosition.CENTER.name
}

STR_NO_FILE_SELECTED = "No file selected."
STR_SELECTED_FILE_WILL_BE_DISPLAYED = "The selected file path will be displayed here."
