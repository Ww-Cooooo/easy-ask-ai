# 来源与依赖

Prompt Ready 自身的组合流程、交接模板和安装辅助脚本按 [MIT](LICENSE) 分发。

必需依赖单独安装，不把其完整内容冒充本包原创：

- [Matt Pocock / skills：grilling](https://github.com/mattpocock/skills/tree/49dd158d1076134a641b33efb035946536778336/skills/productivity/grilling)：按决策依赖分轮追问、给出推荐并等待回答。固定提交 `49dd158d1076134a641b33efb035946536778336`，MIT，版权 Matt Pocock。本包对无子 Agent 宿主提供自行调查的适配，保留用户决策边界。
- [Ww-Cooooo / more-than-yes](https://github.com/Ww-Cooooo/more-than-yes/tree/8e694886c9bbe610f04795f1221fb641f34f5e1f)：核对目标、前提、证据、方案与实际结果，补充而不迎合。固定提交 `8e694886c9bbe610f04795f1221fb641f34f5e1f`，MIT，版权 Ww-Cooooo。

于 2026-10-19 从原仓库核查提交、完整包与许可证，固定下载摘要见 [dependencies.lock.json](dependencies.lock.json)。上游许可随依赖安装保留。为保留本包方法归属，同时附上 [grilling MIT 声明](notices/grilling-MIT.txt) 与 [more-than-yes MIT 声明](notices/more-than-yes-MIT.txt)。

制作时使用 Skill Creator 组织包，并用 [Skill Improve](https://github.com/Ww-Cooooo/skill-improve) 检查判断依据、隐含上下文与独立执行条件。后者不是运行依赖。来源归属不证明本包已在所有模型、领域和宿主验证。
