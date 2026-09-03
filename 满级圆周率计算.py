from mpmath import mp
import time
import psutil

def check_memory():
    """检查内存使用情况"""
    mem = psutil.virtual_memory()
    print(f"总内存: {mem.total / (1024**3):.1f} GB")
    print(f"可用内存: {mem.available / (1024**3):.1f} GB")
    return mem.available / (1024**3)

def calc_pi_1亿位():
    """专门为16GB内存优化的1亿位圆周率计算"""
    
    # 设置精度（1亿位 + 安全余量）
    digits = 100000000
    mp.dps = digits + 50
    
    print("=" * 60)
    print("🚀 开始计算 1亿位 圆周率")
    print("=" * 60)
    
    # 检查内存
    available_gb = check_memory()
    if available_gb < 4:
        print("⚠️ 可用内存不足4GB，建议关闭其他程序")
        return
    
    print(f"\n⏱️ 预计耗时: 20-40 分钟")
    print("📊 文件大小: ~100 MB")
    print("💾 内存占用: ~1.5-2 GB")
    print("\n开始计算...")
    
    start = time.time()
    
    # 计算
    pi = mp.pi
    calc_time = time.time() - start
    print(f"✅ 计算完成！耗时 {calc_time/60:.2f} 分钟")
    
    # 转换为字符串（最耗内存的步骤）
    print("🔄 正在转换为字符串...")
    start_str = time.time()
    pi_str = str(pi)
    str_time = time.time() - start_str
    print(f"✅ 转换完成！耗时 {str_time:.2f} 秒")
    
    # 分批保存（避免一次性写入卡死）
    print("💾 正在保存文件...")
    chunk_size = 10000000  # 每次保存1000万位
    total_digits = len(pi_str) - 2  # 减去 "3."
    
    with open("pi_1亿位.txt", "w", encoding="utf-8") as f:
        # 先写入整数部分
        f.write("3.\n")
        
        # 分批写入小数部分
        decimal_part = pi_str[2:]  # 去掉 "3."
        
        for i in range(0, len(decimal_part), chunk_size):
            chunk = decimal_part[i:i+chunk_size]
            f.write(chunk)
            f.write("\n")  # 每1000万位换行
            progress = (i + chunk_size) / len(decimal_part) * 100
            if progress <= 100:
                print(f"  进度: {progress:.1f}% ({i+chunk_size:,} 位)")
    
    total_time = time.time() - start
    print("=" * 60)
    print(f"🎉 全部完成！总耗时: {total_time/60:.2f} 分钟")
    print(f"📁 文件: pi_1亿位.txt ({(total_digits/1024/1024):.1f} MB)")
    print(f"📊 位数: {total_digits:,}")
    print("=" * 60)

# 运行
if __name__ == "__main__":
    calc_pi_1亿位()
