@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

:: 脚本名称
set "SCRIPT_NAME=%~nx0"
:: 脚本所在目录
set "SCRIPT_DIR=%~dp0"

:: --- 默认设置 ---
set DEFAULT_SPLIT_TIME=300
:: 默认运行模式: python
set DEFAULT_RUN_MODE=python
:: 运行模式: exe 或 python
set "RUN_MODE=%DEFAULT_RUN_MODE%"

:: --- 参数解析 ---
:parse_args
if "%1"=="" goto :parse_args_end
if /i "%1"=="--exe" (
    set RUN_MODE=exe
    shift
    goto :parse_args
)
if /i "%1"=="--python" (
    set RUN_MODE=python
    shift
    goto :parse_args
)
goto :parse_args_end
:parse_args_end

:: --- 验证运行模式对应的文件是否存在 ---
set "PYTHON_SCRIPT=%SCRIPT_DIR%split_time.py"
set "EXE_FILE=%SCRIPT_DIR%split_time.exe"

:: 检查文件是否存在
set "PYTHON_EXISTS=0"
if exist "%PYTHON_SCRIPT%" set PYTHON_EXISTS=1

set "EXE_EXISTS=0"
if exist "%EXE_FILE%" set EXE_EXISTS=1

:: 自动修正运行模式
if "%RUN_MODE%"=="exe" (
    if %EXE_EXISTS% EQU 0 (
        echo [警告] 未找到 split_time.exe，自动切换到 Python 模式
        set RUN_MODE=python
    )
) else (
    if %PYTHON_EXISTS% EQU 0 (
        echo [警告] 未找到 split_time.py，自动切换到 EXE 模式
        set RUN_MODE=exe
        :: 再次检查 EXE 文件是否存在
        if %EXE_EXISTS% EQU 0 (
            echo [错误] 既未找到 split_time.py 也未找到 split_time.exe
            pause
            exit /b 1
        )
    )
)

echo [设置] 运行模式: %RUN_MODE%

cls
echo =======================================================
echo            字幕分割工具 (V1.0)
echo =======================================================
echo [运行模式] %RUN_MODE%
echo =======================================================
echo.

:: --- 交互式获取媒体文件 ---
:get_media_file
set "MEDIA_FILE="
echo 请输入媒体文件路径（或拖拽文件到此处），然后按 Enter:
echo 支持的格式: .mp4, .mp3, .avi, .mkv, .wav, .flac, .mov, .wmv
set /p "MEDIA_FILE=^> "
:: 移除引号
set "MEDIA_FILE=!MEDIA_FILE:"=!"
:: 检查文件是否存在
if not exist "!MEDIA_FILE!" (
    echo.
    echo [错误] 媒体文件不存在: "!MEDIA_FILE!"
    echo 请检查路径是否正确，然后重新输入。
    echo.
    goto :get_media_file
)
:: 验证媒体文件扩展名
for %%F in ("!MEDIA_FILE!") do (
    set "MEDIA_EXT=%%~xF"
    set "MEDIA_EXT_LOWER=%%~xF"
)
:: 转换为小写以便比较
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.MP4=.mp4!"
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.MP3=.mp3!"
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.AVI=.avi!"
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.MKV=.mkv!"
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.WAV=.wav!"
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.FLAC=.flac!"
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.MOV=.mov!"
set "MEDIA_EXT_LOWER=!MEDIA_EXT_LOWER:.WMV=.wmv!"

:: 检查是否为支持的媒体文件格式
if not "!MEDIA_EXT_LOWER!"==".mp4" if not "!MEDIA_EXT_LOWER!"==".mp3" if not "!MEDIA_EXT_LOWER!"==".avi" if not "!MEDIA_EXT_LOWER!"==".mkv" if not "!MEDIA_EXT_LOWER!"==".wav" if not "!MEDIA_EXT_LOWER!"==".flac" if not "!MEDIA_EXT_LOWER!"==".mov" if not "!MEDIA_EXT_LOWER!"==".wmv" (
    echo.
    echo [错误] 不支持的媒体文件格式: !MEDIA_EXT!
    echo 支持的格式: .mp4, .mp3, .avi, .mkv, .wav, .flac, .mov, .wmv
    echo 请重新输入正确的媒体文件。
    echo.
    goto :get_media_file
)
echo [验证通过] 媒体文件: "!MEDIA_FILE!"

:: --- 交互式获取字幕文件 ---
:get_sub_file
set "SUB_FILE="
echo.
echo 请输入字幕文件路径（或拖拽文件到此处），然后按 Enter:
echo 支持的格式: .srt, .ass
set /p "SUB_FILE=^> "
:: 移除引号
set "SUB_FILE=!SUB_FILE:"=!"
:: 检查文件是否存在
if not exist "!SUB_FILE!" (
    echo.
    echo [错误] 字幕文件不存在: "!SUB_FILE!"
    echo 请检查路径是否正确，然后重新输入。
    echo.
    goto :get_sub_file
)
:: 验证字幕文件扩展名
for %%F in ("!SUB_FILE!") do (
    set "SUB_EXT=%%~xF"
    set "SUB_EXT_LOWER=%%~xF"
)
:: 转换为小写以便比较
set "SUB_EXT_LOWER=!SUB_EXT_LOWER:.SRT=.srt!"
set "SUB_EXT_LOWER=!SUB_EXT_LOWER:.ASS=.ass!"

:: 检查是否为支持的字幕文件格式
if not "!SUB_EXT_LOWER!"==".srt" if not "!SUB_EXT_LOWER!"==".ass" (
    echo.
    echo [错误] 不支持的字幕文件格式: !SUB_EXT!
    echo 支持的格式: .srt, .ass
    echo 请重新输入正确的字幕文件。
    echo.
    goto :get_sub_file
)
echo [验证通过] 字幕文件: "!SUB_FILE!"

:: --- 交互式获取分割时长 ---
:get_split_time
set "SPLIT_TIME="
echo.
echo 请输入每个片段的最小目标时长（秒），按 Enter 使用默认值 %DEFAULT_SPLIT_TIME% 秒:
set /p "SPLIT_TIME=^> "
:: 检查输入是否为空，使用默认值
if "!SPLIT_TIME!"=="" (
    set SPLIT_TIME=%DEFAULT_SPLIT_TIME%
    echo [使用默认值] 分割时长: !SPLIT_TIME! 秒
) else (
    :: 移除可能的空格
    set "SPLIT_TIME=!SPLIT_TIME: =!"
    :: 简化的数字验证 - 只检查是否为正数
    set /a "TEST_NUM=!SPLIT_TIME!+0"
    if !ERRORLEVEL! NEQ 0 (
        echo.
        echo [错误] 输入的时长不是有效的数字，请重新输入。
        echo.
        goto :get_split_time
    )
    :: 检查是否为正数
    if !TEST_NUM! LEQ 0 (
        echo.
        echo [错误] 输入的时长必须大于 0，请重新输入。
        echo.
        goto :get_split_time
    )
    echo [验证通过] 分割时长: !SPLIT_TIME! 秒
)

echo.
echo =======================================================
echo                  开始分割
echo =======================================================
echo.
echo 正在调用 %RUN_MODE% 进行分割...
echo.

:: --- 执行分割命令 ---
if "%RUN_MODE%"=="exe" (
    "%EXE_FILE%" "!SUB_FILE!" "!MEDIA_FILE!" --time !SPLIT_TIME!
) else (
    python "%PYTHON_SCRIPT%" "!SUB_FILE!" "!MEDIA_FILE!" --time !SPLIT_TIME!
)

:: 保存执行结果
set "EXEC_RESULT=%ERRORLEVEL%"

echo.
echo =======================================================
echo                  分割完成
echo =======================================================
echo [执行结果] 退出代码: %EXEC_RESULT%
echo.
pause

endlocal

exit /b %EXEC_RESULT%
