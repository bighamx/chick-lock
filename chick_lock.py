# -*- coding: utf-8 -*-
"""
🐤 小鸡乐园 - 全屏锁屏游戏 v3
- 全屏白色, 拦截所有键盘/鼠标事件(不会影响系统)
- 按任意键 / 点击鼠标 → 出现一只小鸡, 到处跑, 走出屏幕消失
- 每只小鸡独一无二: 随机颜色 / 花纹 / 体型 / 配饰 / 大小(含稀有巨型)
- 小鸡随机生蛋, 蛋继承母鸡基因(蛋壳带色), 自动孵出小鸡
- 音效: 生蛋/孵化/行走唧唧声(限频防重叠)
- 家长退出: Ctrl + Alt + Q
"""
import array
import ctypes
import math
import random
import threading
import pygame
from ctypes import wintypes

# ============ 系统级按键屏蔽: Win键 / Alt+Tab / Alt+F4 ============
user32 = ctypes.WinDLL('user32', use_last_error=True)
kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)

WH_KEYBOARD_LL = 13
VK_LWIN, VK_RWIN = 0x5B, 0x5C
VK_TAB, VK_F4, VK_MENU = 0x09, 0x73, 0x12


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [("vkCode", wintypes.DWORD), ("scanCode", wintypes.DWORD),
                ("flags", wintypes.DWORD), ("time", wintypes.DWORD),
                ("dwExtraInfo", ctypes.c_size_t)]


LowLevelKeyboardProc = ctypes.WINFUNCTYPE(
    ctypes.c_long, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)


def _hook_proc(nCode, wParam, lParam):
    if nCode == 0:  # HC_ACTION
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb.vkCode
        if vk in (VK_LWIN, VK_RWIN):
            return 1  # 屏蔽 Win 键
        if vk in (VK_TAB, VK_F4) and (user32.GetAsyncKeyState(VK_MENU) & 0x8000):
            return 1  # 屏蔽 Alt+Tab / Alt+F4
    return user32.CallNextHookEx(None, nCode, wParam, lParam)


_hook_proc_ref = LowLevelKeyboardProc(_hook_proc)


def _hook_loop():
    hhook = user32.SetWindowsHookExW(WH_KEYBOARD_LL, _hook_proc_ref,
                                     kernel32.GetModuleHandleW(None), 0)
    if not hhook:
        return
    msg = wintypes.MSG()
    while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
        user32.TranslateMessage(ctypes.byref(msg))
        user32.DispatchMessageW(ctypes.byref(msg))


threading.Thread(target=_hook_loop, daemon=True).start()

# ============ 游戏配置 ============
FPS = 60
MAX_BIOS = 70           # 生物上限(鸡+蛋, 体积变大后调低)
AUTO_SPAWN_GAP_MS = 6000  # 空屏这么久后自动飘小鸡(屏保)

BG = (255, 255, 255)
DARK = (96, 74, 30)
TEXT_C = (150, 150, 160)
RAINBOW = [(255, 90, 90), (255, 170, 70), (255, 230, 80),
           (120, 220, 120), (90, 180, 255), (190, 140, 255)]

# (身体, 翅膀, 嘴, 腮红)
SCHEMES = [
    ((255, 209, 61), (250, 186, 55), (255, 140, 26), (255, 160, 150)),   # 经典黄
    ((255, 255, 255), (228, 228, 228), (255, 140, 26), (255, 180, 170)),  # 雪白
    ((255, 168, 60), (248, 138, 40), (200, 90, 20), (255, 150, 130)),    # 蜜橘
    ((212, 182, 140), (190, 160, 118), (178, 118, 58), (240, 170, 150)),  # 浅棕
    ((118, 96, 78), (96, 76, 60), (235, 180, 90), (210, 150, 130)),      # 可可
    ((72, 72, 72), (52, 52, 52), (255, 170, 60), (220, 130, 120)),       # 黑珍珠
    ((140, 200, 240), (108, 175, 222), (255, 150, 60), (255, 180, 170)),  # 天空蓝
    ((255, 152, 182), (245, 120, 158), (255, 120, 90), (255, 170, 190)),  # 樱花粉
    ((178, 228, 138), (152, 210, 112), (255, 160, 70), (255, 190, 160)),  # 薄荷绿
    ((198, 168, 240), (172, 138, 226), (255, 150, 90), (240, 170, 220)),  # 葡萄紫
    ((255, 222, 132), (250, 200, 100), (255, 140, 26), (255, 170, 150)),  # 奶油金
]

BODY_TYPES = ['round', 'round', 'plump', 'slim']


def contrast(scheme):
    """深色鸡配白描边, 浅色鸡配深棕描边"""
    body = scheme[0]
    lum = 0.299 * body[0] + 0.587 * body[1] + 0.114 * body[2]
    return (255, 255, 255) if lum < 128 else DARK


def random_pattern():
    r = random.random()
    if r < 0.30:
        return 'none'
    if r < 0.50:
        return 'dots'
    if r < 0.70:
        return 'stripes'
    if r < 0.80:
        return 'heart'
    if r < 0.93:
        return 'star'
    return 'rainbow'          # 稀有彩虹鸡


def random_accessory():
    r = random.random()
    if r < 0.72:
        return None
    if r < 0.83:
        return 'bow'
    if r < 0.91:
        return 'crown'
    if r < 0.97:
        return 'glasses'
    return 'hat'


# ============ 音效(程序合成, 无需素材文件) ============
def _synth(freq_from, freq_to, dur, vol, noise=False, wave='sine'):
    rate = 44100
    n = int(rate * dur)
    buf = array.array('h')
    for i in range(n):
        t = i / rate
        frac = i / max(1, n - 1)
        freq = freq_from + (freq_to - freq_from) * frac
        env = min(1.0, i / max(1, int(rate * 0.006))) * math.exp(-3.0 * frac)
        if noise:
            v = random.uniform(-1, 1)
        else:
            v = math.sin(2 * math.pi * freq * t) if wave == 'sine' else \
                (1.0 if math.sin(2 * math.pi * freq * t) >= 0 else -1.0)
        s = int(v * env * vol * 32767)
        buf.append(s)  # L
        buf.append(s)  # R
    return pygame.mixer.Sound(buffer=buf.tobytes())


def _synth_hatch():
    """破壳噪声(0-0.12s) + 小鸡叽(0.12s后), 合成为一个音效"""
    rate = 44100
    n = int(rate * 0.28)
    buf = array.array('h')
    for i in range(n):
        t = i / rate
        if t < 0.12:  # 破壳: 短噪声
            frac = t / 0.12
            v = random.uniform(-1, 1) * (1.0 - frac * 0.7) * 0.55
        else:         # 叽: 高频chirp
            j = t - 0.12
            frac = j / 0.16
            freq = 1900 + 650 * frac
            env = math.exp(-3.0 * frac) * min(1.0, j / 0.005)
            v = math.sin(2 * math.pi * freq * j) * env * 0.4
        s = int(v * 32767)
        buf.append(s)
        buf.append(s)
    return pygame.mixer.Sound(buffer=buf.tobytes())


class SoundBox:
    """全局音效控制器: 所有声音都限频, 避免小鸡多时重叠密集"""

    def __init__(self):
        self.egg = _synth(520, 280, 0.09, 0.5)          # 生蛋: 啵
        self.hatch = _synth_hatch()                     # 孵化: 咔啦+叽
        self.cheeps = [                                  # 行走: 3种唧唧声变体
            _synth(1500, 2100, 0.08, 0.30),
            _synth(1750, 1450, 0.07, 0.28),
            _synth(2100, 2450, 0.06, 0.26),
        ]
        self._next_cheep = 0
        self._last_egg = -10000
        self._last_hatch = -10000

    def cheep(self, now, count):
        """行走唧唧声: 鸡越多间隔越短, 但有下限, 每次只响一声"""
        if count <= 0 or now < self._next_cheep:
            return
        gap = max(300, 950 - count * 5)
        self._next_cheep = now + random.randint(gap, gap + 400)
        s = random.choice(self.cheeps)
        s.set_volume(random.uniform(0.10, 0.20))
        s.play()

    def egg_pop(self, now):
        if now - self._last_egg < 350:
            return
        self._last_egg = now
        self.egg.set_volume(0.40)
        self.egg.play()

    def hatch_pop(self, now):
        if now - self._last_hatch < 500:
            return
        self._last_hatch = now
        self.hatch.set_volume(0.45)
        self.hatch.play()


# ============ 小鸡 ============
class Chick:
    def __init__(self, x, y, size=None, grow=False, genes=None):
        if genes:
            self.scheme, self.pattern, self.body_type, self.accessory = genes
        else:
            self.scheme = random.choice(SCHEMES)
            self.pattern = random_pattern()
            self.body_type = random.choice(BODY_TYPES)
            self.accessory = random_accessory()
        if size is None:
            r = random.random()
            if r < 0.04:        # 稀有巨型
                size = random.uniform(80, 120)
                self.speed = random.uniform(22, 38)
            elif r < 0.10:      # 迷你
                size = random.uniform(26, 34)
                self.speed = random.uniform(60, 110)
            else:
                size = random.uniform(46, 74)
                self.speed = random.uniform(36, 80)
        else:
            self.speed = random.uniform(36, 80)
        self.x, self.y = float(x), float(y)
        self.size = size
        ang = random.uniform(0, math.tau)
        self.vx = math.cos(ang) * self.speed
        self.vy = math.sin(ang) * self.speed
        self.walk = random.uniform(0, math.tau)
        self.turn_t = random.uniform(1.0, 2.5)
        self.egg_t = random.uniform(4, 10)
        self.grow = grow
        # 孵出的小鸡长大目标随机(42~85, 7% 巨型宝宝 95~125), 避免尺寸统一
        if grow:
            if random.random() < 0.07:
                self.grow_target = random.uniform(95, 125)
            else:
                self.grow_target = random.uniform(42, 85)
        else:
            self.grow_target = self.size
        self.hop = random.uniform(0, math.tau)

    @property
    def genes(self):
        return (self.scheme, self.pattern, self.body_type, self.accessory)

    def offscreen(self, w, h, pad=60):
        return (self.x < -pad or self.x > w + pad or
                self.y < -pad or self.y > h + pad)

    def update(self, dt, w, h):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.walk += dt * 10
        self.hop += dt * random.uniform(4, 8)

        # 缓慢随机转向(不反弹, 走着走着就走出屏幕)
        self.turn_t -= dt
        if self.turn_t <= 0:
            self.turn_t = random.uniform(1.0, 2.5)
            ang = random.uniform(-math.pi / 5, math.pi / 5)
            c, s = math.cos(ang), math.sin(ang)
            self.vx, self.vy = self.vx * c - self.vy * s, self.vx * s + self.vy * c
            sp = math.hypot(self.vx, self.vy) or 1
            self.vx = self.vx / sp * self.speed
            self.vy = self.vy / sp * self.speed

        # 孵出的小鸡慢慢长大到各自的随机目标
        if self.grow and self.size < self.grow_target:
            self.size += 6 * dt

    def draw(self, surf):
        x, y, r = self.x, self.y, self.size
        flip = self.vx < 0
        bob = math.sin(self.hop) * r * 0.08
        body, wing, beak, cheek = self.scheme
        ol = contrast(self.scheme)
        lw = max(2, int(r * 0.09))

        # 腿
        leg_swing = math.sin(self.walk) * r * 0.35
        leg_y = y + r * 0.62 + bob
        for dx in (-r * 0.22 + leg_swing, r * 0.22 - leg_swing):
            pygame.draw.line(surf, beak, (x + dx * 0.6, y + r * 0.45 + bob),
                             (x + dx, leg_y), max(2, int(r * 0.1)))
            pygame.draw.line(surf, beak, (x + dx, leg_y),
                             (x + dx + r * 0.16, leg_y + r * 0.08), max(2, int(r * 0.1)))

        # 身体(按体型)
        if self.body_type == 'plump':
            bw, bh = r * 2.2, r * 1.35
        elif self.body_type == 'slim':
            bw, bh = r * 1.55, r * 1.75
        else:
            bw, bh = r * 1.9, r * 1.55
        body_rect = pygame.Rect(0, 0, bw, bh)
        body_rect.center = (x, y + bob * 0.6)
        self._fill_body(surf, body_rect, body, ol, lw)

        # 纹理(身体上)
        if self.pattern not in ('none', 'rainbow'):
            self._draw_pattern(surf, x, y + bob * 0.6, r, bw, bh)

        # 头(圆, 朝移动方向)
        hd = r * 0.52 if flip else -r * 0.52
        hx, hy = x + hd, y - r * 0.45 + bob * 0.6
        head_r = r * 0.52
        pygame.draw.circle(surf, body, (int(hx), int(hy)), int(head_r))
        pygame.draw.circle(surf, ol, (int(hx), int(hy)), int(head_r), lw)

        # 呆毛
        pygame.draw.line(surf, ol,
                         (hx + (r * 0.18 if flip else -r * 0.18), hy - r * 0.42),
                         (hx + (r * 0.34 if flip else -r * 0.34), hy - r * 0.62),
                         max(2, int(r * 0.05)))

        # 嘴
        bx = hx + (r * 0.5 if flip else -r * 0.5)
        by = hy + r * 0.08
        pygame.draw.polygon(surf, beak, [
            (bx, by - r * 0.06),
            (bx + (r * 0.34 if flip else -r * 0.34), by + r * 0.02),
            (bx, by + r * 0.2)])

        # 腮红(已移除, 白色背景上显突兀)

        # 眼睛
        ex = hx + (r * 0.2 if flip else -r * 0.2)
        ey = hy - r * 0.12
        pygame.draw.circle(surf, (40, 40, 40), (int(ex), int(ey)), max(2, int(r * 0.11)))
        pygame.draw.circle(surf, (255, 255, 255), (int(ex + r * 0.04), int(ey - r * 0.04)),
                           max(1, int(r * 0.04)))

        # 眼镜
        if self.accessory == 'glasses':
            g = (70, 60, 70)
            gr = int(r * 0.23)
            pygame.draw.circle(surf, g, (int(ex), int(ey)), gr, max(1, int(r * 0.05)))
            gx2 = int(ex + (r * 0.46 if flip else -r * 0.46))
            pygame.draw.circle(surf, g, (gx2, int(ey)), gr, max(1, int(r * 0.05)))
            pygame.draw.line(surf, g, (ex, ey), (gx2, ey), max(1, int(r * 0.05)))

        # 翅膀(摆动)
        wd = r * 0.32 if flip else -r * 0.32
        wy = y + r * 0.18 + bob * 0.6 + math.sin(self.walk) * r * 0.12
        wing_rect = pygame.Rect(0, 0, r * 0.52, r * 0.4)
        wing_rect.center = (x + wd, wy)
        pygame.draw.ellipse(surf, wing, wing_rect)
        pygame.draw.ellipse(surf, ol, wing_rect, lw)

        # 头部配饰(蝴蝶结 / 皇冠 / 帽子)
        if self.accessory == 'bow':
            ax = x + (r * 0.15 if flip else -r * 0.15)
            ay = hy - r * 0.48
            bow_c = (255, 90, 140)
            pygame.draw.polygon(surf, bow_c,
                                [(ax, ay), (ax - r * 0.45, ay - r * 0.26), (ax - r * 0.45, ay + r * 0.26)])
            pygame.draw.polygon(surf, bow_c,
                                [(ax, ay), (ax + r * 0.45, ay - r * 0.26), (ax + r * 0.45, ay + r * 0.26)])
            pygame.draw.circle(surf, (230, 60, 110), (int(ax), int(ay)), max(2, int(r * 0.12)))
        elif self.accessory == 'crown':
            ax = x + (r * 0.15 if flip else -r * 0.15)
            ay = hy - r * 0.5
            cw = r * 0.72
            pts = [(ax - cw / 2, ay), (ax - cw / 2, ay - r * 0.26),
                   (ax - cw / 4, ay - r * 0.1), (ax, ay - r * 0.36),
                   (ax + cw / 4, ay - r * 0.1), (ax + cw / 2, ay - r * 0.26),
                   (ax + cw / 2, ay)]
            pygame.draw.polygon(surf, (255, 200, 40), pts)
            pygame.draw.polygon(surf, (190, 140, 20), pts, 2)
            pygame.draw.circle(surf, (255, 60, 60), (int(ax), int(ay - r * 0.18)),
                               max(2, int(r * 0.08)))
        elif self.accessory == 'hat':
            ax = x + (r * 0.15 if flip else -r * 0.15)
            ay = hy - r * 0.5
            hat_c = (70, 150, 220)
            pygame.draw.ellipse(surf, hat_c, (ax - r * 0.58, ay - r * 0.12, r * 1.16, r * 0.36))
            pygame.draw.ellipse(surf, hat_c, (ax - r * 0.36, ay - r * 0.62, r * 0.72, r * 0.55))
            pygame.draw.ellipse(surf, (50, 120, 190),
                                (ax - r * 0.36, ay - r * 0.62, r * 0.72, r * 0.55), 2)
            pygame.draw.rect(surf, (255, 255, 255),
                             (ax - r * 0.28, ay - r * 0.6, r * 0.56, r * 0.12))

    def _fill_body(self, surf, rect, body, ol, lw):
        if self.pattern == 'rainbow':
            # 逐行扫描, 只画椭圆内部的彩虹色带(避免超出椭圆轮廓)
            cx, cy = rect.centerx, rect.centery
            hw, hh = rect.width / 2.0, rect.height / 2.0
            n = len(RAINBOW)
            for py in range(rect.top, rect.bottom):
                t = (py - cy) / hh
                if abs(t) > 1:
                    continue
                half_w = hw * math.sqrt(1 - t * t)
                x0 = max(rect.left, int(cx - half_w))
                x1 = min(rect.right, int(cx + half_w))
                if x1 <= x0:
                    continue
                idx = min(n - 1, int((py - rect.top) * n / rect.height))
                pygame.draw.line(surf, RAINBOW[idx], (x0, py), (x1, py))
        else:
            pygame.draw.ellipse(surf, body, rect)
        pygame.draw.ellipse(surf, ol, rect, lw)

    def _draw_pattern(self, surf, cx, cy, r, bw, bh):
        pc = contrast(self.scheme)
        if self.pattern == 'dots':
            for i in range(4):
                ang = i * math.tau / 4 + self.walk * 0.4
                dx = math.cos(ang) * bw * 0.26
                dy = math.sin(ang) * bh * 0.24
                pygame.draw.circle(surf, pc, (int(cx + dx), int(cy + dy)),
                                   max(2, int(r * 0.11)))
        elif self.pattern == 'stripes':
            for off in (-r * 0.24, 0, r * 0.24):
                pygame.draw.arc(surf, pc,
                                (cx - bw * 0.55, cy + off - bh * 0.5, bw * 1.1, bh),
                                math.pi * 0.15, math.pi * 0.85, max(2, int(r * 0.08)))
        elif self.pattern == 'heart':
            s = r * 0.38
            pygame.draw.circle(surf, pc, (int(cx - s * 0.35), int(cy - s * 0.15)), int(s * 0.42))
            pygame.draw.circle(surf, pc, (int(cx + s * 0.35), int(cy - s * 0.15)), int(s * 0.42))
            pygame.draw.polygon(surf, pc,
                                [(cx - s * 0.7, cy - s * 0.05), (cx + s * 0.7, cy - s * 0.05),
                                 (cx, cy + s * 0.7)])
        elif self.pattern == 'star':
            s = r * 0.42
            pts = []
            for i in range(10):
                ang = -math.pi / 2 + i * math.pi / 5
                rad = s if i % 2 == 0 else s * 0.45
                pts.append((cx + math.cos(ang) * rad, cy + math.sin(ang) * rad))
            pygame.draw.polygon(surf, pc, pts)


# ============ 蛋(可能基因突变, 蛋壳颜色=孵出小鸡颜色) ============
class Egg:
    def __init__(self, x, y, genes):
        self.x, self.y = float(x), float(y + 40)
        # 基因突变: 45% 概率孵出的小鸡完全变异, 打散同色垄断
        if random.random() < 0.45:
            self.genes = (random.choice(SCHEMES), random_pattern(),
                          random.choice(BODY_TYPES), random_accessory())
        else:
            self.genes = genes
        body = self.genes[0][0]
        self.shell = tuple(int(c * 0.55 + 255 * 0.45) for c in body)
        self.outline = contrast(self.genes[0])
        self.hatch_t = random.uniform(6, 12)
        self.cracked = False

    def update(self, dt):
        self.hatch_t -= dt
        if not self.cracked and self.hatch_t <= 2.2:
            self.cracked = True
        return self.hatch_t <= 0

    def draw(self, surf):
        x, y = self.x, self.y
        wob = math.sin(pygame.time.get_ticks() * 0.01) * 2.5 if self.cracked else 0
        rect = pygame.Rect(0, 0, 56, 70)
        rect.center = (x + wob, y)
        pygame.draw.ellipse(surf, self.shell, rect)
        pygame.draw.ellipse(surf, self.outline, rect, 3)
        if self.cracked:
            # 裂纹露出里面的小鸡颜色
            body = self.genes[0][0]
            pygame.draw.line(surf, body, (x + wob - 8, y - 10), (x + wob - 2, y), 5)
            pygame.draw.line(surf, body, (x + wob + 2, y - 4), (x + wob + 8, y + 12), 5)
            pygame.draw.lines(surf, self.outline, False,
                              [(x + wob - 8, y - 16), (x + wob, y - 4), (x + wob - 9, y + 10)], 3)
            pygame.draw.lines(surf, self.outline, False,
                              [(x + wob + 8, y - 12), (x + wob + 4, y + 4), (x + wob + 11, y + 16)], 3)


# ============ 碎片粒子(破壳特效) ============
class Shard:
    def __init__(self, x, y, color):
        ang = random.uniform(0, math.tau)
        sp = random.uniform(60, 200)
        self.x, self.y = x, y
        self.vx = math.cos(ang) * sp
        self.vy = math.sin(ang) * sp - 60
        self.life = random.uniform(0.4, 0.9)
        self.s = random.uniform(5, 12)
        self.color = color

    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 300 * dt
        self.life -= dt
        return self.life > 0

    def draw(self, surf):
        alpha = max(0.0, min(1.0, self.life))
        c = tuple(int(v * alpha + 255 * (1 - alpha)) for v in self.color)
        pygame.draw.rect(surf, c, (self.x, self.y, self.s, self.s))


# ============ 主程序 ============
def main():
    # 音效初始化(必须在 pygame.init 之前); 无音频设备则静音运行
    sound = None
    try:
        pygame.mixer.pre_init(44100, -16, 2, 512)
        pygame.mixer.init()
        sound = SoundBox()
    except Exception:
        sound = None

    pygame.init()
    info = pygame.display.Info()
    w, h = info.current_w, info.current_h
    screen = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
    pygame.display.set_caption("Chick Lock")
    pygame.mouse.set_visible(False)
    pygame.event.set_grab(True)          # 独占输入, 拦截 Alt+Tab
    clock = pygame.time.Clock()

    font = None
    for name in ("microsoftyahei", "msyh", "simhei", "arial"):
        try:
            font = pygame.font.SysFont(name, 30)
            if font is not None:
                break
        except Exception:
            pass

    chicks, eggs, shards = [], [], []

    def spawn_chick(x, y, size=None, grow=False, genes=None):
        if len(chicks) + len(eggs) >= MAX_BIOS:
            return
        x = max(40.0, min(w - 40.0, x))
        y = max(40.0, min(h - 130.0, y))
        chicks.append(Chick(x, y, size=size, grow=grow, genes=genes))

    def spawn_egg(x, y, genes):
        if len(chicks) + len(eggs) >= MAX_BIOS:
            return
        x = max(50.0, min(w - 50.0, x))
        y = max(50.0, min(h - 160.0, y))
        eggs.append(Egg(x, y, genes))
        if sound:
            sound.egg_pop(pygame.time.get_ticks())

    def hatch(egg):
        spawn_chick(egg.x, egg.y, size=random.uniform(30, 44), grow=True, genes=egg.genes)
        for _ in range(6):
            shards.append(Shard(egg.x, egg.y, egg.shell))
        if sound:
            sound.hatch_pop(pygame.time.get_ticks())

    running = True
    last_keydown = -100000   # 用于 KEYDOWN/TEXTINPUT 去重(输入法场景)
    last_auto = -100000      # 屏保自动生成时间戳
    while running:
        dt = clock.tick(FPS) / 1000.0
        now = pygame.time.get_ticks()
        mods = pygame.key.get_mods()

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                running = False
            elif ev.type == pygame.KEYDOWN:
                last_keydown = now
                # 家长退出: Ctrl+Alt+Q
                if ev.key == pygame.K_q and (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_ALT):
                    running = False
                else:
                    spawn_chick(random.uniform(80, w - 80), random.uniform(80, h * 0.55))
            elif ev.type == pygame.TEXTINPUT:
                # 中文输入法组合时 KEYDOWN 被 IME 吞掉, 用文本事件兜底
                if ev.text.lower() == 'q' and (mods & pygame.KMOD_CTRL) and (mods & pygame.KMOD_ALT):
                    running = False
                elif now - last_keydown > 80:
                    spawn_chick(random.uniform(80, w - 80), random.uniform(80, h * 0.55))
            elif ev.type == pygame.MOUSEBUTTONDOWN:
                spawn_chick(*ev.pos)

        # 更新
        for c in chicks:
            c.update(dt, w, h)
            c.egg_t -= dt
            if c.egg_t <= 0:
                c.egg_t = random.uniform(4, 10)
                spawn_egg(c.x, c.y + c.size, c.genes)
        # 走出屏幕的小鸡直接消失
        chicks = [c for c in chicks if not c.offscreen(w, h)]

        # 屏保: 空屏(没鸡没蛋)一段时间后, 自动飘出几只小鸡
        if not chicks and not eggs:
            if now - last_auto >= AUTO_SPAWN_GAP_MS:
                last_auto = now
                for _ in range(random.randint(3, 6)):
                    spawn_chick(random.uniform(80, w - 80),
                                random.uniform(80, h * 0.55))

        # 鸡与鸡之间的软斥力
        n = len(chicks)
        for i in range(n):
            ci = chicks[i]
            for j in range(i + 1, n):
                cj = chicks[j]
                dx = cj.x - ci.x
                dy = cj.y - ci.y
                d2 = dx * dx + dy * dy
                min_d = ci.size + cj.size
                if 0 < d2 < min_d * min_d:
                    d = math.sqrt(d2) or 0.01
                    push = (min_d - d) * 2.2
                    ux, uy = dx / d, dy / d
                    ci.x -= ux * push * dt * 10
                    ci.y -= uy * push * dt * 10
                    cj.x += ux * push * dt * 10
                    cj.y += uy * push * dt * 10

        for e in list(eggs):
            if e.update(dt):
                eggs.remove(e)
                hatch(e)
        shards = [s for s in shards if s.update(dt)]

        # 行走唧唧声(全局限频)
        if sound:
            sound.cheep(now, len(chicks))

        # 绘制
        screen.fill(BG)
        for s in shards:
            s.draw(screen)
        for e in eggs:
            e.draw(screen)
        for c in chicks:
            c.draw(screen)

        # 提示文字
        if font:
            tip = font.render("任意键/点击 召唤小鸡 · 每只都独一无二 · 家长退出 Ctrl+Alt+Q",
                              True, TEXT_C)
            screen.blit(tip, tip.get_rect(center=(w // 2, h - 34)))
            if chicks or eggs:
                cnt = font.render("小鸡 %d    蛋 %d" % (len(chicks), len(eggs)), True, TEXT_C)
                screen.blit(cnt, (24, 16))

        pygame.display.flip()

    pygame.mouse.set_visible(True)
    pygame.event.set_grab(False)
    pygame.quit()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # 兜底: 出错也恢复鼠标/退出全屏
        pygame.mouse.set_visible(True)
        pygame.event.set_grab(False)
        pygame.quit()
        raise
