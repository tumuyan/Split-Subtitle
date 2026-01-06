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
    start_time: float = 0.0
    end_time: float = 0.0
    start_line_num: int = 0
    end_line_num: int = 0
    last_speaker: str = None

    def set_start_time(self, start_time: float):
        """设置分片的开始时间（毫秒）"""
        if start_time < 0:
            self.start_time = 0.0
        else:
            self.start_time = start_time
    
    def set_end_time(self, end_time: float):
        """设置分片的结束时间（毫秒）"""
        if end_time < 0:
            self.end_time = 0.0
        else:
            self.end_time = end_time

    @property
    def duration(self) -> float:
        # 返回毫秒
        return self.end_time - self.start_time

    @property
    def line_count(self) -> int:
        return self.end_line_num - self.start_line_num + 1

    @property
    def notinited(self) -> int:
        return self.end_line_num <= 0

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

    # 分析说话人信息
    actors = {event.name for event in subs if event.name and event.name.strip()}
    multi_speaker = len(actors) > 1
    if len(actors) >= 1:
        console.print(f"说话人列表: [green]{', '.join(sorted(list(actors)))}[/green]")
    else:
        console.print("[yellow]未检测到有效的说话人信息[/yellow]")

    seg:Segment=None
    segments: List[Segment] = []

    last_end:float = 0.0
    pad:float=0.0
    line_num:int=0

    for i, event in enumerate(subs):
        line_num = i + 1

        gap = event.start - last_end
        if gap<=0:
            pad =0
        elif gap < (2 * padding_ms):
            # 如果间隙不足以容纳两边的padding，则在中间分割
            pad = gap / 2
        else:
            # 间隙足够，各自应用完整的padding
            pad = gap

        if seg:
            seg.set_end_time(last_end+pad)
        last_end = event.end

        if not seg:
            # 如果当前分片为空，则初始化
            seg = Segment(event.start-padding_ms,event.end,line_num,line_num)
            if event.name:
                seg.last_speaker = event.name
            # 无说话人时不再立即添加片段，而是等待达到最小时长再分割

        elif seg.duration >= min_duration_ms:
            if multi_speaker:
                if seg.last_speaker != event.name:
                    # 如果是多说话人且当前说话人与上一个分片的说话人不同，则分割
                    segments.append(seg)
                    seg = Segment(event.start-pad,event.end,line_num,line_num,event.name)
                else:
                    # 如果是多说话人且当前说话人与上一个分片的说话人相同，则继续累积
                    seg.set_end_time(event.end)
                    seg.end_line_num = line_num
                    if event.name:
                        seg.last_speaker = event.name
            else:
                # 如果是单说话人或无说话人，达到最小时长就分割
                segments.append(seg)
                seg = Segment(event.start-pad,event.end,line_num,line_num,event.name if event.name else None)
        else:
            seg.set_end_time(event.end)
            seg.end_line_num = line_num
            if event.name:
                seg.last_speaker = event.name

    if not seg:
        return segments

    if seg.duration < min_duration_ms and len(segments)>0:
        console.print("\n[yellow]最后一个分片过短，合并到上一个[/yellow]")
        segment = segments[-1]
        segment.end_time = last_end + padding_ms
        segment.end_line_num = line_num
        segments[-1] = segment
    else:
        seg.set_end_time(event.end+padding_ms)
        segments.append(seg)

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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只生成分片计划，不执行实际的分割操作。"
    )
    
    args = parser.parse_args()

    subtitle_path = Path(args.subtitle_file)
    media_path = Path(args.media_file)
    min_duration = args.time
    padding = args.padding
    dry_run = args.dry_run

    if not subtitle_path.is_file():
        console.print(f"[bold red]错误:[/bold red] 字幕文件未找到: {subtitle_path}")
        sys.exit(1)
    if not dry_run and not media_path.is_file():
        console.print(f"[bold red]错误:[/bold red] 媒体文件未找到: {media_path}")
        sys.exit(1)
        
    ffmpeg_exec = None
    if not dry_run:
        ffmpeg_exec = find_ffmpeg(args.ffmpeg, console)
        if not ffmpeg_exec:
            sys.exit(1)

    console.print("-" * 50)
    console.print(f"字幕文件: [cyan]{subtitle_path.name}[/cyan]")
    console.print(f"媒体文件: [cyan]{media_path.name}[/cyan]")
    if dry_run:
        console.print(f"FFmpeg路径: [yellow]跳过检查 (dry-run模式)[/yellow]")
    else:
        console.print(f"FFmpeg路径: [cyan]{ffmpeg_exec}[/cyan]")
    console.print(f"最小时长: [bold]{min_duration}[/bold] 秒")
    console.print(f"Padding: [bold]{padding}[/bold] 秒")
    if dry_run:
        console.print(f"运行模式: [yellow]dry-run (仅生成计划)[/yellow]")
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
    table.add_column("时长(秒)", justify="right")
    table.add_column("字幕行", justify="right")
    table.add_column("行数", justify="right")

    for i, seg in enumerate(segments):
        start_sec = seg.start_time / 1000.0
        end_sec = seg.end_time / 1000.0
        duration_sec = end_sec - start_sec
        
        start_str = format_time(start_sec)
        end_str = format_time(end_sec)
        duration_str = f"{duration_sec:.2f}"
        line_range = f"{seg.start_line_num}-{seg.end_line_num}"
        line_count = f"{seg.end_line_num-seg.start_line_num+1}"
        
        table.add_row(str(i+1), start_str, end_str, duration_str, line_range, line_count)

    console.print(table)
    # --- 表格打印优化结束 ---

    confirm = input("请确认是否按计划进行切分? (y/n, default=y): ")
    if confirm.lower() == 'n':
        console.print("[yellow]操作已取消。[/yellow]")
        sys.exit(0)

    if dry_run:
        console.print("\n[yellow]dry-run模式: 跳过实际分割操作[/yellow]")
        console.print("[bold]>> 分片计划生成完成。[/bold]")
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