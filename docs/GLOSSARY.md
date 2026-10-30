# 中英术语与检索

在浏览器或编辑器中按 `Ctrl+F`（macOS：`Command+F`），输入中文或英文检索本页。高级设置窗口本身也支持中文名称、简要说明及英文参数键搜索。

## 对照英文教程

| 英文 | 中文显示或含义 | 命令示例 |
| --- | --- | --- |
| Action / A | 动作（部分菜单为“操作”） | 右侧对象动作菜单 |
| Show / S | 显示 | `show cartoon` |
| Hide / H | 隐藏 | `hide lines` |
| Label / L | 标签 | `label name CA, resn` |
| Color / C | 颜色 | `color cyan` |
| Lines | 线条 | `show lines` |
| Sticks | 棒状 | `show sticks` |
| Spheres | 球体 | `show spheres` |
| Cartoon | 二级结构示意 | `show cartoon` |
| Ribbon | 带状 | `show ribbon` |
| Surface | 表面 | `show surface` |
| Mesh | 网格 | `show mesh` |
| Dots | 点状 | `show dots` |
| Transparency | 透明度 | `set transparency, 0.5` |
| Zoom | 缩放 | `zoom all` |
| Orient | 定向 | `orient all` |
| Center | 居中 | `center all` |
| Scene | 场景 | `scene view1, store` |
| Selection | 选择范围 / 选区 | `select protein, polymer.protein` |
| Residue | 残基 | `select res10, resi 10` |
| Chain | 链 | `select chainA, chain A` |
| Atom | 原子 | `select calpha, name CA` |
| State | 状态：对象的一组坐标 | `set state, 1` |
| Frame | 帧：动画时间位置 | `frame 1` |
| Ray tracing | 光线追踪 / 光追 | `ray` |
| Fetch | 获取结构 | `fetch 1ubq` |
| Load | 加载文件 | `load example.pdb` |
| Save | 保存 | `save result.pse` |

命令示例使用英文语法。`State` 和 `Frame` 在动画中有关联，分别表示对象坐标状态和动画帧，界面翻译按上下文处理。

## 常用设置键

| 英文参数键 | 中文含义 |
| --- | --- |
| `line_width` | 线条宽度 |
| `stick_radius` | 棒状半径 |
| `sphere_scale` | 球体缩放 |
| `transparency` | 表面透明度 |
| `cartoon_transparency` | 二级结构示意透明度 |
| `bg_rgb` | 背景颜色 |
| `orthoscopic` | 正交投影 |
| `ray_trace_mode` | 光追模式 |

例如在高级设置中搜索“线宽”或 `line_width`，再编辑数值；表格底部和工具提示可以查看原始英文键。完整设置词典见 [`settings_zh.tsv`](../pymol_zh_cn/settings_zh.tsv)，界面词典见 [`translations.tsv`](../pymol_zh_cn/translations.tsv)。
