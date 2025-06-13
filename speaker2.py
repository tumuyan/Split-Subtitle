import argparse
import sys
from pathlib import Path
import pysubs2
from pyannote.audio import Pipeline
import torch
from tqdm import tqdm

def find_max_overlap_speaker(sub_start, sub_end, diarization):
    max_overlap = 0
    best_speaker = "Unknown" # 默认值
    
    for segment, _, speaker in diarization.itertracks(yield_label=True):
        overlap_start = max(sub_start, segment.start)
        overlap_end = min(sub_end, segment.end)
        overlap_duration = overlap_end - overlap_start
        
        if overlap_duration > max_overlap:
            max_overlap = overlap_duration
            best_speaker = speaker
            
    return best_speaker

def main():
    parser = argparse.ArgumentParser(
        description="使用本地的 pyannote.audio 模型进行说话人识别并与字幕对齐。",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument("subtitle_file", type=Path, help="输入的字幕文件路径 (srt 或 ass)。")
    parser.add_argument("media_file", type=Path, help="输入的视频或音频文件路径。")
    parser.add_argument("-o", "--output_file", type=Path, help="输出字幕文件路径。")
    parser.add_argument(
        "--model_dir", type=Path, default="./diarization_model",
        help="包含 pyannote 模型的本地文件夹路径。"
    )
    
    if len(sys.argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)
        
    args = parser.parse_args()
    
    output_path = args.output_file or args.subtitle_file.with_name(f"{args.subtitle_file.stem}.diarized_local{args.subtitle_file.suffix}")

    # --- 新增/修改部分：根据输出文件扩展名判断格式 ---
    # 决定输出格式是ASS还是其他格式，这会影响说话人信息的写入方式
    is_output_ass = output_path.suffix.lower() in ['.ass', '.ssa']
    
    # 检查模型文件夹和配置文件是否存在
    config_path = args.model_dir / "config.yaml"
    if not config_path.is_file():
        print(f"❌ 错误：在 '{args.model_dir}' 文件夹中找不到 'config.yaml'。")
        print("请确保您已成功下载模型，并且 --model_dir 参数指向了正确的路径。")
        sys.exit(1)

    # --- 1. 从本地路径初始化 Pipeline ---
    print(f"🔊 正在从本地路径 '{args.model_dir}' 加载模型...")
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"将使用 '{device}' 设备进行处理。")
    
    try:
        pipeline = Pipeline.from_pretrained(config_path)
        pipeline.to(torch.device(device))
    except Exception as e:
        print(f"\n❌ 从本地加载模型失败: {e}")
        sys.exit(1)

    # --- 2. 执行说话人日志 ---
    print(f"🔄 正在处理媒体文件: {args.media_file}...")
    print("这可能需要很长时间，取决于文件长度和您的硬件...")
    try:
        diarization = pipeline(str(args.media_file))
        print("✅ 说话人日志处理完成！")
    except Exception as e:
        print(f"\n❌ 处理媒体文件时出错: {e}")
        sys.exit(1)

    # --- 3. 加载字幕并对齐 ---
    print(f"📝 正在加载字幕文件: {args.subtitle_file} 并进行对齐...")
    subs = pysubs2.load(str(args.subtitle_file), encoding="utf-8")
    
    # --- 关键修改：使用 is_output_ass 进行判断 ---
    for sub_line in tqdm(subs, desc="对齐字幕"):
        sub_start_sec = sub_line.start / 1000.0
        sub_end_sec = sub_line.end / 1000.0
        
        speaker_id = find_max_overlap_speaker(sub_start_sec, sub_end_sec, diarization)
        
        if speaker_id != "Unknown":
            simple_id = speaker_id.split('_')[1].lstrip('0')
            speaker_name = f"Speaker {simple_id}"

            # 根据输出格式决定如何写入说话人
            if is_output_ass:
                # 对于 ASS/SSA 格式，填充 Name (Actor) 字段
                if not sub_line.name: # 只有当 Name 字段为空时才填充
                    sub_line.name = speaker_name
            else:
                # 对于 SRT 等其他格式，将说话人作为前缀添加到文本中
                sub_line.text = f"{speaker_name}: {sub_line.text}"

    # --- 4. 保存结果 ---
    subs.save(str(output_path), encoding="utf-8")
    
    print("\n🎉 全部完成！")
    print(f"输出文件已保存至: {output_path}")

if __name__ == "__main__":
    main()