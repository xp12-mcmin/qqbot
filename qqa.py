# lightweight_vision_assistant.py - 专为2GB显存优化
import os
import sys
import time
import torch
from PIL import Image
import pyautogui
import pyperclip
from pynput import keyboard

print("="*60)
print("🤖 AI QQ助手 - 2GB显存优化版")
print("="*60)

class LightweightVisionAssistant:
    def __init__(self):
        # 配置
        self.hotkey = '<ctrl>+<alt>+v'  # V for Vision
        self.model = None
        self.processor = None
        self.screenshot_dir = "screenshots"
        self.use_gpu = False  # 先默认CPU，后面检测
        
        os.makedirs(self.screenshot_dir, exist_ok=True)
        
        # 检测硬件
        self.detect_hardware()
    
    def detect_hardware(self):
        """检测硬件并选择最优方案"""
        print("🔍 检测硬件配置...")
        
        self.has_nvidia = torch.cuda.is_available()
        if self.has_nvidia:
            # 获取显存信息
            free_memory = torch.cuda.get_device_properties(0).total_memory / 1024**3
            print(f"✅ NVIDIA显卡: {torch.cuda.get_device_name(0)}")
            print(f"✅ 总显存: {free_memory:.1f}GB")
            
            # GTX 1050只有2GB显存，需要特殊处理
            if free_memory <= 2.5:  # 2GB显存
                print("⚠️  检测到低显存显卡(2GB)，使用优化模式")
                self.use_gpu = True
                self.low_vram_mode = True
                self.model_choice = "blip2-tiny"  # 选择最小模型
            else:
                self.use_gpu = True
                self.low_vram_mode = False
                self.model_choice = "blip2-base"
        else:
            print("⚠️  未检测到NVIDIA显卡，使用CPU模式")
            self.use_gpu = False
            self.model_choice = "blip2-tiny"
        
        print(f"🎯 选择模型: {self.model_choice}")
        print(f"🔧 运行模式: {'GPU优化' if self.use_gpu else 'CPU'}")
    
    def load_model_blip2_tiny(self):
        """加载BLIP-2最小版本"""
        try:
            from transformers import Blip2Processor, Blip2ForConditionalGeneration
            
            print("🤖 加载 BLIP-2-Opt-2.7B (最小版本)...")
            
            # 配置加载参数
            kwargs = {
                "torch_dtype": torch.float16 if self.use_gpu else torch.float32,
            }
            
            if self.use_gpu:
                if self.low_vram_mode:
                    # 2GB显存特殊优化
                    kwargs["device_map"] = "auto"
                    kwargs["load_in_8bit"] = True  # 8bit量化
                    kwargs["low_cpu_mem_usage"] = True
                else:
                    kwargs["device_map"] = "auto"
            else:
                kwargs["device_map"] = None
                kwargs["low_cpu_mem_usage"] = True
            
            # 加载处理器和模型
            self.processor = Blip2Processor.from_pretrained(
                "Salesforce/blip2-opt-2.7b"
            )
            
            self.model = Blip2ForConditionalGeneration.from_pretrained(
                "Salesforce/blip2-opt-2.7b",
                **kwargs
            )
            
            # 如果是CPU模式，移动到CPU
            if not self.use_gpu:
                self.model = self.model.to("cpu")
            
            print("✅ BLIP-2模型加载成功！")
            return True
            
        except Exception as e:
            print(f"❌ BLIP-2加载失败: {e}")
            return False
    
    def load_model_qwen_cpu(self):
        """备选方案：Qwen-VL CPU版本"""
        try:
            print("🤖 加载 Qwen-VL-Chat (CPU版本)...")
            
            from transformers import AutoModelForCausalLM, AutoTokenizer
            
            self.processor = AutoTokenizer.from_pretrained(
                "Qwen/Qwen-VL-Chat",
                trust_remote_code=True
            )
            
            self.model = AutoModelForCausalLM.from_pretrained(
                "Qwen/Qwen-VL-Chat",
                device_map="cpu",
                trust_remote_code=True,
                torch_dtype=torch.float32
            )
            
            print("✅ Qwen-VL-Chat加载成功！")
            return True
            
        except Exception as e:
            print(f"❌ Qwen-VL加载失败: {e}")
            return False
    
    def load_model(self):
        """智能加载模型"""
        print("\n📥 正在加载视觉AI模型...")
        
        # 根据选择加载模型
        if self.model_choice == "blip2-tiny":
            success = self.load_model_blip2_tiny()
            if not success:
                print("尝试备选方案...")
                success = self.load_model_qwen_cpu()
        else:
            success = self.load_model_blip2_base()
        
        if success:
            print("🎉 模型加载完成，系统就绪！")
            return True
        else:
            print("❌ 所有模型加载失败，使用文本模式")
            return False
    
    def capture_screen(self):
        """截图"""
        try:
            from PIL import ImageGrab
            
            print("📸 截取屏幕中...")
            screenshot = ImageGrab.grab()
            
            # 保存截图（可选）
            timestamp = time.strftime("%H%M%S")
            filename = f"{self.screenshot_dir}/capture_{timestamp}.jpg"
            
            # 压缩图片以节省内存
            screenshot.save(filename, "JPEG", quality=85, optimize=True)
            print(f"✅ 截图保存: {filename}")
            
            return screenshot
            
        except Exception as e:
            print(f"❌ 截图失败: {e}")
            return None
    
    def analyze_image_lightweight(self, image):
        """轻量级图像分析（为2GB显存优化）"""
        if self.model is None:
            return "请先加载AI模型。"
        
        try:
            print("🔍 AI正在分析图片...")
            start_time = time.time()
            
            # 进一步压缩图片尺寸，减少内存占用
            max_size = 512  # 限制图片大小
            if max(image.size) > max_size:
                ratio = max_size / max(image.size)
                new_size = (int(image.size[0] * ratio), int(image.size[1] * ratio))
                image = image.resize(new_size, Image.Resampling.LANCZOS)
                print(f"  图片压缩: {image.size}")
            
            # BLIP-2处理流程
            if hasattr(self.processor, '__class__') and 'Blip2Processor' in str(self.processor.__class__):
                # BLIP-2处理
                inputs = self.processor(
                    images=image,
                    text="请描述这张图片中的聊天内容，给出简要回复建议",
                    return_tensors="pt"
                )
                
                # 内存优化：移动到对应设备
                if self.use_gpu:
                    inputs = {k: v.cuda() for k, v in inputs.items()}
                
                # 生成回复（限制长度）
                with torch.no_grad():
                    output_ids = self.model.generate(
                        **inputs,
                        max_new_tokens=80,  # 限制token数量
                        min_length=20,
                        do_sample=False,  # 贪婪解码，节省计算
                        temperature=0.7,
                    )
                
                # 解码
                response = self.processor.decode(output_ids[0], skip_special_tokens=True)
                
                # 提取有效部分
                if "建议" in response:
                    response = response.split("建议")[-1].strip()
                
            else:
                # Qwen-VL处理
                query = "请简要描述这张聊天截图的内容"
                response, _ = self.model.chat(self.processor, query=query, image=image)
            
            elapsed = time.time() - start_time
            print(f"✅ 分析完成，耗时: {elapsed:.1f}秒")
            print(f"📝 分析结果: {response[:60]}...")
            
            return response
            
        except torch.cuda.OutOfMemoryError:
            print("❌ 显存不足！清理缓存重试...")
            torch.cuda.empty_cache()
            return "显存不足，分析失败。"
            
        except Exception as e:
            print(f"❌ 分析失败: {str(e)[:100]}")
            return f"分析失败: {str(e)[:50]}"
    
    def generate_smart_reply(self, analysis):
        """根据分析生成智能回复"""
        # 提取关键信息生成回复
        reply_templates = [
            "根据聊天内容，{analysis}",
            "明白了，{analysis}",
            "好的，{analysis}",
            "{analysis}，请知悉。",
            "收到，{analysis}"
        ]
        
        import random
        template = random.choice(reply_templates)
        
        # 简化分析文本
        short_analysis = analysis[:30] + "..." if len(analysis) > 30 else analysis
        
        # 生成回复
        reply = template.format(analysis=short_analysis)
        
        # 确保回复长度合适
        if len(reply) > 100:
            reply = reply[:97] + "..."
        
        return reply
    
    def send_qq_message(self, text):
        """发送QQ消息"""
        try:
            print(f"📤 准备发送: {text}")
            
            # 复制到剪贴板
            pyperclip.copy(text)
            time.sleep(0.15)
            
            # 粘贴
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(0.1)
            
            # 发送
            pyautogui.press('enter')
            
            print("✅ 消息已发送！")
            return True
            
        except Exception as e:
            print(f"❌ 发送失败: {e}")
            return False
    
    def on_hotkey(self):
        """热键触发流程"""
        print("\n" + "="*50)
        print("🎯 AI助手启动！")
        
        # 1. 截图
        screenshot = self.capture_screen()
        if not screenshot:
            print("❌ 截图失败，终止")
            return
        
        # 2. AI分析
        analysis = self.analyze_image_lightweight(screenshot)
        
        # 3. 生成回复
        reply = self.generate_smart_reply(analysis)
        
        # 4. 发送
        self.send_qq_message(reply)
        
        print("="*50)
        print("✨ 流程完成！")
    
    def start(self):
        """启动助手"""
        print(f"\n🎮 热键: {self.hotkey}")
        print("💡 切换到QQ窗口，按热键使用")
        print("🛑 按ESC键退出")
        print("-"*50)
        
        # 加载模型（可能会下载）
        print("正在初始化AI模型...")
        model_loaded = self.load_model()
        
        if not model_loaded:
            print("⚠️  AI模型未加载，使用文本模式")
            print("💡 后续按热键会使用预设回复")
        
        # 热键监听
        def on_activate():
            self.on_hotkey()
        
        def on_exit():
            print("\n👋 退出AI助手")
            return False
        
        with keyboard.GlobalHotKeys({
            self.hotkey: on_activate,
            '<esc>': on_exit
        }) as h:
            h.join()

# 运行
if __name__ == "__main__":
    try:
        assistant = LightweightVisionAssistant()
        assistant.start()
    except KeyboardInterrupt:
        print("\n👋 用户中断")
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        input("\n按回车退出...")
