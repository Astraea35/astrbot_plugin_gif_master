import os
import re
import uuid
import asyncio
import subprocess
from .utils import MediaResolver

class FfmpegConverter:
    def __init__(self, temp_dir: str, config: dict, resolver: MediaResolver):
        self.temp_dir = temp_dir
        self.config = config
        self.resolver = resolver

    async def handle_conversion(self, event, args: str):
        url = await self.resolver.get_media_url(event, "video")
        if not url:
            await event.send(event.plain_result("⚠️ 未发现可转换的视频！请长按引用群聊视频，或直接发送视频+指令。"))
            return
        
        width = self.config.get("default_width", 400)
        fps = self.config.get("default_fps", 15)
        speed = 1.0
        reverse = False
        rotation = 0
        
        w_match = re.search(r'-w\s+(\d+)', args)
        if w_match:
            width = min(int(w_match.group(1)), self.config.get("max_width", 720))
        s_match = re.search(r'-s\s+([\d.]+)', args)
        if s_match:
            speed = float(s_match.group(1))
        if '-r' in args:
            reverse = True
        rot_match = re.search(r'-rot\s+(\d+)', args)
        if rot_match:
            rotation = int(rot_match.group(1)) % 360
        
        vid_path = os.path.join(self.temp_dir, f"vid_{uuid.uuid4().hex[:8]}.mp4")
        webp_path = os.path.join(self.temp_dir, f"res_{uuid.uuid4().hex[:8]}.webp")
        
        try:
            await self.resolver.download_media(url, vid_path, event)
            await asyncio.to_thread(self._process_ffmpeg, vid_path, webp_path, width, speed, reverse, rotation, fps)
            if os.path.exists(vid_path):
                os.remove(vid_path)
            await self.resolver.respond_result(event, webp_path)
        except Exception as e:
            if os.path.exists(vid_path):
                os.remove(vid_path)
            await event.send(event.plain_result(f"❌ 视频转 WebP 失败: {str(e)}"))

    def _process_ffmpeg(self, in_p, out_p, w, s, r, rot, fps):
        vf_parts = [f"fps={fps}", f"scale={w}:-1:flags=lanczos"]
        if rot == 90:
            vf_parts.append("transpose=1")
        elif rot == 180:
            vf_parts.append("transpose=2,transpose=2")
        elif rot == 270:
            vf_parts.append("transpose=2")
        if s != 1.0:
            vf_parts.append(f"setpts={1.0/s}*PTS")
        if r:
            vf_parts.append("reverse")
        filter_str = ",".join(vf_parts)
        
        # 使用 libwebp 替代 GIF 的 palettegen 算法
        cmd = [
            "ffmpeg", "-y", "-i", in_p,
            "-vf", filter_str,
            "-c:v", "libwebp",
            "-lossless", "0",
            "-compression_level", "6",
            "-q:v", "90",
            "-loop", "0",
            out_p
        ]
        try:
            subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, text=True)
        except subprocess.CalledProcessError as e:
            raise Exception(f"FFmpeg处理失败:\n{e.stderr[-300:]}")