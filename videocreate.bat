@echo off
chcp 65001 > nul
cd /d "%~dp0"

echo --------------------------------------------------
echo  [1/2] 必要ライブラリ（Pillow / OpenCV）の準備状態をチェックしています...
echo --------------------------------------------------
python -m pip install Pillow opencv-python

echo.
echo --------------------------------------------------
echo  [2/2] 秒数合成プログラムを起動します。
echo --------------------------------------------------
python add_timestamp.py

pause