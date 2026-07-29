import os
import uuid
import base64
import shutil
import asyncio
import aiohttp
import urllib.parse
from PIL import Image as PILImage, ImageFont
from astrbot.api.event import AstrMessageEvent
from astrbot.api.message_components import Image as AstrImage

class MediaResolver:
    def __init__(self, config: dict, context):
        self.config = config
        self.context = context

    async def get_media_url(self, event: AstrMessageEvent, type_req="image", is_template=False):
        def extract_path(comp):
            return getattr(comp, "url", None) or getattr(comp, "file_id", None) or getattr(comp, "path", None) or getattr(comp, "file", None)
            
        allowed_classes = [type_req.capitalize(), "File"]
        allowed_types = [type_req, "file", "flash"] if type_req == "image" else [type_req, "file"]

        if hasattr(event.message_obj, 'message_chain'):
            for comp in event.message_obj.message_chain:
                if comp.__class__.__name__ in allowed_classes or getattr(comp, "type", "") in allowed_types:
                    res = extract_path(comp)
                    if res:
                        return res
                    
        if hasattr(event.message_obj, 'message'):
            for comp in event.message_obj.message:
                if comp.__class__.__name__ in allowed_classes or getattr(comp, "type", "") in allowed_types:
                    res = extract_path(comp)
                    if res:
                        return res

        quoted = getattr(event, 'quoted', None)
        if not quoted and hasattr(event, 'message_obj'):
            for comp in getattr(event.message_obj, 'message', []):
                if comp.__class__.__name__ == "Reply" or getattr(comp, "type", "") == "reply":
                    if event.get_platform_name() == "aiocqhttp" and hasattr(event, 'bot'):
                        try:
                            msg_id = getattr(comp, 'id', None) or getattr(comp, 'message_id', None)
                            if msg_id:
                                res = await event.bot.api.call_action('get_msg', message_id=int(msg_id))
                                msg_list = res.get('message', [])
                                for m in msg_list:
                                    if m.get('type') in allowed_types:
                                        data = m.get('data', {})
                                        return data.get('url') or data.get('file_id') or data.get('file')
                        except:
                            pass
                    break

        if quoted:
            chain = getattr(quoted, 'message_chain', None) or getattr(getattr(quoted, 'message_obj', None), 'message_chain', None)
            if chain:
                for comp in chain:
                    if comp.__class__.__name__ in allowed_classes or getattr(comp, "type", "") in allowed_types:
                        res = extract_path(comp)
                        if res:
                            return res
            
            raw_msg = getattr(quoted, 'message', None)
            if raw_msg:
                for m in raw_msg:
                    if isinstance(m, dict) and m.get('type') in allowed_types:
                        data = m.get('data', {})
                        return data.get('url') or data.get('file_id') or data.get('file')

        if is_template and type_req == "image" and self.config.get("enable_at_avatar", True):
            for chain_name in ['message_chain', 'message']:
                if hasattr(event.message_obj, chain_name):
                    for comp in getattr(event.message_obj, chain_name):
                        if comp.__class__.__name__ == "At" or getattr(comp, "type", "") == "at":
                            target_qq = getattr(comp, "qq", None) or getattr(comp, "id", None)
                            if target_qq:
                                return f"http://q.qlogo.cn/headimg_dl?dst_uin={target_qq}&spec=640"
        return None

    async def download_media(self, url: str, target_path: str, event: AstrMessageEvent):
        if not url:
            raise Exception("媒体地址/标识为空")
            
        url = str(url).strip()

        if url.startswith("http://") or url.startswith("https://"):
            async with aiohttp.ClientSession() as sess:
                async with sess.get(url) as r:
                    if r.status != 200:
                        raise Exception(f"HTTP状态码异常: {r.status}")
                    with open(target_path, 'wb') as f:
                        f.write(await r.read())
            return

        if url.startswith("file://"):
            local_path = urllib.parse.unquote(url[7:])
            if os.name == 'nt' and local_path.startswith("/"):
                local_path = local_path[1:] 
            if os.path.exists(local_path):
                shutil.copy(local_path, target_path)
                return
            else:
                raise Exception(f"找不到本地文件: {local_path}")

        if url.startswith("base64://"):
            with open(target_path, 'wb') as f:
                f.write(base64.b64decode(url[9:]))
            return

        unquoted = urllib.parse.unquote(url)
        if os.path.exists(unquoted):
            shutil.copy(unquoted, target_path)
            return
        if os.path.exists(url):
            shutil.copy(url, target_path)
            return

        if event.get_platform_name() == "aiocqhttp":
            try:
                res = await event.bot.api.call_action('get_file', file_id=unquoted)
                if res:
                    real_url = res.get('url') or res.get('file')
                    if real_url and str(real_url) != str(url) and str(real_url) != unquoted:
                        await self.download_media(real_url, target_path, event)
                        return
            except:
                pass
            
            group_id = getattr(event.message_obj, 'group_id', None)
            if group_id:
                try:
                    res = await event.bot.api.call_action('get_group_file_url', group_id=int(group_id), file_id=unquoted)
                    if res:
                        real_url = res.get('url')
                        if real_url and str(real_url) != str(url) and str(real_url) != unquoted:
                            await self.download_media(real_url, target_path, event)
                            return
                except:
                    pass
            
            try:
                res = await event.bot.api.call_action('get_image', file=unquoted)
                if res:
                    real_url = res.get('url') or res.get('file')
                    if real_url and str(real_url) != str(url) and str(real_url) != unquoted:
                        await self.download_media(real_url, target_path, event)
                        return
            except:
                pass

        raise Exception(f"群文件解析失败，标识: {unquoted[:40]}...")

    @staticmethod
    def get_font(font_path: str, font_size: int):
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, font_size)
            except:
                pass
        search_paths = ["/usr/share/fonts", "/usr/local/share/fonts", "."]
        for s_path in search_paths:
            if os.path.exists(s_path):
                for root, dirs, files in os.walk(s_path):
                    for file in files:
                        if file.endswith((".ttc", ".ttf")):
                            f_lower = file.lower()
                            if "zenhei" in f_lower or "wqy" in f_lower or "heiti" in f_lower or "simhei" in f_lower or "noto" in f_lower or "cjk" in f_lower:
                                try:
                                    return ImageFont.truetype(os.path.join(root, file), font_size)
                                except:
                                    continue
        return ImageFont.load_default()

    @staticmethod
    def save_webp_safely(out_filename: str, frames, durations, loop=0):
        """将帧序列以高画质 WebP 格式无损保存"""
        out_frames = [f.convert('RGBA') for f in frames]
            
        if len(out_frames) > 1:
            out_frames[0].save(
                out_filename, format='WEBP', save_all=True, append_images=out_frames[1:],
                duration=durations, loop=loop, quality=95, method=6
            )
        elif len(out_frames) == 1:
            out_frames[0].save(
                out_filename, format='WEBP', quality=95, method=6
            )

    # 保持兼容别名
    save_gif_safely = save_webp_safely

    async def respond_result(self, event: AstrMessageEvent, file_path: str):
        if self.config.get("send_mode") == "作为文件发送":
            with open(file_path, "rb") as f:
                b64 = base64.b64encode(f.read()).decode()
            file_name = f"meme_{uuid.uuid4().hex[:6]}.webp"
            target = event.message_obj.group_id or event.message_obj.sender.user_id
            action = 'send_group_msg' if event.message_obj.group_id else 'send_private_msg'
            payload = {"file": f"base64://{b64}", "name": file_name}
            await event.bot.api.call_action(action, group_id=int(target) if event.message_obj.group_id else None, user_id=int(target) if not event.message_obj.group_id else None, message=[{"type": "file", "data": payload}])
        else:
            await event.send(event.chain_result([AstrImage.fromFileSystem(file_path)]))

        async def delayed_remove(p):
            await asyncio.sleep(20)
            if os.path.exists(p):
                os.remove(p)
        asyncio.create_task(delayed_remove(file_path))