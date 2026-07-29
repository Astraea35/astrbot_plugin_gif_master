import os
import asyncio
from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register

from .meme.utils import MediaResolver
from .meme.magic import MagicProcessor
from .meme.symmetry import SymmetryProcessor
from .meme.ffmpeg_convert import FfmpegConverter
from .meme.nested import NestedProcessor
from .meme.templates import TemplateProcessor

@register("gif_master", "AI_Meme_Master", "GIF全能魔术工具箱 (明确指令版)", "3.1.2", "移除模糊的翻转指令，全量规范为明确的上下/左右翻转")
class GifMasterPlugin(Star):
    def __init__(self, context: Context, config: dict = None):
        super().__init__(context)
        self.config = config or self.context.get_plugin_config() or {}
        self.resolver = MediaResolver(self.config, self.context)
        
        self.temp_dir = os.path.join("data", "gif_master")
        os.makedirs(self.temp_dir, exist_ok=True)
        
        self.magic_proc = MagicProcessor(self.temp_dir, self.config, self.resolver)
        self.symmetry_proc = SymmetryProcessor(self.temp_dir, self.config, self.resolver)
        self.ffmpeg_proc = FfmpegConverter(self.temp_dir, self.config, self.resolver)
        self.nested_proc = NestedProcessor(self.temp_dir, self.config, self.resolver)
        self.template_proc = TemplateProcessor(self.temp_dir, self.config, self.resolver)

    # ====== 1. 变换类指令（精简模糊指令，全面明确方向） ======
    @filter.command("gif倒放")
    async def cmd_reverse_l(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "reverse")
    @filter.command("GIF倒放")
    async def cmd_reverse_u(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "reverse")

    @filter.command("gif回弹")
    async def cmd_rebound_l(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "rebound")
    @filter.command("GIF回弹")
    async def cmd_rebound_u(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "rebound")

    # 【核心修改】明确为左右水平翻转，删去含糊的 "gif翻转"
    @filter.command("gif左右翻转")
    async def cmd_flip_h_l(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "flip_h")
    @filter.command("GIF左右翻转")
    async def cmd_flip_h_u(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "flip_h")
    @filter.command("左右翻转")
    async def cmd_flip_h_d(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "flip_h")

    # 明确为上下垂直翻转
    @filter.command("gif上下翻转")
    async def cmd_flip_v_l(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "flip_v")
    @filter.command("GIF上下翻转")
    async def cmd_flip_v_u(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "flip_v")
    @filter.command("上下翻转")
    async def cmd_flip_v_d(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "flip_v")

    @filter.command("gif旋转")
    async def cmd_rotate_l(self, event: AstrMessageEvent): await self.magic_proc.rotate(event, "rotate")
    @filter.command("GIF旋转")
    async def cmd_rotate_u(self, event: AstrMessageEvent): await self.magic_proc.rotate(event, "rotate")

    @filter.command("gif反色")
    async def cmd_invert_l(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "invert")
    @filter.command("GIF反色")
    async def cmd_invert_u(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "invert")
    @filter.command("反色")
    async def cmd_invert_d(self, event: AstrMessageEvent): await self.magic_proc.handle_magic(event, "invert")

    @filter.command("gif变速")
    async def cmd_speed_l1(self, event: AstrMessageEvent, multiplier: str = "1.0"): await self.magic_proc.handle_magic(event, "speed", float(multiplier))
    @filter.command("GIF变速")
    async def cmd_speed_u1(self, event: AstrMessageEvent, multiplier: str = "1.0"): await self.magic_proc.handle_magic(event, "speed", float(multiplier))
    @filter.command("gif调速")
    async def cmd_speed_l2(self, event: AstrMessageEvent, multiplier: str = "1.0"): await self.magic_proc.handle_magic(event, "speed", float(multiplier))
    @filter.command("调速")
    async def cmd_speed_d(self, event: AstrMessageEvent, multiplier: str = "1.0"): await self.magic_proc.handle_magic(event, "speed", float(multiplier))

    # ====== 2. 对称类指令 ======
    @filter.command("gif左对称")
    async def cmd_sym_left_l(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "left")
    @filter.command("左对称")
    async def cmd_sym_left_d(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "left")

    @filter.command("gif右对称")
    async def cmd_sym_right_l(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "right")
    @filter.command("右对称")
    async def cmd_sym_right_d(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "right")

    @filter.command("gif上对称")
    async def cmd_sym_top_l(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "top")
    @filter.command("上对称")
    async def cmd_sym_top_d(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "top")

    @filter.command("gif下对称")
    async def cmd_sym_bottom_l(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "bottom")
    @filter.command("下对称")
    async def cmd_sym_bottom_d(self, event: AstrMessageEvent): await self.symmetry_proc.handle_symmetry(event, "bottom")

    # ====== 3. 视频处理与表情模板 ======
    @filter.command("转gif")
    async def cmd_video_to_gif_l(self, event: AstrMessageEvent, args: str = ""): await self.ffmpeg_proc.handle_conversion(event, args)
    @filter.command("转GIF")
    async def cmd_video_to_gif_u(self, event: AstrMessageEvent, args: str = ""): await self.ffmpeg_proc.handle_conversion(event, args)

    @filter.command("makegif")
    async def cmd_make_nested_l(self, event: AstrMessageEvent, text: str = ""): await self.nested_proc.handle_nested(event, text)
    @filter.command("MAKEGIF")
    async def cmd_make_nested_u(self, event: AstrMessageEvent, text: str = ""): await self.nested_proc.handle_nested(event, text)

    @filter.command("摸头")
    async def cmd_petpet(self, event: AstrMessageEvent): await self.template_proc.handle_template(event, "petpet", require_at=False)
    @filter.command("发射")
    async def cmd_shoot(self, event: AstrMessageEvent): await self.template_proc.handle_template(event, "shoot", require_at=False)
    @filter.command("杀")
    async def cmd_behead(self, event: AstrMessageEvent): await self.template_proc.handle_template(event, "behead", require_at=False)
    @filter.command("操你")
    async def cmd_do(self, event: AstrMessageEvent): await self.template_proc.handle_template(event, "do", require_at=True)
    @filter.command("抽你")
    async def cmd_lash(self, event: AstrMessageEvent): await self.template_proc.handle_template(event, "lash", require_at=True)