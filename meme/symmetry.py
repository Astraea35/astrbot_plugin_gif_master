import os
import uuid
import asyncio
from PIL import Image as PILImage, ImageSequence, ImageOps
from .utils import MediaResolver

class SymmetryProcessor:
    def __init__(self, temp_dir: str, config: dict, resolver: MediaResolver):
        self.temp_dir = temp_dir
        self.config = config
        self.resolver = resolver

    async def handle_symmetry(self, event, direction: str):
        url = await self.resolver.get_media_url(event, "image", is_template=False)
        if not url:
            await event.send(event.plain_result("⚠️ 未捕捉到可用图片！请在发送指令的同时附带图片，或长按回复一张图片。"))
            return
            
        input_path = os.path.join(self.temp_dir, f"sym_in_{uuid.uuid4().hex[:6]}.img")
        out_path = os.path.join(self.temp_dir, f"sym_out_{uuid.uuid4().hex[:6]}.webp")
        try:
            await self.resolver.download_media(url, input_path, event)
            await asyncio.to_thread(self._process_symmetry, input_path, out_path, direction)
            await self.resolver.respond_result(event, out_path)
        except Exception as e:
            await event.send(event.plain_result(f"❌ 对称失败: {str(e)}"))
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)

    def _process_symmetry(self, in_p, out_p, direction):
        im = PILImage.open(in_p)
        frames, durations = [], []
        info_dur = im.info.get('duration', 100)
        
        for frame in ImageSequence.Iterator(im):
            f = frame.copy().convert('RGBA')
            w, h = f.size
            if direction == "left":
                left_half = f.crop((0, 0, w // 2, h))
                mirrored = ImageOps.mirror(left_half)
                new_img = PILImage.new('RGBA', (w, h))
                new_img.paste(left_half, (0, 0))
                new_img.paste(mirrored, (w // 2, 0))
                f = new_img
            elif direction == "right":
                right_half = f.crop((w // 2, 0, w, h))
                mirrored = ImageOps.mirror(right_half)
                new_img = PILImage.new('RGBA', (w, h))
                new_img.paste(mirrored, (0, 0))
                new_img.paste(right_half, (w // 2, 0))
                f = new_img
            elif direction == "top":
                top_half = f.crop((0, 0, w, h // 2))
                flipped = ImageOps.flip(top_half)
                new_img = PILImage.new('RGBA', (w, h))
                new_img.paste(top_half, (0, 0))
                new_img.paste(flipped, (0, h // 2))
                f = new_img
            elif direction == "bottom":
                bottom_half = f.crop((0, h // 2, w, h))
                flipped = ImageOps.flip(bottom_half)
                new_img = PILImage.new('RGBA', (w, h))
                new_img.paste(flipped, (0, 0))
                new_img.paste(bottom_half, (0, h // 2))
                f = new_img
            frames.append(f)
            durations.append(frame.info.get('duration', info_dur))
            
        MediaResolver.save_webp_safely(out_p, frames, durations, im.info.get('loop', 0))