# 🐤 小鸡乐园 (Chick Lock)

> 全屏小鸡锁屏游戏 —— 防小朋友乱玩电脑的 kiosk 模式全屏程序
> A fullscreen chicken-themed kiosk lock screen for Windows. When the kids want to "help" you use the computer, let them play with the chickens instead.

按任意键 / 点击鼠标，就会冒出一只**独一无二**的小鸡：它会满屏乱跑、下蛋、孵小鸡，然后自己走出屏幕消失。所有键盘和鼠标操作都被程序吃掉，电脑完全锁死，小朋友玩得开心，你的电脑安然无恙。

Press any key or click anywhere to spawn a unique chicken. Chickens wander around, lay eggs, hatch babies, then walk off-screen and disappear. All keyboard & mouse input is captured by the program — the PC is fully locked while the kids play.

---

## ✨ 特性 Features

- 🖥️ **全屏锁定** — 白色全屏窗口，隐藏鼠标，独占输入，系统级屏蔽 `Win` 键 / `Alt+Tab` / `Alt+F4`
- 🐔 **每只鸡都独一无二** — 随机组合：
  - **颜色**：11 套色板（经典黄 / 雪白 / 蜜橘 / 浅棕 / 可可 / 黑珍珠 / 天空蓝 / 樱花粉 / 薄荷绿 / 葡萄紫 / 奶油金）
  - **花纹**：圆点 / 条纹 / 爱心 / 星星 / 稀有彩虹渐变
  - **体型**：圆滚滚 / 胖墩墩 / 瘦高个
  - **配饰**：蝴蝶结 🎀 / 皇冠 👑 / 眼镜 / 小蓝帽
  - **大小**：迷你 → 普通 → 4% 概率的巨型鸡（占屏 1/4）
- 🥚 **基因继承 + 突变** — 蛋壳颜色 = 即将孵出小鸡的颜色（45% 概率基因突变，防止单一颜色垄断种群）；破壳有碎片特效
- 🔊 **音效** — 生蛋"啵"、破壳"咔啦+叽"、行走唧唧声；全部限频防重叠（鸡越多间隔越短，但有下限），嘈杂但不清脆的音量自动随机微调
- 🎬 **屏保模式** — 屏幕空 6 秒后自动飘出 3~6 只小鸡，屏幕永不空白
- ⌨️ **输入法兼容** — 中文输入法组合拼音时按键同样出鸡（IME 兼容，防丢按键）
- 🔒 **家长逃生** — `Ctrl+Alt+Q` 退出；`Ctrl+Alt+Del` 是系统级后门，永远有效

## 🖥️ 运行环境 Requirements

| 项目 | 要求 |
|------|------|
| 系统 | Windows 10/11（音效与按键屏蔽依赖 Windows API） |
| Python | 3.10+（建议 3.12/3.13） |
| pygame | 2.x |

## 🚀 运行方法 Usage

```bash
# 安装依赖
pip install pygame

# 运行（pythonw.exe 可避免黑色控制台窗口）
python chick_lock.py
```

或者直接创建桌面快捷方式，目标指向：

```
C:\...\Python313\pythonw.exe  "D:\...\chick_lock.py"
```

### 家长退出 Exit

- **`Ctrl + Alt + Q`** — 正常退出
- **`Ctrl + Alt + Del`** — Windows 安全界面（程序无法拦截，永远可用）

## ⚙️ 可调参数 Configuration

文件顶部的常量可直接修改：

| 常量 | 默认 | 说明 |
|------|------|------|
| `MAX_BIOS` | 70 | 屏幕上鸡+蛋的数量上限 |
| `AUTO_SPAWN_GAP_MS` | 6000 | 空屏多久后自动飘小鸡（屏保） |
| `SCHEMES` | 11 套 | 小鸡色板（身体/翅膀/嘴/腮红） |
| `RAINBOW` | 6 色 | 彩虹鸡渐变配色 |

## 📁 文件结构 Structure

```
chick-lock/
├── chick_lock.py   # 单文件程序（全部逻辑，无外部素材）
└── README.md
```

## 🎯 设计说明 Design Notes

- **为什么小鸡会走出屏幕消失？** 这是刻意的生态循环：小鸡出屏 → 释放名额 → 小朋友继续按键永远有新鸡。同时配合生蛋孵化，形成"生成 → 繁衍 → 离开"的完整生命周期。
- **音效不重叠的原理**：全局只有一个"说话"的小鸡（限频 300ms 起），生蛋/孵化同类音效 350/500ms 内去重。
- **基因垄断防护**：蛋有 45% 概率基因突变，蛋壳颜色始终等于孵出小鸡的颜色，规则自洽。

## 📜 许可证 License

[MIT](LICENSE)
