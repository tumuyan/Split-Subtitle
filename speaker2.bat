@echo off
setlocal enabledelayedexpansion

goto :main_loop

:: =================================================================
::  ��ʱ���ӳ��� (���޸��˽�������)
:: =================================================================
:start_timer
set "start_time_%~1=%time%"
exit /b

:stop_timer
set "end_time=%time%"
set "start_time_str=!start_time_%~1!"

:: ���㿪ʼʱ����������� (1��=100����)
:: [�޸�] ʹ�� "1" ǰ׺����ǿ��ʮ���ƽ��������� 08/09 ��������Ч�˽�������
set /a "start_h=1!start_time_str:~0,2! - 100"
set /a "start_m=1!start_time_str:~3,2! - 100"
set /a "start_s=1!start_time_str:~6,2! - 100"
set /a "start_cs=1!start_time_str:~9,2! - 100"
set /a "total_start_cs=(start_h * 360000) + (start_m * 6000) + (start_s * 100) + start_cs"

:: �������ʱ�����������
set /a "end_h=1!end_time:~0,2! - 100"
set /a "end_m=1!end_time:~3,2! - 100"
set /a "end_s=1!end_time:~6,2! - 100"
set /a "end_cs=1!end_time:~9,2! - 100"
set /a "total_end_cs=(end_h * 360000) + (end_m * 6000) + (end_s * 100) + end_cs"

:: �������ҹ�����
if !total_end_cs! lss !total_start_cs! (
    set /a "total_end_cs+=8640000"
)

:: �����ʱ
set /a "duration_cs = total_end_cs - total_start_cs"
set /a "duration_s = duration_cs / 100"
set /a "duration_ms_part = (duration_cs %% 100) * 10"
set /a "duration_h = duration_s / 3600"
set /a "duration_m = (duration_s %% 3600) / 60"
set /a "final_s = duration_s %% 60"

:: [�Ż�] ��ʽ������Ϊ�̶���3λ�� (���� 050, 120)
set "padded_ms=00!duration_ms_part!"
set "padded_ms=!padded_ms:~-3!"

echo [��ʱ] %~1 ��ʱ: !duration_h!ʱ !duration_m!�� !final_s!�� !padded_ms!����
exit /b


:: --- ��ѭ�� ---
:main_loop
cls
echo =======================================================
echo      ����˵����ʶ����Ļ������ (V2.1)
echo =======================================================
echo.

:: --- ��ȡ����֤ý���ļ� ---
:get_media_file
set "MEDIA_FILE="
echo �뽫ý���ļ� (��Ƶ����Ƶ) ��ק���˴��ں� Enter:
set /p "MEDIA_FILE=> "
set "MEDIA_FILE=!MEDIA_FILE:"=!"
if not exist "!MEDIA_FILE!" (
    echo.
    echo [����] ý���ļ�������: "!MEDIA_FILE!"
    echo ����·���Ƿ���ȷ��Ȼ�����ԡ�
    echo.
    goto :get_media_file
)
echo [��֤ͨ��] ý���ļ�: "!MEDIA_FILE!"

:: --- ��ȡ����֤��Ļ�ļ� ---
:get_sub_file
set "SUB_FILE="
echo.
echo �뽫��Ļ�ļ� (.srt �� .ass) ��ק���˴��ں� Enter:
set /p "SUB_FILE=> "
set "SUB_FILE=!SUB_FILE:"=!"

:: 1. ����ļ��Ƿ����
if not exist "!SUB_FILE!" (
    echo.
    echo [����] ��Ļ�ļ�������: "!SUB_FILE!"
    echo ����·���Ƿ���ȷ��Ȼ�����ԡ�
    goto :get_sub_file
)

:: 2. �����Ļ�ļ���ʽ
set "SUB_EXT="
for %%F in ("!SUB_FILE!") do set "SUB_EXT=%%~xF"
if /i not "!SUB_EXT!"==".srt" if /i not "!SUB_EXT!"==".ass" (
    echo.
    echo [����] ��Ļ�ļ���ʽ����ȷ����֧�� .srt �� .ass �ļ���
    echo       ���ṩ���ļ���: !SUB_EXT!
    echo �������ṩ��ȷ��ʽ����Ļ�ļ���
    goto :get_sub_file
)
echo [��֤ͨ��] ��Ļ�ļ�: "!SUB_FILE!"


:: --- ��Ƶ���� ---
set "AUDIO_TO_PROCESS="
set "TEMP_WAV_CREATED=0"
set "TEMP_WAV_FILE=_temp_audio_for_diarization.wav"

set "MEDIA_EXT="
for %%F in ("!MEDIA_FILE!") do set "MEDIA_EXT=%%~xF"

if /i "!MEDIA_EXT!"==".wav" (
    echo.
    echo [��Ϣ] ��⵽�����ļ��� WAV����ֱ��ʹ�á�
    set "AUDIO_TO_PROCESS=!MEDIA_FILE!"
) else (
    echo.
    echo [��Ϣ] ��⵽�� WAV ý���ļ���������ȡ��ת��Ϊ��׼ WAV...
    echo      ��ʽ: 16kHz, 32λ����, ������
    
    call :start_timer FFmpeg
    ffmpeg -y -i "!MEDIA_FILE!" -vn -acodec pcm_s32le -ar 16000 -ac 1 "!TEMP_WAV_FILE!" >nul 2>&1
    set FFMPEG_EC=!errorlevel!
    call :stop_timer FFmpeg
    
    if !FFMPEG_EC! neq 0 (
        echo.
        echo [����] ʹ�� FFmpeg ת����Ƶʱʧ�ܣ�
        echo ����ý���ļ��Ƿ���֧���Լ� FFmpeg �Ƿ���������
        echo �밴������������˵�����...
        pause >nul
        goto main_loop
    )
    
    echo [�ɹ�] ��ʱ WAV �ļ�������: "!TEMP_WAV_FILE!"
    set "AUDIO_TO_PROCESS=!TEMP_WAV_FILE!"
    set "TEMP_WAV_CREATED=1"
)

:: --- ʶ��˵���� ---
set "OUTPUT_FILE="
for %%F in ("!SUB_FILE!") do set "OUTPUT_FILE=%%~dpnF.speaker.ass"

echo.
echo [��Ϣ] ׼������ Python �ű�����˵����ʶ�����й�������һЩ��������������...
echo      - ��Ļ����: "!SUB_FILE!"
echo      - ��Ƶ����: "!AUDIO_TO_PROCESS!"
echo      - ������: "!OUTPUT_FILE!"
echo.
echo --- ʶ��˵���˿�ʼ ---

call :start_timer Python
python speaker2.py "!SUB_FILE!" "!AUDIO_TO_PROCESS!" -o "!OUTPUT_FILE!"
call :stop_timer Python

echo --- ʶ��˵���˽��� ---
echo.

:: --- ������ʱ�ļ� ---
if !TEMP_WAV_CREATED!==1 (
    if exist "!TEMP_WAV_FILE!" (
        echo.
        echo [����] ɾ����ʱ WAV �ļ�...
        del "!TEMP_WAV_FILE!"
    )
)

:: --- �и��ļ� ---
python "!OUTPUT_FILE!" "!MEDIA_FILE!" --time 60

:: --- ѭ�����˳� ---
echo.
echo =======================================================
echo      ������ɣ�
echo =======================================================
echo.
set "CHOICE="
set /p "CHOICE=�� Enter ����������һ���ļ�, ������ Q ���� Enter �˳�: "
if /i "!CHOICE!"=="Q" (
    goto :end
)
goto main_loop


:end
endlocal
echo.
echo �ű����˳���
pause