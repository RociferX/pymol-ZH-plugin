# 兼容性记录

“自动检查通过”指离屏控件、翻译资源、打包及隔离安装/自动加载检查；“实际桌面通过”另需真实屏幕和键鼠证据。两者分开记录。

| 系统与环境 | 自动检查 | 实际桌面 | 状态 |
| --- | --- | --- | --- |
| Windows，conda-forge PyMOL 3.1.0，Python 3.12，PyQt5 / Qt 5.15.15 | 本地通过 | 0.3.1 指定窗口通过 | 基准环境；0.3.2 另做程序回归 |
| GitHub Windows runner，PyMOL 3.1.0，Python 3.12，PyQt5 | 见下方 CI | 未进行 | 自动回归环境 |
| Ubuntu 24.04，PyMOL 3.1.0，Python 3.12，PyQt5，Noto Sans CJK | [0.3.2 自动检查通过](https://github.com/RociferX/pymol-ZH-plugin/actions/runs/41086189819) | 未进行 | 新增 Linux 自动检查 |
| macOS | 未验证 | 未验证 | 欢迎提交复现信息 |
| 其他 PyMOL 版本或 Qt 绑定 | 未验证 | 未验证 | 按实际结果补充 |

[查看自动检查的运行结果与环境清单](https://github.com/RociferX/pymol-ZH-plugin/actions/workflows/checks.yml)。每次运行保留按平台区分的 JSON 报告及插件 ZIP；完整安装依赖版本在 `Record environment` 步骤中。

当前 CI 使用仓库的 `environment-open-source.yml`，固定 PyMOL 3.1.0、Python 3.12 和 PyQt5，其余依赖由 conda-forge 解析。仓库推送、PR、版本标签和手动触发均会检查。离屏检查不代表已验证真实 OpenGL 绘图区或所有桌面布局。

新环境反馈入口：[兼容性反馈](https://github.com/RociferX/pymol-ZH-plugin/issues/new?template=compatibility.yml)。请提供系统及架构、安装来源、PyMOL/插件/Python/Qt 版本、系统缩放、操作步骤与检查结果。
