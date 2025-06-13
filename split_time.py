# --- START OF FILE split_time.py (Optimized with rich) ---

import argparse
import subprocess
import sys
import pysubs2
from pathlib import Path
import shutil
from dataclasses import dataclass, field
from typing import List, Optional

# 导入 rich 库的关键组件
try:
    from rich.console import Console
    from rich.table import Table
except ImportError:
    print("错误: rich 库未安装。请运行 'pip install rich' 进行安装。")
    sys.exit(1)


# --- 全局常量 ---
FFMPEG_DEFAULT_ARGS = ['-map', '0', '-c', 'copy', '-y']
DEFAULT_MIN_DURATION = 60.0
DEFAULT_PADDING = 0.5

@dataclass
class Segment:
    """
    用于存储分片信息的数据类
    注意：这里的 start_time 和 end_time 内部存储为毫秒
    """
    start_time: float
    end_time: float
    start_line_num: int
    end_line_num: int
    lines: List[str] = field(default_factory=list)

    @property
    def duration(self) -> float:
        # 返回毫秒
        return self.end_time - self.start_time

    @property
    def line_count(self) -> int:
        return len(self.lines)

def find_ffmpeg(ffmpeg_path: Optional[str], console: Console) -> Optional[str]:
    """在系统PATH或用户指定路径中查找ffmpeg可执行文件"""
    if ffmpeg_path:
        if Path(ffmpeg_path).is_file():
            return ffmpeg_path
        else:
            console.print(f"[bold red]错误:[/bold red] 在指定路径未找到ffmpeg: {ffmpeg_path}")
            return None
    
    found_path = shutil.which('ffmpeg')
    if found_path:
        return found_path
    
    console.print("[bold red]错误:[/bold red] 未在系统PATH中找到ffmpeg。请使用 --ffmpeg 参数指定其路径。")
    return None

def format_time(seconds: float) -> str:
    """将秒数格式化为 HH:MM:SS.mmm 的字符串"""
    if seconds < 0:
        seconds = 0
    milliseconds = int((seconds - int(seconds)) * 1000)
    seconds = int(seconds)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}.{milliseconds:03d}"

def analyze_segments(
    subs: pysubs2.SSAFile,
    min_duration: float,
    padding: float,
    console: Console
) -> List[Segment]:
    """
    分析字幕并生成分片计划
    """
    if not subs:
        return []

    # 将输入的秒转换为毫秒，以统一单位
    min_duration_ms = min_duration * 1000
    padding_ms = padding * 1000

    # 1. 分析说话人信息
    actors = {event.name for event in subs if event.name and event.name.strip()}
    multi_speaker = len(actors) > 1
    console.print(f"字幕分析: {'[cyan]检测到多个说话人[/cyan]' if multi_speaker else '[yellow]未检测到多个或有效的说话人信息[/yellow]'}")
    if multi_speaker:
        console.print(f"说话人列表: [green]{', '.join(sorted(list(actors)))}[/green]")

    segments: List[Segment] = []
    current_lines = []
    
    for i, event in enumerate(subs):
        line_num = i + 1
        line_text = f"L{line_num} ({event.name or 'N/A'}): {event.text}"
        
        if not current_lines:
            current_lines.append({'event': event, 'line_num': line_num, 'text': line_text})
            continue

        should_split = False
        start_event = current_lines[0]['event']
        potential_duration = event.end - start_event.start

        if potential_duration >= min_duration_ms:
            if multi_speaker:
                last_event = current_lines[-1]['event']
                if event.name != last_event.name:
                    should_split = True
            else:
                should_split = True
        
        if should_split:
            last_event_in_segment = current_lines[-1]['event']
            gap = event.start - last_event_in_segment.end
            
            start_time = current_lines[0]['event'].start
            end_time = last_event_in_segment.end

            if gap < (2 * padding_ms):
                split_point = gap / 2
                end_time += split_point
                next_start_time = event.start - split_point
            else:
                end_time += padding_ms
                next_start_time = event.start - padding_ms

            segment = Segment(
                start_time=start_time,
                end_time=end_time,
                start_line_num=current_lines[0]['line_num'],
                end_line_num=current_lines[-1]['line_num'],
                lines=[item['text'] for item in current_lines]
            )
            segments.append(segment)
            
            event.start = next_start_time
            current_lines = [{'event': event, 'line_num': line_num, 'text': line_text}]
        else:
            current_lines.append({'event': event, 'line_num': line_num, 'text': line_text})

    if current_lines:
        start_event = current_lines[0]['event']
        end_event = current_lines[-1]['event']
        
        segment = Segment(
            start_time=start_event.start,
            end_time=end_event.end + padding_ms,
            start_line_num=current_lines[0]['line_num'],
            end_line_num=current_lines[-1]['line_num'],
            lines=[item['text'] for item in current_lines]
        )
        segments.append(segment)

    if len(segments) >= 2 and segments[-1].duration < (min_duration_ms / 2):
        console.print("\n[yellow]检测到最后一个分片过短，正在合并到上一个分片...[/yellow]")
        last_segment = segments.pop()
        second_last_segment = segments[-1]
        
        second_last_segment.end_time = last_segment.end_time
        second_last_segment.end_line_num = last_segment.end_line_num
        second_last_segment.lines.extend(last_segment.lines)
        console.print("[green]合并完成。[/green]")

    return segments

def main():
    # 初始化 rich console
    console = Console()

    parser = argparse.ArgumentParser(
        description="根据字幕文件将媒体文件分割成多个片段。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    # ... (前面的 parser.add_argument 部分保持不变) ...
    parser.add_argument("subtitle_file", help="ASS/SSA 字幕文件路径。")
    parser.add_argument("media_file", help="视频或音频媒体文件路径。")
    parser.add_argument(
        "-t", "--time",
        type=float,
        default=DEFAULT_MIN_DURATION,
        help=f"每个片段的最小目标时长（秒）。\n默认: {DEFAULT_MIN_DURATION}秒。"
    )
    parser.add_argument(
        "-p", "--padding",
        type=float,
        default=DEFAULT_PADDING,
        help=f"在片段前后添加的填充时间（秒）。\n默认: {DEFAULT_PADDING}秒。"
    )
    parser.add_argument(
        "--ffmpeg",
        help="FFmpeg可执行文件的路径。\n如果未提供，脚本将尝试在系统PATH中查找。"
    )
    
    args = parser.parse_args()

    subtitle_path = Path(args.subtitle_file)
    media_path = Path(args.media_file)
    min_duration = args.time
    padding = args.padding

    if not subtitle_path.is_file():
        console.print(f"[bold red]错误:[/bold red] 字幕文件未找到: {subtitle_path}")
        sys.exit(1)
    if not media_path.is_file():
        console.print(f"[bold red]错误:[/bold red] 媒体文件未找到: {media_path}")
        sys.exit(1)
        
    ffmpeg_exec = find_ffmpeg(args.ffmpeg, console)
    if not ffmpeg_exec:
        sys.exit(1)

    console.print("-" * 50)
    console.print(f"字幕文件: [cyan]{subtitle_path.name}[/cyan]")
    console.print(f"媒体文件: [cyan]{media_path.name}[/cyan]")
    console.print(f"FFmpeg路径: [cyan]{ffmpeg_exec}[/cyan]")
    console.print(f"最小时长: [bold]{min_duration}[/bold] 秒")
    console.print(f"Padding: [bold]{padding}[/bold] 秒")
    console.print("-" * 50)

    try:
        subs = pysubs2.load(str(subtitle_path), encoding="utf-8")
        subs.sort()
    except Exception as e:
        console.print(f"[bold red]错误:[/bold red] 解析字幕文件失败: {e}")
        sys.exit(1)
        
    if not subs:
        console.print("[bold yellow]警告:[/bold yellow] 字幕文件为空或不包含任何有效事件。")
        sys.exit(0)

    segments = analyze_segments(subs, min_duration, padding, console)

    if not segments:
        console.print("[yellow]未能根据设定条件生成任何分片。[/yellow]")
        sys.exit(0)

    # --- 使用 rich Table 优化表格打印 ---
    table = Table(title="分片计划分析", show_header=True, header_style="bold magenta")
    table.add_column("片段", style="dim", width=6, justify="right")
    table.add_column("开始时间", justify="center", style="cyan")
    table.add_column("结束时间", justify="center", style="cyan")
    table.add_column("时长(秒)", justify="right", style="green")
    table.add_column("字幕行", justify="center")
    table.add_column("行数", justify="right")

    for i, seg in enumerate(segments):
        start_sec = seg.start_time / 1000.0
        end_sec = seg.end_time / 1000.0
        duration_sec = seg.duration / 1000.0
        
        start_str = format_time(start_sec)
        end_str = format_time(end_sec)
        duration_str = f"{duration_sec:.2f}"
        line_range = f"{seg.start_line_num}-{seg.end_line_num}"
        line_count = f"{seg.line_count}"
        
        table.add_row(str(i+1), start_str, end_str, duration_str, line_range, line_count)

    console.print(table)
    # --- 表格打印优化结束 ---

    confirm = input("以上是分片计划。是否继续执行FFmpeg进行切分? (y/n, default=y): ")
    if confirm.lower() == 'n':
        console.print("[yellow]操作已取消。[/yellow]")
        sys.exit(0)

    output_dir = media_path.parent / f"{media_path.stem}_segments"
    output_dir.mkdir(exist_ok=True)
    
    # ------------------- 这是修改后的行 -------------------
    console.print(f"\n文件将输出到目录: [link={output_dir.resolve().as_uri()}]{output_dir}[/link]")
    # ------------------------------------------------------

    success_count = 0
    fail_count = 0

    for i, seg in enumerate(segments):
        output_filename = output_dir / f"{media_path.stem}_segment_{i+1:03d}{media_path.suffix}"
        
        start_sec = seg.start_time / 1000.0
        end_sec = seg.end_time / 1000.0
        
        cmd = [
            ffmpeg_exec,
            '-ss', format_time(start_sec),
            '-to', format_time(end_sec),
            '-i', str(media_path),
        ]
        cmd.extend(FFMPEG_DEFAULT_ARGS)
        cmd.append(str(output_filename))
        
        try:
            # 1. 在 status 中显示动态的“处理中”信息
            status_message = f"处理中 [bold cyan]{i+1}/{len(segments)}[/bold cyan]: [green]{output_filename.name}[/green]"
            with console.status(status_message, spinner="dots"):
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding='utf-8')
                stdout, stderr = process.communicate()
            
            # 2. 任务完成后，打印简洁的最终结果
            if process.returncode == 0:
                # 成功: 打印带对勾的一行
                console.print(f"  [bold green]✓[/bold green] {output_filename.name}")
                success_count += 1
            else:
                # 失败: 打印带叉的一行，并附上错误详情
                console.print(f"  [bold red]✗[/bold red] {output_filename.name} - FFmpeg执行失败")
                fail_count += 1
                # 只在失败时打印详细错误
                error_lines = [f"    [red]{line}[/red]" for line in stderr.splitlines() if 'frame=' not in line]
                if error_lines:
                    console.print("\n".join(error_lines))

        except Exception as e:
            console.print(f"  [bold red]✗[/bold red] {output_filename.name} - 执行时发生错误: {e}")
            fail_count += 1

    # --- 循环结束，打印总结信息 ---
    console.print("\n[bold]>> 所有分片处理完成。[/bold]")
    console.print(f"[green]成功: {success_count}[/green], [red]失败: {fail_count}[/red]")


if __name__ == "__main__":
    main()