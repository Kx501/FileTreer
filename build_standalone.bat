@echo off
chcp 65001 >nul
echo 开始编译 FileTreer（独立目录模式）...
python -m nuitka ^
    --standalone ^
    --windows-console-mode=disable ^
    --enable-plugin=tk-inter ^
    --include-module=config ^
    --include-module=filetree_generator ^
    --include-module=gui ^
    --assume-yes-for-downloads ^
    --output-dir=dist ^
    --output-filename=FileTreer.exe ^
    main.py

if %ERRORLEVEL% EQU 0 (
    echo 编译成功！可执行文件位于 dist\main.dist 目录
) else (
    echo 编译失败！
    pause
)

