import os
import uuid
import asyncio
from PIL import Image as PILImage, ImageSequence, ImageDraw
from .utils import MediaResolver

class NestedProcessor:
    def __init__(self, temp_dir: str, config: dict, resolver: MediaResolver):
        self.temp_dir = temp_dir
        self.config = config
        self.resolver = resolver

    async def handle_nested(self, event, text: str):
        text = text.strip()
        if not text:
            await event.send(event.plain_result("请提供文案，使用 <> 或 {} 作为内嵌动图占位符。例如：/makegif 要我一直<>吗？"))
            return
            
        url = await self.resolver.get_media_url(event, "image", is_template=False)
        if not url:
            await event.send(event.plain_result("❌ 识别失败！请长按回复/引用一张完整的动图后再输入指令。"))
            return
            
        input_path = os.path.join(self.temp_dir, f"nest_in_{uuid.uuid4().hex[:6]}.img")
        out_path = os.path.join(self.temp_dir, f"nest_out_{uuid.uuid4().hex[:6]}.webp")
        try:
            await self.resolver.download_media(url, input_path, event)
            await asyncio.to_thread(self._process_nested, input_path, out_path, text)
            await self.resolver.respond_result(event, out_path)
        except Exception as e:
            await event.send(event.plain_result(f"❌ 套娃失败: {str(e)}"))
        finally:
            if os.path.exists(input_path):
                os.remove(input_path)

    def _process_nested(self, in_p, out_p, text):
        original_gif = PILImage.open(in_p)
        
        font_size = max(28, int(original_gif.width * 0.085))
        font = self.resolver.get_font(self.config.get("font_path", ""), font_size)
        
        if "<>" in text:
            left_text, right_text = text.split("<>", 1)
        elif "{}" in text:
            left_text, right_text = text.split("{}", 1)
        else:
            left_text, right_text = text, ""
        
        mini_gif_size = int(font_size * 1.4)
        
        temp_img = PILImage.new("RGBA", (1, 1))
        temp_img_draw = ImageDraw.Draw(temp_img)
        left_bbox = temp_img_draw.textbbox((0, 0), left_text, font=font)
        left_w, left_h = left_bbox[2] - left_bbox[0], left_bbox[3] - left_bbox[1]
        right_bbox = temp_img_draw.textbbox((0, 0), right_text, font=font)
        right_w = right_bbox[2] - right_bbox[0]
        
        bottom_row_width = left_w + 8 + mini_gif_size + 8 + right_w
        padding = max(16, int(original_gif.width * 0.04))
        
        canvas_w = max(original_gif.width, bottom_row_width) + padding * 2
        canvas_h = original_gif.height + max(left_h, mini_gif_size) + padding * 3
        
        bg_color = (0, 0, 0, 255) if self.config.get("bg_style") == "black" else (255, 255, 255, 255)
        text_color = (255, 255, 255, 255) if self.config.get("bg_style") == "black" else (0, 0, 0, 255)
        
        top_x = (canvas_w - original_gif.width) // 2
        top_y = padding
        row_start_x = (canvas_w - bottom_row_width) // 2
        row_y = top_y + original_gif.height + padding
        
        raw_frames = []
        for frame in ImageSequence.Iterator(original_gif):
            canvas = PILImage.new("RGBA", (canvas_w, canvas_h), bg_color)
            current_rgba = frame.convert('RGBA')
            canvas.paste(current_rgba, (top_x, top_y), current_rgba)
            draw = ImageDraw.Draw(canvas)
            draw.text((row_start_x, row_y), left_text, font=font, fill=text_color)
            
            mini_frame = current_rgba.resize((mini_gif_size, mini_gif_size), PILImage.Resampling.LANCZOS)
            mini_x = row_start_x + left_w + 8
            mini_y = row_y + (left_h - mini_gif_size) // 2 + 2
            canvas.paste(mini_frame, (mini_x, mini_y), mini_frame)
            draw.text((mini_x + mini_gif_size + 8, row_y), right_text, font=font, fill=text_color)
            raw_frames.append(canvas)
        
        # 直接输出高品质 WebP，省去原本 GIF 强制的 256 色 quantization
        duration = original_gif.info.get('duration', 100)
        loop = original_gif.info.get('loop', 0)
        MediaResolver.save_webp_safely(out_p, raw_frames, duration, loop=loop)