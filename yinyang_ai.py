"""
阴阳库模块（NoneBot2 适配版）
修复：移除 NoneBot1 的 CommandSession，改用 NoneBot2 最新接口
功能：管理QQ号的阴阳库分类（阳库=白名单/可信，阴库=黑名单/限制）
指令：
1. 阴阳库添加 <QQ号> <阴/阳> [备注] → 添加QQ到对应库
2. 阴阳库删除 <QQ号> → 从阴阳库移除QQ
3. 阴阳库查询 <QQ号> → 查询QQ所属库
4. 阴阳库列表 <阴/阳> → 查看对应库的所有QQ
5. 阴阳库切换 <QQ号> <阴/阳> → 切换QQ的库分类
"""
import json
import os
from datetime import datetime
from nonebot import on_command, get_bot, logger
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11 import MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.params import CommandArg
from nonebot.adapters.onebot.v11.message import Message

# ==================== 配置项 ====================
# 数据存储文件路径
YIN_YANG_DB_FILE = "data/yin_yang_db.json"
# 管理员QQ列表（和 admins.json 保持一致）
ADMIN_QQ = {"2249528587", "2839325731", "927924546"}

# ==================== 数据初始化 ====================
class YinYangDB:
    """阴阳库核心类（逻辑不变，仅修复导入错误）"""
    def __init__(self):
        # 初始化数据结构：yin=阴库，yang=阳库，每个QQ对应备注+添加时间
        self.data = {
            "yin": {},   # 阴库：{"QQ号": {"remark": "备注", "add_time": "时间"}}
            "yang": {}   # 阳库：{"QQ号": {"remark": "备注", "add_time": "时间"}}
        }
        self.load_data()

    def load_data(self):
        """加载阴阳库数据"""
        os.makedirs("data", exist_ok=True)
        if os.path.exists(YIN_YANG_DB_FILE):
            try:
                with open(YIN_YANG_DB_FILE, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                # 补全缺失的库（防止文件损坏）
                self.data.setdefault("yin", {})
                self.data.setdefault("yang", {})
                logger.info("[阴阳库] 数据加载成功")
            except Exception as e:
                logger.error(f"[阴阳库] 数据加载失败，使用默认值：{e}")
        else:
            self.save_data()
            logger.info("[阴阳库] 初始化新的阴阳库数据文件")

    def save_data(self):
        """保存阴阳库数据"""
        try:
            with open(YIN_YANG_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"[阴阳库] 数据保存失败：{e}")

    def add_qq(self, qq: str, lib_type: str, remark: str = "无") -> bool:
        """添加QQ到指定库（yin/yang）"""
        qq = qq.strip()
        if not qq.isdigit():
            return False
        
        # 先从另一个库移除（避免重复）
        other_lib = "yang" if lib_type == "yin" else "yin"
        if qq in self.data[other_lib]:
            del self.data[other_lib][qq]
        
        # 添加到目标库
        self.data[lib_type][qq] = {
            "remark": remark,
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_data()
        return True

    def del_qq(self, qq: str) -> bool:
        """从阴阳库移除QQ"""
        qq = qq.strip()
        if qq in self.data["yin"]:
            del self.data["yin"][qq]
            self.save_data()
            return True
        elif qq in self.data["yang"]:
            del self.data["yang"][qq]
            self.save_data()
            return True
        return False

    def query_qq(self, qq: str) -> str:
        """查询QQ所属库"""
        qq = qq.strip()
        if qq in self.data["yin"]:
            info = self.data["yin"][qq]
            return f"❌ 该QQ属于【阴库】\n备注：{info['remark']}\n添加时间：{info['add_time']}"
        elif qq in self.data["yang"]:
            info = self.data["yang"][qq]
            return f"✅ 该QQ属于【阳库】\n备注：{info['remark']}\n添加时间：{info['add_time']}"
        else:
            return "❓ 该QQ未加入阴阳库"

    def list_qq(self, lib_type: str) -> str:
        """查看指定库的所有QQ"""
        if lib_type not in ["yin", "yang"]:
            return "❌ 库类型错误，仅支持：阴/阳"
        
        lib_name = "阴库" if lib_type == "yin" else "阳库"
        qq_list = self.data[lib_type]
        if not qq_list:
            return f"📄 {lib_name} 暂无数据"
        
        # 拼接列表
        result = [f"📄 {lib_name} 列表（共{len(qq_list)}条）："]
        for idx, (qq, info) in enumerate(qq_list.items(), 1):
            result.append(f"{idx}. QQ：{qq} | 备注：{info['remark']} | 添加时间：{info['add_time']}")
        return "\n".join(result)

    def switch_qq(self, qq: str, target_lib: str) -> str:
        """切换QQ的库分类"""
        qq = qq.strip()
        if target_lib not in ["yin", "yang"]:
            return "❌ 目标库错误，仅支持：阴/阳"
        
        # 检查当前所属库
        current_lib = None
        if qq in self.data["yin"]:
            current_lib = "yin"
        elif qq in self.data["yang"]:
            current_lib = "yang"
        else:
            return "❌ 该QQ未加入阴阳库，无法切换"
        
        if current_lib == target_lib:
            return f"❌ 该QQ已在【{'阴库' if target_lib == 'yin' else '阳库'}】中，无需切换"
        
        # 切换（复用添加逻辑）
        remark = self.data[current_lib][qq]["remark"]
        self.add_qq(qq, target_lib, remark)
        return f"✅ 已将QQ {qq} 从【{'阴库' if current_lib == 'yin' else '阳库'}】切换到【{'阴库' if target_lib == 'yin' else '阳库'}】"

# 初始化阴阳库实例
yin_yang_db = YinYangDB()

# ==================== 权限校验（NoneBot2 版） ====================
async def check_admin(event: MessageEvent) -> bool:
    """权限校验：仅管理员可使用阴阳库指令"""
    user_id = str(event.user_id)
    # 超级用户（NoneBot2 配置的 SUPERUSER）或指定管理员QQ
    return user_id in ADMIN_QQ or user_id in SUPERUSER

# ==================== 指令注册（NoneBot2 最新接口） ====================
# 1. 阴阳库添加指令
yin_yang_add = on_command(
    "阴阳库添加",
    aliases={"添加阴阳库"},
    permission=check_admin,
    block=True,
    priority=10
)

@yin_yang_add.handle()
async def handle_yin_yang_add(event: MessageEvent, args: Message = CommandArg()):
    """处理阴阳库添加指令"""
    arg_text = args.extract_plain_text().strip()
    arg_list = arg_text.split()
    
    if len(arg_list) < 2:
        await yin_yang_add.finish("❌ 指令格式错误！\n正确格式：阴阳库添加 <QQ号> <阴/阳> [备注]\n示例：阴阳库添加 123456789 阳 可信用户")
    
    qq = arg_list[0]
    lib_type = arg_list[1].lower()
    remark = " ".join(arg_list[2:]) if len(arg_list) > 2 else "无"
    
    # 校验库类型
    if lib_type not in ["阴", "阳"]:
        await yin_yang_add.finish("❌ 库类型错误！仅支持：阴/阳")
    
    # 转换为内部标识
    lib_type = "yin" if lib_type == "阴" else "yang"
    success = yin_yang_db.add_qq(qq, lib_type, remark)
    
    if success:
        await yin_yang_add.finish(f"✅ 已将QQ {qq} 添加到【{'阴库' if lib_type == 'yin' else '阳库'}】\n备注：{remark}")
    else:
        await yin_yang_add.finish("❌ 添加失败！请检查QQ号是否为纯数字")

# 2. 阴阳库删除指令
yin_yang_del = on_command(
    "阴阳库删除",
    aliases={"删除阴阳库"},
    permission=check_admin,
    block=True,
    priority=10
)

@yin_yang_del.handle()
async def handle_yin_yang_del(event: MessageEvent, args: Message = CommandArg()):
    qq = args.extract_plain_text().strip()
    if not qq:
        await yin_yang_del.finish("❌ 指令格式错误！\n正确格式：阴阳库删除 <QQ号>\n示例：阴阳库删除 123456789")
    
    success = yin_yang_db.del_qq(qq)
    if success:
        await yin_yang_del.finish(f"✅ 已从阴阳库移除QQ {qq}")
    else:
        await yin_yang_del.finish(f"❌ 删除失败！QQ {qq} 未加入阴阳库")

# 3. 阴阳库查询指令
yin_yang_query = on_command(
    "阴阳库查询",
    aliases={"查询阴阳库"},
    permission=check_admin,
    block=True,
    priority=10
)

@yin_yang_query.handle()
async def handle_yin_yang_query(event: MessageEvent, args: Message = CommandArg()):
    qq = args.extract_plain_text().strip()
    if not qq:
        await yin_yang_query.finish("❌ 指令格式错误！\n正确格式：阴阳库查询 <QQ号>\n示例：阴阳库查询 123456789")
    
    result = yin_yang_db.query_qq(qq)
    await yin_yang_query.finish(result)

# 4. 阴阳库列表指令
yin_yang_list = on_command(
    "阴阳库列表",
    aliases={"阴阳库查看"},
    permission=check_admin,
    block=True,
    priority=10
)

@yin_yang_list.handle()
async def handle_yin_yang_list(event: MessageEvent, args: Message = CommandArg()):
    lib_type = args.extract_plain_text().strip().lower()
    if not lib_type or lib_type not in ["阴", "阳"]:
        await yin_yang_list.finish("❌ 指令格式错误！\n正确格式：阴阳库列表 <阴/阳>\n示例：阴阳库列表 阳")
    
    lib_type = "yin" if lib_type == "阴" else "yang"
    result = yin_yang_db.list_qq(lib_type)
    await yin_yang_list.finish(result)

# 5. 阴阳库切换指令
yin_yang_switch = on_command(
    "阴阳库切换",
    aliases={"切换阴阳库"},
    permission=check_admin,
    block=True,
    priority=10
)

@yin_yang_switch.handle()
async def handle_yin_yang_switch(event: MessageEvent, args: Message = CommandArg()):
    arg_text = args.extract_plain_text().strip()
    arg_list = arg_text.split()
    
    if len(arg_list) < 2:
        await yin_yang_switch.finish("❌ 指令格式错误！\n正确格式：阴阳库切换 <QQ号> <阴/阳>\n示例：阴阳库切换 123456789 阴")
    
    qq = arg_list[0]
    target_lib = arg_list[1].lower()
    if target_lib not in ["阴", "阳"]:
        await yin_yang_switch.finish("❌ 目标库错误！仅支持：阴/阳")
    
    target_lib = "yin" if target_lib == "阴" else "yang"
    result = yin_yang_db.switch_qq(qq, target_lib)
    await yin_yang_switch.finish(result)

# ==================== 模块加载提示 ====================
logger.info("[阴阳库模块] NoneBot2 适配版加载完成！")
logger.info("✅ 可用指令：阴阳库添加/删除/查询/列表/切换")
