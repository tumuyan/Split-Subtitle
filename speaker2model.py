import torch
from pyannote.audio import Pipeline
import os
# pip install pyannote.audio 

# --- 在这里填入您的 Hugging Face Token ---
# 这是一个有读权限的token即可
HF_TOKEN = "hf_xxxxx" 

# 模型将要保存到的本地文件夹名
MODEL_DIR = "./diarization_model"

if __name__ == "__main__":
    if not HF_TOKEN or "xxx" in HF_TOKEN:
        print("错误：请在脚本中填入您自己的 Hugging Face Token。")
        exit()

    print(f"正在下载并保存模型到 '{MODEL_DIR}' 文件夹...")
    
    try:
        # 使用 token 从 Hub 下载
        pipeline = Pipeline.from_pretrained(
            "pyannote/speaker-diarization-3.1",
            use_auth_token=HF_TOKEN
        )
        
        # 将下载的模型的所有相关文件保存到本地指定目录
        # pyannote 的新版本可能不再需要手动保存，下载时会自动缓存
        # 但为了确保，我们可以手动指定路径保存
        # 不过，更简单的方式是直接让 from_pretrained 下载到默认缓存
        # 然后我们从缓存中找到它。
        # 一个更直接的方法是让 pipeline 自己处理。
        # 如果需要打包，我们需要找到缓存位置。
        # find cache_dir
        from huggingface_hub import snapshot_download
        
        snapshot_download(
            repo_id="pyannote/speaker-diarization-3.1",
            use_auth_token=HF_TOKEN,
            local_dir=MODEL_DIR,
            local_dir_use_symlinks=False # 使用复制而不是符号链接，方便打包
        )

        print("\n✅ 模型下载并保存成功！")
        print(f"现在您可以将 '{MODEL_DIR}' 文件夹和主程序一起分发给用户。")

    except Exception as e:
        print(f"\n❌ 下载模型时出错。请检查：")
        print("1. 您的 Hugging Face token 是否有效。")
        print("2. 您是否已在模型页面同意用户协议: https://huggingface.co/pyannote/speaker-diarization-3.1")
        print(f"原始错误: {e}")