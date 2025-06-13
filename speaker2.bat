@echo off
setlocal enabledelayedexpansion

goto :main_loop

:: =================================================================
::  计时器子程序 (已修复八进制问题)
:: =================================================================
:start_timer
set "start_time_%~1=%time%"
exit /b

:stop_timer
set "end_time=%time%"
set "start_time_str=!start_time_%~1!"

:: 计算开始时间的总厘秒数 (1秒=100厘秒)
:: [修复] 使用 "1" 前缀技巧强制十进制解析，避免 08/09 被当作无效八进制数。
set /a "start_h=1!start_time_str:~0,2! - 100"
set /a "start_m=1!start_time_str:~3,2! - 100"
set /a "start_s=1!start_time_str:~6,2! - 100"
set /a "start_cs=1!start_time_str:~9,2! - 100"
set /a "total_start_cs=(start_h * 360000) + (start_m * 6000) + (start_s * 100) + start_cs"

:: 计算结束时间的总厘秒数
set /a "end_h=1!end_time:~0,2! - 100"
set /a "end_m=1!end_time:~3,2! - 100"
set /a "end_s=1!end_time:~6,2! - 100"
set /a "end_cs=1!end_time:~9,2! - 100"
set /a "total_end_cs=(end_h * 360000) + (end_m * 6000) + (end_s * 100) + end_cs"

:: 处理跨午夜的情况
if !total_end_cs! lss !total_start_cs! (
    set /a "total_end_cs+=8640000"
)

:: 计算耗时
set /a "duration_cs = total_end_cs - total_start_cs"
set /a "duration_s = duration_cs / 100"
set /a "duration_ms_part = (duration_cs %% 100) * 10"
set /a "duration_h = duration_s / 3600"
set /a "duration_m = (duration_s %% 3600) / 60"
set /a "final_s = duration_s %% 60"

:: [优化] 格式化毫秒为固定的3位数 (例如 050, 120)
set "padded_ms=00!duration_ms_part!"
set "padded_ms=!padded_ms:~-3!"

echo [计时] %~1 耗时: !duration_h!时 !duration_m!分 !final_s!秒 !padded_ms!毫秒
exit /b


:: --- 主循环 ---
:main_loop
cls
echo =======================================================
echo      批量说话人识别字幕处理工具 (V2.1)
echo =======================================================
echo.

:: --- 获取并验证媒体文件 ---
:get_media_file
set "MEDIA_FILE="
echo 请将媒体文件 (视频或音频) 拖拽到此窗口后按 Enter:
set /p "MEDIA_FILE=> "
set "MEDIA_FILE=!MEDIA_FILE:"=!"
if not exist "!MEDIA_FILE!" (
    echo.
    echo [错误] 媒体文件不存在: "!MEDIA_FILE!"
    echo 请检查路径是否正确，然后重试。
    echo.
    goto :get_media_file
)
echo [验证通过] 媒体文件: "!MEDIA_FILE!"

:: --- 获取并验证字幕文件 ---
:get_sub_file
set "SUB_FILE="
echo.
echo 请将字幕文件 (.srt 或 .ass) 拖拽到此窗口后按 Enter:
set /p "SUB_FILE=> "
set "SUB_FILE=!SUB_FILE:"=!"

:: 1. 检查文件是否存在
if not exist "!SUB_FILE!" (
    echo.
    echo [错误] 字幕文件不存在: "!SUB_FILE!"
    echo 请检查路径是否正确，然后重试。
    goto :get_sub_file
)

:: 2. 检查字幕文件格式
set "SUB_EXT="
for %%F in ("!SUB_FILE!") do set "SUB_EXT=%%~xF"
if /i not "!SUB_EXT!"==".srt" if /i not "!SUB_EXT!"==".ass" (
    echo.
    echo [错误] 字幕文件格式不正确。仅支持 .srt 或 .ass 文件。
    echo       您提供的文件是: !SUB_EXT!
    echo 请重新提供正确格式的字幕文件。
    goto :get_sub_file
)
echo [验证通过] 字幕文件: "!SUB_FILE!"


:: --- 音频处理 ---
set "AUDIO_TO_PROCESS="
set "TEMP_WAV_CREATED=0"
set "TEMP_WAV_FILE=_temp_audio_for_diarization.wav"

set "MEDIA_EXT="
for %%F in ("!MEDIA_FILE!") do set "MEDIA_EXT=%%~xF"

if /i "!MEDIA_EXT!"==".wav" (
    echo.
    echo [信息] 检测到输入文件是 WAV，将直接使用。
    set "AUDIO_TO_PROCESS=!MEDIA_FILE!"
) else (
    echo.
    echo [信息] 检测到非 WAV 媒体文件，正在提取并转换为标准 WAV...
    echo      格式: 16kHz, 32位浮点, 单声道
    
    call :start_timer FFmpeg
    ffmpeg -y -i "!MEDIA_FILE!" -vn -acodec pcm_s32le -ar 16000 -ac 1 "!TEMP_WAV_FILE!" >nul 2>&1
    set FFMPEG_EC=!errorlevel!
    call :stop_timer FFmpeg
    
    if !FFMPEG_EC! neq 0 (
        echo.
        echo [错误] 使用 FFmpeg 转换音频时失败！
        echo 请检查媒体文件是否受支持以及 FFmpeg 是否工作正常。
        echo 请按任意键返回主菜单重试...
        pause >nul
        goto main_loop
    )
    
    echo [成功] 临时 WAV 文件已生成: "!TEMP_WAV_FILE!"
    set "AUDIO_TO_PROCESS=!TEMP_WAV_FILE!"
    set "TEMP_WAV_CREATED=1"
)

:: --- 识别说话人 ---
set "OUTPUT_FILE="
for %%F in ("!SUB_FILE!") do set "OUTPUT_FILE=%%~dpnF.speaker.ass"

echo.
echo [信息] 准备调用 Python 脚本进行说话人识别，运行过程中有一些警告是正常现象...
echo      - 字幕输入: "!SUB_FILE!"
echo      - 音频输入: "!AUDIO_TO_PROCESS!"
echo      - 结果输出: "!OUTPUT_FILE!"
echo.
echo --- 识别说话人开始 ---

call :start_timer Python
python speaker2.py "!SUB_FILE!" "!AUDIO_TO_PROCESS!" -o "!OUTPUT_FILE!"
call :stop_timer Python

echo --- 识别说话人结束 ---
echo.

:: --- 清理临时文件 ---
if !TEMP_WAV_CREATED!==1 (
    if exist "!TEMP_WAV_FILE!" (
        echo.
        echo [清理] 删除临时 WAV 文件...
        del "!TEMP_WAV_FILE!"
    )
)

:: --- 切割文件 ---
python "!OUTPUT_FILE!" "!MEDIA_FILE!" --time 60

:: --- 循环或退出 ---
echo.
echo =======================================================
echo      任务完成！
echo =======================================================
echo.
set "CHOICE="
set /p "CHOICE=按 Enter 继续处理下一个文件, 或输入 Q 并按 Enter 退出: "
if /i "!CHOICE!"=="Q" (
    goto :end
)
goto main_loop


:end
endlocal
echo.
echo 脚本已退出。
pause