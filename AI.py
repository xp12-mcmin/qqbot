import pyautogui
import cv2
import numpy as np
import time
import math
import random
from collections import deque
import keyboard
import win32gui
import win32api
import win32con
from dataclasses import dataclass
from typing import Optional, List, Tuple

# ========== 配置 ==========
pyautogui.PAUSE = 0
pyautogui.FAILSAFE = True

@dataclass
class Entity:
    x: int
    y: int
    width: int
    height: int
    hp: int = 100
    distance: float = 0
    entity_id: int = 0

class SimpleCombatBot:
    """简化版战斗AI - 不乱跑版本"""
    
    def __init__(self, game_window_title: str = "迷你世界"):
        self.running = True
        
        # 当前锁定的目标（不会乱切换）
        self.locked_target: Optional[Entity] = None
        self.locked_target_id = None
        self.locked_target_time = 0
        
        # 获取游戏窗口
        self.game_window = self.find_game_window(game_window_title)
        if self.game_window:
            win32gui.SetForegroundWindow(self.game_window)
            time.sleep(0.5)
        
        # 屏幕尺寸
        if self.game_window:
            rect = win32gui.GetWindowRect(self.game_window)
            self.screen_width = rect[2] - rect[0]
            self.screen_height = rect[3] - rect[1]
        else:
            self.screen_width, self.screen_height = pyautogui.size()
        
        self.center_x = self.screen_width // 2
        self.center_y = self.screen_height // 2
        
        # ========== 战斗状态机 ==========
        # combat_state: 'aiming' = 瞄准中, 'attacking' = 攻击中, 'dodging' = 闪避中
        self.combat_state = 'aiming'
        self.state_start_time = time.time()
        
        # ========== 瞄准参数 ==========
        self.aim_speed = 0.35          # 瞄准速度
        self.aim_deadzone = 8          # 死区（像素内认为已瞄准）
        self.aim_complete_time = 0.3   # 瞄准后攻击持续时间
        
        # ========== 走位参数（只在必要时触发）==========
        self.last_move_time = 0
        self.move_cooldown = 1.0       # 1秒才走位一次，不会乱跑
        self.dodge_distance = 40       # 闪避距离
        
        # ========== 识别参数 ==========
        self.red_ranges = [
            ([0, 40, 50], [10, 255, 255]),
            ([160, 40, 50], [180, 255, 255]),
        ]
        
        # 统计
        self.kill_count = 0
        self.frame_count = 0
        self.last_attack_time = 0
        
        # 敌人历史（用于锁定）
        self.enemy_history = {}
        self.next_entity_id = 1
        
        print(f"屏幕: {self.screen_width}x{self.screen_height}")
        print("F12停止 | F11暂停 | 状态: 运行中")
        
    def find_game_window(self, title: str):
        windows = []
        def enum_callback(hwnd, _):
            if title in win32gui.GetWindowText(hwnd):
                windows.append(hwnd)
        win32gui.EnumWindows(enum_callback, None)
        return windows[0] if windows else None
    
    def capture_screen(self) -> np.ndarray:
        """截图"""
        if self.game_window:
            rect = win32gui.GetWindowRect(self.game_window)
            screenshot = pyautogui.screenshot(region=rect)
        else:
            screenshot = pyautogui.screenshot()
        return cv2.cvtColor(np.array(screenshot), cv2.COLOR_RGB2BGR)
    
    def detect_enemies(self, img: np.ndarray) -> List[Entity]:
        """检测敌人（红框）"""
        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)
        combined_mask = np.zeros(img.shape[:2], dtype=np.uint8)
        
        for lower, upper in self.red_ranges:
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
            combined_mask = cv2.bitwise_or(combined_mask, mask)
        
        kernel = np.ones((3, 3), np.uint8)
        combined_mask = cv2.morphologyEx(combined_mask, cv2.MORPH_CLOSE, kernel)
        
        contours, _ = cv2.findContours(combined_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        enemies = []
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            area = w * h
            
            if 400 < area < 40000 and 0.3 < w/h < 2.5:
                # 估算血量
                hp_roi = img[y:y+h, x:x+w]
                hp = self._estimate_hp(hp_roi)
                
                enemy = Entity(
                    x=x + w//2,
                    y=y + h//3,
                    width=w,
                    height=h,
                    hp=hp,
                    distance=self._calc_distance(w, h)
                )
                enemies.append(enemy)
        
        return enemies
    
    def _estimate_hp(self, roi: np.ndarray) -> int:
        """估算血量"""
        if roi.size == 0:
            return 100
        
        h, w = roi.shape[:2]
        if h < 15:
            return 100
        
        hp_roi = roi[5:int(h*0.25), :]
        if hp_roi.size == 0:
            return 100
        
        hsv = cv2.cvtColor(hp_roi, cv2.COLOR_BGR2HSV)
        lower = np.array([0, 80, 100])
        upper = np.array([10, 255, 255])
        mask = cv2.inRange(hsv, lower, upper)
        
        red_ratio = np.count_nonzero(mask) / mask.size if mask.size > 0 else 0
        return int(red_ratio * 100)
    
    def _calc_distance(self, width: int, height: int) -> float:
        """估算距离"""
        if width > 0:
            return 400 / width * 200
        return 500
    
    def lock_best_target(self, enemies: List[Entity]):
        """锁定最佳目标（不频繁切换）"""
        if not enemies:
            self.locked_target = None
            self.locked_target_id = None
            return
        
        # 如果当前有锁定目标且还活着，继续锁定
        if self.locked_target is not None:
            # 检查锁定的目标是否还在
            still_alive = False
            for e in enemies:
                # 通过位置和大小判断是否是同一个目标
                dx = abs(e.x - self.locked_target.x)
                dy = abs(e.y - self.locked_target.y)
                if dx < 100 and dy < 100 and e.hp > 0:
                    # 更新目标信息
                    self.locked_target = e
                    still_alive = True
                    break
            
            if still_alive:
                return
        
        # 锁定新目标：选血量最低的
        alive_enemies = [e for e in enemies if e.hp > 0]
        if alive_enemies:
            # 优先选血量低的
            alive_enemies.sort(key=lambda e: e.hp)
            self.locked_target = alive_enemies[0]
            print(f"\n锁定新目标 HP: {self.locked_target.hp}%")
    
    def aim_at_target(self) -> bool:
        """瞄准目标，返回是否已瞄准"""
        if self.locked_target is None:
            return False
        
        dx = self.locked_target.x - self.center_x
        dy = self.locked_target.y - self.center_y
        distance = math.sqrt(dx**2 + dy**2)
        
        # 已瞄准
        if distance < self.aim_deadzone:
            return True
        
        # 移动鼠标
        move_x = int(dx * self.aim_speed)
        move_y = int(dy * self.aim_speed)
        
        # 限制单次移动
        max_move = 30
        move_x = max(-max_move, min(max_move, move_x))
        move_y = max(-max_move, min(max_move, move_y))
        
        if move_x != 0 or move_y != 0:
            win32api.mouse_event(win32con.MOUSEEVENTF_MOVE, move_x, move_y, 0, 0)
            self.center_x += move_x
            self.center_y += move_y
        
        return False
    
    def should_dodge(self) -> bool:
        """判断是否需要闪避（检测攻击特效）"""
        # 简单检测：屏幕亮度突然变化
        # 这里先返回False，需要再加
        return False
    
    def dodge(self):
        """执行闪避（只移动一点点）"""
        now = time.time()
        if now - self.last_move_time < self.move_cooldown:
            return
        
        # 随机方向闪避
        direction = random.choice([
            ('a', -30), ('d', 30), ('w', 0), ('s', 0)
        ])
        
        # 短按方向键
        pyautogui.keyDown(direction[0])
        time.sleep(0.1)
        pyautogui.keyUp(direction[0])
        
        self.last_move_time = now
        self.combat_state = 'aiming'
        print("闪避!")
    
    def attack(self):
        """攻击"""
        now = time.time()
        if now - self.last_attack_time < 0.15:  # 攻击间隔
            return
        
        pyautogui.click(button='left')
        self.last_attack_time = now
    
    def update_state(self, is_aimed: bool):
        """更新战斗状态机"""
        now = time.time()
        
        if self.combat_state == 'aiming':
            if is_aimed:
                # 瞄准完成，进入攻击状态
                self.combat_state = 'attacking'
                self.state_start_time = now
                print("瞄准完成，开始攻击")
        
        elif self.combat_state == 'attacking':
            # 攻击状态持续一段时间
            if now - self.state_start_time > self.aim_complete_time:
                self.combat_state = 'aiming'
        
        elif self.combat_state == 'dodging':
            if now - self.state_start_time > 0.3:
                self.combat_state = 'aiming'
    
    def main_loop(self):
        """主循环"""
        print("\n战斗AI运行中...")
        print("=" * 40)
        
        paused = False
        last_status_time = time.time()
        
        while self.running:
            # 快捷键
            if keyboard.is_pressed('F12'):
                self.running = False
                break
            
            if keyboard.is_pressed('F11'):
                paused = not paused
                print(f"{'暂停' if paused else '继续'}")
                time.sleep(0.5)
                continue
            
            if paused:
                time.sleep(0.1)
                continue
            
            # 1. 截图并检测敌人
            img = self.capture_screen()
            enemies = self.detect_enemies(img)
            
            # 2. 锁定目标
            self.lock_best_target(enemies)
            
            # 3. 战斗逻辑
            if self.locked_target:
                # 检查目标是否死亡
                if self.locked_target.hp <= 0:
                    self.kill_count += 1
                    print(f"\n击杀! 总击杀: {self.kill_count}")
                    self.locked_target = None
                    self.combat_state = 'aiming'
                else:
                    # 瞄准
                    is_aimed = self.aim_at_target()
                    
                    # 状态机
                    self.update_state(is_aimed)
                    
                    # 根据状态执行动作
                    if self.combat_state == 'attacking':
                        self.attack()
                    
                    # 偶尔检查是否需要闪避
                    if self.should_dodge() and self.combat_state != 'dodging':
                        self.combat_state = 'dodging'
                        self.state_start_time = time.time()
                        self.dodge()
                    
                    # 显示状态
                    now = time.time()
                    if now - last_status_time > 0.5:
                        dx = self.locked_target.x - self.center_x
                        dy = self.locked_target.y - self.center_y
                        error = math.sqrt(dx**2 + dy**2)
                        print(f"\r目标HP: {self.locked_target.hp}% | 瞄准误差: {error:.0f}px | 状态: {self.combat_state} | 击杀: {self.kill_count}", end='')
                        last_status_time = now
            else:
                # 无目标，停止移动
                for k in ['w', 'a', 's', 'd']:
                    pyautogui.keyUp(k)
                
                if self.frame_count % 30 == 0:
                    print(f"\r寻找目标中... 击杀: {self.kill_count}                    ", end='')
            
            # 控制帧率
            time.sleep(0.025)
            self.frame_count += 1
        
        print("\n\nAI已停止")
        # 清理按键
        for k in ['w', 'a', 's', 'd']:
            pyautogui.keyUp(k)
    
    def run(self):
        try:
            self.main_loop()
        except Exception as e:
            print(f"错误: {e}")
        finally:
            print("清理完成")

# ========== 启动 ==========
if __name__ == "__main__":
    print("迷你世界战斗AI - 稳定版")
    print("请以管理员身份运行")
    print("-" * 40)
    
    bot = SimpleCombatBot(game_window_title="迷你世界")
    bot.run()
