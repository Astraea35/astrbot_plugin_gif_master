import asyncio
import os
import re
import uuid

import numpy as np
from PIL import Image as PILImage, ImageDraw, ImageEnhance

from .utils import MediaResolver


class PatinaProcessor:
    """幻影坦克与趣味图像特效，复用 GIF Master 的媒体解析和发送链路。"""

    def __init__(self, temp_dir: str, config: dict, resolver: MediaResolver):
        self.temp_dir = temp_dir
        self.config = config
        self.resolver = resolver

    async def handle(self, event, mode: str):
        handlers = {"camera": self._camera, "prism": self._prism, "pixelate": self._pixelate, "mirage": self._mirage, "raw": self._raw}
        try:
            await handlers[mode](event)
        except Exception as exc:
            await event.send(event.plain_result(f"❌ 图像特效处理失败: {exc}"))

    async def _download_inputs(self, event, count=1, include_at=False):
        urls = await self.resolver.get_media_urls(event, "image", count=count, include_at=include_at)
        paths = []
        try:
            for url in urls:
                path = os.path.join(self.temp_dir, f"patina_in_{uuid.uuid4().hex[:8]}.img")
                await self.resolver.download_media(url, path, event)
                paths.append(path)
        except Exception:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)
            raise
        return paths

    async def _camera(self, event):
        paths = await self._download_inputs(event, 1, include_at=True)
        avatar_path = os.path.join(self.temp_dir, f"patina_avatar_{uuid.uuid4().hex[:8]}.img")
        try:
            if not paths:
                raise ValueError("未捕捉到图片")
            sender_uid = event.message_obj.sender.user_id
            await self.resolver.download_media(f"http://q.qlogo.cn/headimg_dl?dst_uin={sender_uid}&spec=640", avatar_path, event)
            base = PILImage.open(paths[0]).convert("RGB")
            logo = PILImage.open(avatar_path).convert("RGBA")
            w, h = base.size
            bar_h = max(32, int(h * 0.15))
            out = PILImage.new("RGB", (w, h + bar_h), "white")
            out.paste(base, (0, 0))
            draw = ImageDraw.Draw(out)
            font = MediaResolver.get_font(self.config.get("font_path", ""), max(12, int(bar_h * 0.25)))
            device = self.config.get("camera_device_name", "ASTRBOT 14 ULTRA")
            params = "50MP LEICA SUMMILUX 1:1.63-2.5/12-120 ASPH."
            draw.text((int(w * 0.05), h + int(bar_h * 0.25)), device, fill="black", font=font)
            draw.text((w - int(w * 0.45), h + int(bar_h * 0.25)), params, fill="gray", font=font)
            logo_size = max(16, int(bar_h * 0.5))
            logo = logo.resize((logo_size, logo_size), PILImage.Resampling.LANCZOS)
            out.paste(logo, (w // 2 - logo_size // 2, h + int(bar_h * 0.25)), logo)
            out_path = os.path.join(self.temp_dir, f"camera_{uuid.uuid4().hex[:8]}.png")
            out.save(out_path)
            await self.resolver.respond_result(event, out_path)
        finally:
            for path in paths + [avatar_path]:
                if os.path.exists(path):
                    os.remove(path)

    async def _prism(self, event):
        paths = await self._download_inputs(event, 2, include_at=True)
        try:
            if len(paths) < 2:
                raise ValueError("请提供两张图片：第一张为里图，第二张为表图")
            it = int(self.config.get("prism_it", 32)); ct = int(self.config.get("prism_ct", 96))
            ic = float(self.config.get("prism_ic", 50)) / 100.0; cc = float(self.config.get("prism_cc", 50)) / 100.0
            inner = ImageEnhance.Contrast(PILImage.open(paths[0]).convert("L").resize((800, 800))).enhance(ic)
            cover = ImageEnhance.Contrast(PILImage.open(paths[1]).convert("L").resize((800, 800))).enhance(cc)
            i_np, c_np = np.array(inner).astype(float), np.array(cover).astype(float)
            i_proc = (i_np / 255.0) * it; c_proc = (c_np / 255.0) * (255 - ct) + ct
            if self.config.get("prism_reverse", False):
                result = (i_proc + c_proc) / 2
            else:
                checker = (np.indices((800, 800)).sum(axis=0) % 2) == 0
                result = np.where(checker, i_proc, c_proc)
            out_path = os.path.join(self.temp_dir, f"prism_{uuid.uuid4().hex[:8]}.png")
            PILImage.fromarray(np.clip(result, 0, 255).astype(np.uint8)).save(out_path)
            await self.resolver.respond_result(event, out_path)
        finally:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)

    async def _pixelate(self, event):
        paths = await self._download_inputs(event, 1, include_at=True)
        try:
            if not paths:
                raise ValueError("未捕捉到图片")
            amount = int(self.config.get("default_pixel_p", 50))
            match = re.search(r"-p\s+(\d+)", str(event.message_obj.raw_message or ""))
            if match:
                amount = int(match.group(1))
            amount = max(0, min(99, amount))
            img = PILImage.open(paths[0]); w, h = img.size
            scale = max(1, 100 - amount) / 100.0
            out_img = img.resize((max(1, int(w * scale)), max(1, int(h * scale))), PILImage.Resampling.NEAREST).resize((w, h), PILImage.Resampling.NEAREST)
            out_path = os.path.join(self.temp_dir, f"pixelate_{uuid.uuid4().hex[:8]}.png")
            out_img.save(out_path)
            await self.resolver.respond_result(event, out_path)
        finally:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)

    async def _mirage(self, event):
        paths = await self._download_inputs(event, 2, include_at=True)
        try:
            if len(paths) < 2:
                raise ValueError("请提供两张图片：第一张为表图，第二张为里图")
            color = self.config.get("mirage_color_mode", "全彩输出") != "黑白输出"
            weight = max(0.0, min(1.0, float(self.config.get("mirage_blend_weight", 0.7))))
            top = np.array(PILImage.open(paths[0]).convert("RGB").resize((800, 800))).astype(float)
            bottom = np.array(PILImage.open(paths[1]).convert("RGB").resize((800, 800))).astype(float)
            alpha = np.clip(255.0 - (np.mean(top, axis=2) - np.mean(bottom, axis=2) * weight), 1, 255)
            if color:
                pixels = bottom * weight / (alpha[..., None] / 255.0)
                result = np.concatenate([np.clip(pixels, 0, 255), alpha[..., None]], axis=2)
            else:
                pixels = np.mean(bottom, axis=2) * weight / (alpha / 255.0)
                result = np.stack([pixels, pixels, pixels, alpha], axis=2)
            out_path = os.path.join(self.temp_dir, f"mirage_{uuid.uuid4().hex[:8]}.png")
            PILImage.fromarray(np.clip(result, 0, 255).astype(np.uint8)).save(out_path)
            await self.resolver.respond_result(event, out_path)
        finally:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)

    async def _raw(self, event):
        paths = await self._download_inputs(event, 2, include_at=True)
        try:
            if len(paths) < 2:
                raise ValueError("请提供两张图片：第一帧和第二帧")
            frames = [PILImage.open(path).convert("RGB").resize((400, 400)) for path in paths[:2]]
            out_path = os.path.join(self.temp_dir, f"raw_tank_{uuid.uuid4().hex[:8]}.gif")
            frames[0].save(out_path, save_all=True, append_images=[frames[1]], duration=1000, loop=1)
            await self.resolver.respond_result(event, out_path)
        finally:
            for path in paths:
                if os.path.exists(path):
                    os.remove(path)
