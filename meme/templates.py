import os
import re
import uuid
import asyncio
from PIL import Image as PILImage, ImageDraw
from .utils import MediaResolver

class TemplateProcessor:
    def __init__(self, temp_dir: str, config: dict, resolver: MediaResolver):
        self.temp_dir = temp_dir
        self.config = config
        self.resolver = resolver
        self.resource_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "resource")

    @staticmethod
    def _natural_sort_key(filename: str):
        return [int(part) if part.isdigit() else part.lower()
                for part in re.split(r'(\d+)', filename)]

    async def handle_template(self, event, template_name: str, require_at: bool = False):
        target_url = await self.resolver.get_media_url(event, "image", is_template=True)
        if require_at and not target_url:
            await event.send(event.plain_result("⚠️ 此指令需要 @ 一个用户作为互动对象！"))
            return
        if not target_url:
            target_url = f"http://q.qlogo.cn/headimg_dl?dst_uin={event.message_obj.sender.user_id}&spec=640"
        
        input_target = os.path.join(self.temp_dir, f"target_{uuid.uuid4().hex[:6]}.png")
        input_self = None
        if require_at:
            input_self = os.path.join(self.temp_dir, f"self_{uuid.uuid4().hex[:6]}.png")
            self_url = f"http://q.qlogo.cn/headimg_dl?dst_uin={event.message_obj.sender.user_id}&spec=640"
            await self.resolver.download_media(self_url, input_self, event)
        
        out_path = os.path.join(self.temp_dir, f"tpl_{uuid.uuid4().hex[:6]}.webp")
        try:
            await self.resolver.download_media(target_url, input_target, event)
            await asyncio.to_thread(self._render_template, input_target, input_self, out_path, template_name)
            await self.resolver.respond_result(event, out_path)
        except Exception as e:
            await event.send(event.plain_result(f"❌ 表情包生成失败: {str(e)}"))
        finally:
            if os.path.exists(input_target): os.remove(input_target)
            if input_self and os.path.exists(input_self): os.remove(input_self)

    def _render_template(self, target_p, self_p, out_p, mode):
        target_img = PILImage.open(target_p).convert('RGBA')
        self_img = PILImage.open(self_p).convert('RGBA') if self_p else None
        
        frames = []
        durations = []
        
        if mode == "petpet":
            hand = PILImage.open(os.path.join(self.resource_dir, "petpet_hand.png")).convert('RGBA')
            specs = [(112,112,0,0), (114,100,0,12), (116,85,0,27), (114,95,0,17), (112,112,0,0)]
            for i, (w, h, dx, dy) in enumerate(specs):
                canvas = PILImage.new("RGBA", (112, 112), (255, 255, 255, 0))
                resized = target_img.resize((w, h), PILImage.Resampling.LANCZOS)
                canvas.paste(resized, (dx, dy), resized)
                hand_frame = hand.crop((i * 112, 0, (i + 1) * 112, 112))
                canvas.paste(hand_frame, (0, 0), hand_frame)
                frames.append(canvas)
                durations.append(40)
        
        elif mode in ["shoot", "behead", "do", "lash"]:
            frame_dir = os.path.join(self.resource_dir, f"{mode}_frames")
            if not os.path.isdir(frame_dir):
                raise Exception(f"缺少资源 {mode}_frames 目录")
                
            frame_files = sorted(
                [f for f in os.listdir(frame_dir) if f.lower().endswith('.png')],
                key=self._natural_sort_key
            )
            if not frame_files:
                raise Exception(f"模板 {mode} 内无可用帧素材")
            
            do_locs = [
                {"target": (0, 74, 46, 46), "self": (106, 15, 50, 50)},
                {"target": (0, 82, 46, 40), "self": (106, 11, 50, 54)},
                {"target": (0, 70, 46, 48), "self": (106, 18, 50, 48)}
            ]
            lash_locs = [
                {"self": (15, 30, 48, 48), "target": (110, 55, 48, 48)},
                {"self": (15, 28, 48, 48), "target": (110, 58, 48, 48)},
                {"self": (15, 32, 48, 48), "target": (110, 52, 48, 48)},
                {"self": (15, 30, 48, 48), "target": (110, 55, 48, 48)},
                {"self": (15, 28, 48, 48), "target": (110, 58, 48, 48)},
                {"self": (15, 32, 48, 48), "target": (110, 52, 48, 48)},
                {"self": (15, 30, 48, 48), "target": (110, 55, 48, 48)},
                {"self": (15, 28, 48, 48), "target": (110, 58, 48, 48)},
                {"self": (15, 32, 48, 48), "target": (110, 52, 48, 48)}
            ]
            
            for idx, fname in enumerate(frame_files):
                base = PILImage.open(os.path.join(frame_dir, fname)).convert('RGBA')
                canvas = PILImage.new("RGBA", base.size, (255, 255, 255, 0))
                
                if mode == "do":
                    loc = do_locs[idx % len(do_locs)]
                    t_box = loc["target"]
                    scaled_target = target_img.resize((t_box[2], t_box[3]), PILImage.Resampling.LANCZOS)
                    canvas.paste(scaled_target, (t_box[0], t_box[1]), scaled_target)
                    if self_img:
                        s_box = loc["self"]
                        scaled_self = self_img.resize((s_box[2], s_box[3]), PILImage.Resampling.LANCZOS)
                        canvas.paste(scaled_self, (s_box[0], s_box[1]), scaled_self)
                        
                elif mode == "lash":
                    loc = lash_locs[idx % len(lash_locs)]
                    if self_img:
                        s_box = loc["self"]
                        scaled_self = self_img.resize((s_box[2], s_box[3]), PILImage.Resampling.LANCZOS)
                        canvas.paste(scaled_self, (s_box[0], s_box[1]), scaled_self)
                    t_box = loc["target"]
                    scaled_target = target_img.resize((t_box[2], t_box[3]), PILImage.Resampling.LANCZOS)
                    canvas.paste(scaled_target, (t_box[0], t_box[1]), scaled_target)
                    
                else:  
                    tw, th = int(base.width * 0.4), int(base.height * 0.4)
                    scaled_target = target_img.resize((tw, th), PILImage.Resampling.LANCZOS)
                    tx = (base.width - tw) // 2
                    ty = base.height - th - 20
                    canvas.paste(scaled_target, (tx, ty), scaled_target)
                
                canvas.paste(base, (0, 0), base)
                frames.append(canvas)
                durations.append(60)
        else:
            raise Exception(f"未知模板: {mode}")
        
        MediaResolver.save_webp_safely(out_p, frames, durations, loop=0)