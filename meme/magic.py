import os
import uuid
import asyncio
from PIL import Image as PILImage, ImageSequence, ImageOps
from .utils import MediaResolver

class MagicProcessor:
    def __init__(self, temp_dir: str, config: dict, resolver: MediaResolver):
        self.temp_dir = temp_dir
        self.config = config
        self.resolver = resolver

    async def handle_magic(self, event, action: str, param: float = 1.0):
        url = await self.resolver.get_media_url(event, "image", is_template=False)
        if not url:
            await event.send(event.plain_result("⚠️ 未捕捉到可用图片！请在发送指令的同时附带图片，或长按回复一张动图。"))
            return
            
        input_path = os.path.join(self.temp_dir, f"in_{uuid.uuid4().hex[:6]}.img")
        out_path = os.path.join(self.temp_dir, f"magic_{uuid.uuid4().hex[:6]}.webp")
        try:
            await self.resolver.download_media(url, input_path, event)
            await asyncio.to_thread(self._process_pipeline, input_path, out_path, action, param)
            await self.resolver.respond_result(event, out_path)
        except Exception as e:
            await event.send(event.plain_result(f"❌ 魔法变换失败: {str(e)}"))
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)

    def _process_pipeline(self, in_p, out_p, action, param):
        im = PILImage.open(in_p)
        frames, durations = [], []
        info_dur = im.info.get('duration', 100)
        
        for frame in ImageSequence.Iterator(im):
            f = frame.copy().convert('RGBA')
            
            if action == "flip_h":
                f = ImageOps.mirror(f)
            elif action == "flip_v":
                f = ImageOps.flip(f)
            elif action == "rotate":
                f = f.rotate(270, expand=True)
            elif action == "invert":
                r, g, b, a = f.split()
                rgb_inverted = ImageOps.invert(PILImage.merge('RGB', (r, g, b)))
                f = PILImage.merge('RGBA', (*rgb_inverted.split(), a))
                
            frames.append(f)
            durations.append(frame.info.get('duration', info_dur))
            
        if action == "reverse":
            frames.reverse()
            durations.reverse()
        elif action == "rebound" and len(frames) > 1:
            frames = frames + frames[-2:0:-1]
            durations = durations + durations[-2:0:-1]
        elif action == "speed":
            durations = [max(30, int(d / param)) for d in durations]
            
        MediaResolver.save_webp_safely(out_p, frames, durations, im.info.get('loop', 0))