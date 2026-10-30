# pymol-ZH-plugin

**PyMOL 开源版的简体中文显示插件。安装后正常启动 PyMOL 即可显示中文，可随时切回英文。**

通过 Qt 绘制映射和覆盖面板显示中文，保留英文命令、参数键、选项值、用户输入和分子数据。插件独立安装，无需修改 PyMOL 原程序文件或使用专用启动器。

[下载最新版插件](https://github.com/RociferX/pymol-ZH-plugin/releases/latest) · [更新记录](CHANGELOG.md) · [检查范围](docs/VALIDATION.md)

![中文菜单、对象操作区与右下角控件](docs/images/main.png)

## 安装

1. 从 [Releases](https://github.com/RociferX/pymol-ZH-plugin/releases) 下载 **`pymol_zh_cn-0.3.1.zip`**，无需解压。GitHub 自动生成的 `Source code` 压缩包用于开发，请选择带版本号的插件 ZIP。
2. 在 PyMOL 中打开 `Plugin → Plugin Manager → Install New Plugin → Choose file...`，选择该 ZIP。
3. 首次安装后当前窗口自动显示中文；更新已经加载的旧版本时，重启一次 PyMOL。
4. 以后从原有图标或命令照常启动，插件默认自动加载。

在 `插件 → 中文显示 / Chinese Display` 中选择 **恢复英文显示** 或 **启用中文显示**，即时切换语言。

### 停用和卸载

在插件管理器的已安装插件中找到 `pymol_zh_cn`，取消 `startup` 后重启可停止自动加载；使用管理器卸载后重启可移除插件。临时查看原始英文帮助和错误信息，可以直接使用“恢复英文显示”。

## 中文覆盖

| 区域 | 内容 |
| --- | --- |
| 主界面 | 常用菜单与子菜单、工具栏、按钮、标签、选项卡、非编辑下拉框、工具提示 |
| 绘图区右侧 | **A 动作、S 显示、H 隐藏、L 标签、C 颜色**及其多级菜单、动态对象与配色色块 |
| 右下角 | 鼠标模式、默认键位表、选择粒度、状态/帧数、播放控制、序列和全屏按钮 |
| 导入和导出 | 密度图、轨迹、Maestro、MTZ、动画、PNG，以及获取 PDB、保存分子等窗口 |
| 高级设置 | 基准环境中的 **779 项**中文名称和简要说明，支持中文或英文参数键搜索 |
| 属性与向导 | 属性分类及 34 个常见字段；测量、成对拟合、密度图、外观、塑形、突变和标签向导；标签包含 9 种模式 |
| 命令帮助 | **299 篇独立帮助**，含别名共 330 个主题；语法、Python API 和示例保留原语法 |
| 输出与异常 | 匹配版本源码整理的 **1331 条反馈和错误句式**，另含常见 Python 异常、启动消息及功能限制说明 |

这些数字对应下述已测试的 PyMOL 3.1.0 环境。第三方模块的任意输出、未知文字及驱动原始诊断未命中词典时显示原文；用户标签、序列、文件内容、路径、对象名和可编辑输入保留原文。

## 兼容性与布局

已验证：**Windows、conda-forge PyMOL Open-Source 3.1.0（`py312h7aa25ef_8`）、Python 3.12、PyQt5 / Qt 5.15.15**。其他 PyMOL 版本、Qt 绑定、macOS 和 Linux 尚未验证。需要 PyMOL 的 Qt 图形界面及可显示中文的系统字体。

中文按钮、下拉框和长说明会扩展尺寸或换行；设置表与标签页参考可用屏幕宽度。已检查 100%、125%、150%、200% 离屏缩放，并完成 100% 和 200% 的指定窗口实际桌面检查，详见[检查记录](docs/VALIDATION.md)。

右侧面板覆盖原 OpenGL 英文侧栏，菜单复用原始命令。右下角状态定时刷新；自定义 `button` 重绑定不会同步到默认键位表。恢复英文时隐藏覆盖层并撤销临时菜单包装。插件适配可由 `QStyleFactory` 重建的 Qt 基础样式。

控制台和异常详情的中文显示层保留原控件中的英文输出文档；切回英文可查看、复制原始诊断。插件保留开源版原有功能边界，例如 MTZ 窗口的可见文字翻译不会添加原版缺少的功能。

## 开发与检查

创建基准环境：

```powershell
conda env create -f environment-open-source.yml
conda activate pymol-open-source-zh
```

在仓库根目录运行现有检查及打包脚本：

```powershell
python tests/test_display.py
python scripts/verify_output.py
python scripts/run_gui_verification.py
python scripts/check_form_layouts.py
python scripts/build_plugin.py
python scripts/check_package.py
python scripts/check_plugin_installation.py
```

Qt 检查脚本使用离屏模式，不操作用户的桌面窗口。`check_form_layouts.py` 默认检查 100%；设置环境变量 `QT_SCALE_FACTOR` 为 `1.25`、`1.5`、`2` 可分别检查其他缩放。标准安装检查使用隔离用户目录，验证 ZIP 安装与后续自动加载。结果写入被 Git 忽略的 `artifacts/`。

可选源码覆盖盘点需要另行获取对应的 [PyMOL v3.1.0 源码](https://github.com/schrodinger/pymol-open-source/tree/v3.1.0)：

```powershell
python scripts/inventory_translation.py --source path/to/pymol-open-source
```

项目结构：

```text
pymol_zh_cn/                 插件代码与翻译词典
  translations.tsv          界面词典
  settings_zh.tsv            设置中文名称与说明
  messages_zh.tsv            控制台反馈和异常词典
  help_zh.tsv                命令帮助词典
scripts/                    构建、安装与程序检查
tests/                      控件回归检查
docs/                       使用截图与检查范围
environment-open-source.yml 基准环境配方
```

`messages_zh.tsv` 和 `help_zh.tsv` 使用转义 TSV：字段中的 `\n` 表示换行，`\\` 表示反斜杠。帮助中的原版语法、API 和代码示例通过标记引用，修改翻译后请运行 `verify_output.py` 检查原文保留情况。

## 许可与来源

本项目是独立的社区中文显示扩展。插件原创代码采用 [MIT License](LICENSE)。内置帮助和原生消息的英文源文及其派生译文保留 [PyMOL 原始许可](pymol_zh_cn/PYMOL-LICENSE.txt)，详见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。发布包仅包含插件，不捆绑 PyMOL、Python 或 Qt。

PyMOL 上游：[schrodinger/pymol-open-source](https://github.com/schrodinger/pymol-open-source)；社区构建：[conda-forge/pymol-open-source-feedstock](https://github.com/conda-forge/pymol-open-source-feedstock)。Open-Source PyMOL is Copyright (C) Schrodinger, LLC. PyMOL is a trademark of Schrodinger, LLC.
