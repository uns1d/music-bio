[app]
title = MusicBio
project_dir = .
input_file = main.py
exec_directory =
project_file =
icon =

[python]
python_path =
packages = Nuitka==4.1.3

[qt]
qml_files =
excluded_qml_plugins =
modules =
plugins =

[android]
wheel_pyside =
wheel_shiboken =
plugins =

[nuitka]
macos.permissions =
mode = onefile
extra_args = --quiet --noinclude-qt-translations --windows-console-mode=disable --assume-yes-for-downloads

[buildozer]
mode = debug
recipe_dir =
jars_dir =
ndk_path =
sdk_path =
local_libs =
arch =
