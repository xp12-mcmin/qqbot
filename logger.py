"""
彩色日志模块
"""

from colorama import Fore, Back, Style, init
import sys
import traceback

# 初始化 colorama
init(autoreset=True)


class Logger:
    """彩色日志类"""
    
    @staticmethod
    def _print(color: str, tag: str, message: str, end: str = "\n"):
        """内部打印方法"""
        print(f"{color}[{tag}] {message}{Style.RESET_ALL}", end=end)
    
    @staticmethod
    def info(message: str, end: str = "\n"):
        """普通信息 - 白色"""
        print(f"{Fore.WHITE}{message}{Style.RESET_ALL}", end=end)
    
    @staticmethod
    def success(message: str, end: str = "\n"):
        """成功信息 - 绿色"""
        print(f"{Fore.GREEN}✅ {message}{Style.RESET_ALL}", end=end)
    
    @staticmethod
    def error(message: str, end: str = "\n"):
        """错误信息 - 红色"""
        print(f"{Fore.RED}❌ {message}{Style.RESET_ALL}", end=end)
    
    @staticmethod
    def warning(message: str, end: str = "\n"):
        """警告信息 - 黄色"""
        print(f"{Fore.YELLOW}⚠️ {message}{Style.RESET_ALL}", end=end)
    
    @staticmethod
    def command(message: str, end: str = "\n"):
        """命令信息 - 黄色"""
        print(f"{Fore.YELLOW}[命令] {message}{Style.RESET_ALL}", end=end)
    
    @staticmethod
    def debug(message: str, end: str = "\n"):
        """调试信息 - 青色"""
        print(f"{Fore.CYAN}[调试] {message}{Style.RESET_ALL}", end=end)
    
    @staticmethod
    def msg(message: str, end: str = "\n"):
        """消息信息 - 默认色"""
        print(message, end=end)
    
    @staticmethod
    def crash(e: Exception):
        """崩溃信息 - 红色"""
        print(f"\n{Fore.RED}{'='*60}{Style.RESET_ALL}")
        print(f"{Fore.RED}💥 程序崩溃: {e}{Style.RESET_ALL}")
        print(f"{Fore.RED}{traceback.format_exc()}{Style.RESET_ALL}")
        print(f"{Fore.RED}{'='*60}{Style.RESET_ALL}")


# 全局实例
log = Logger()
