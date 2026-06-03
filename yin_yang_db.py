"""
阴阳库模块 - 独立文件
"""

import json
import os
from datetime import datetime


class YinYangDB:
    def __init__(self):
        self.data_file = "data/yin_yang_db.json"
        self.data = {"yin": {}, "yang": {}}
        self.load_data()
    
    def load_data(self):
        os.makedirs("data", exist_ok=True)
        if os.path.exists(self.data_file):
            try:
                with open(self.data_file, "r", encoding="utf-8") as f:
                    self.data = json.load(f)
                self.data.setdefault("yin", {})
                self.data.setdefault("yang", {})
                print(f"[调试] 阴阳库数据加载成功，阴库{len(self.data['yin'])}条，阳库{len(self.data['yang'])}条")
            except Exception as e:
                print(f"[调试] 阴阳库数据加载失败：{e}")
        else:
            self.save_data()
            print("[调试] 初始化新的阴阳库数据文件")
    
    def save_data(self):
        try:
            with open(self.data_file, "w", encoding="utf-8") as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"[调试] 阴阳库数据保存失败：{e}")
    
    def add_qq(self, qq: str, lib_type: str, remark: str = "无") -> bool:
        qq = qq.strip()
        if not qq.isdigit():
            return False
        
        other_lib = "yang" if lib_type == "yin" else "yin"
        if qq in self.data[other_lib]:
            del self.data[other_lib][qq]
        
        self.data[lib_type][qq] = {
            "remark": remark,
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        self.save_data()
        return True
    
    def del_qq(self, qq: str) -> bool:
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
        qq = qq.strip()
        if qq in self.data["yin"]:
            info = self.data["yin"][qq]
            return f"该QQ属于【阴库】\n备注：{info['remark']}\n添加时间：{info['add_time']}"
        elif qq in self.data["yang"]:
            info = self.data["yang"][qq]
            return f"该QQ属于【阳库】\n备注：{info['remark']}\n添加时间：{info['add_time']}"
        else:
            return "该QQ未加入阴阳库"
    
    def list_qq(self, lib_type: str) -> str:
        if lib_type not in ["yin", "yang"]:
            return "库类型错误，仅支持：阴/阳"
        
        lib_name = "阴库" if lib_type == "yin" else "阳库"
        qq_list = self.data[lib_type]
        if not qq_list:
            return f"{lib_name} 暂无数据"
        
        result = [f"{lib_name} 列表（共{len(qq_list)}条）："]
        for idx, (qq, info) in enumerate(qq_list.items(), 1):
            result.append(f"{idx}. QQ：{qq} | 备注：{info['remark']} | 添加时间：{info['add_time']}")
        return "\n".join(result)
    
    def switch_qq(self, qq: str, target_lib: str) -> str:
        qq = qq.strip()
        if target_lib not in ["yin", "yang"]:
            return "目标库错误，仅支持：阴/阳"
        
        current_lib = None
        if qq in self.data["yin"]:
            current_lib = "yin"
        elif qq in self.data["yang"]:
            current_lib = "yang"
        else:
            return "该QQ未加入阴阳库，无法切换"
        
        if current_lib == target_lib:
            return f"该QQ已在【{'阴库' if target_lib == 'yin' else '阳库'}】中，无需切换"
        
        remark = self.data[current_lib][qq]["remark"]
        self.add_qq(qq, target_lib, remark)
        return f"已将QQ {qq} 从【{'阴库' if current_lib == 'yin' else '阳库'}】切换到【{'阴库' if target_lib == 'yin' else '阳库'}】"
