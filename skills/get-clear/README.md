# Get Clear｜问清楚再改

Easy Ask AI 的反馈澄清与返修 Skill。看到当前成果却只能说“不好看”“不够高级”“不是我要的”时，Agent 会结合作品调用 grilling，一次问一个关键问题，帮助你逐步说清期望。问清并确认后，在当前对话继续实际返修。

## 安装与调用

把整个 `get-clear` 文件夹放到宿主实际使用的技能目录。Codex 与本机验证的 DeepSeek harness 支持用户目录下 `.agents/skills/`；其他环境按宿主文档或实际列表确定。刷新或新开对话后确认 `get-clear` 可见，不只检查文件存在。

- Codex：`使用 $get-clear，帮我问清这版哪里不符合我的期望，再修改。`
- DeepSeek harness：输入 `/get-clear`，随后描述反馈。
- 隐式触发：对当前成果表达含糊的不满意，不需要点名。是否实际选择由宿主与模型决定；遇到漏选时先检查列表、调用策略和读技能记录。

首次使用检查 `grilling` 与 `more-than-yes`，缺少时按 [依赖准备](references/dependencies.md) 在授权内补装。辅助脚本需要 Python 3.10+，不自动安装系统运行时。只有本 Skill 不足以赋予宿主制作网页、生成视频等工具能力；实际返修使用现有领域工具。

## 你要回答什么

你不必先懂设计术语，也不必找一份完美参考。Agent 会根据当前作品问具体的感受、情境或对照，你可以回答“都不是”“都有一点”“说不清”。每次回答都会改变下一问，已确定的内容不会反复询问。

访谈会弄清整体期望、需要保留和避免的内容、关键取舍与如何判断下一版。Agent 再用 More Than Yes 核对遗漏并复述修改方向；你确认后，它直接完成当前任务的修改和相关检查。明确的小修改直接执行。

默认不生成交给别人的长 Prompt、不要求换窗口。只有你要求另一个对话执行时才切换到 Prompt Ready。多轮或中断需要时在现有任务记录中保存决定；无现有位置时使用 `.get-clear/<任务名>/requirements.md`。

完整流程见 [SKILL.md](SKILL.md)，提问方式见 [questioning.md](references/questioning.md)，演示见 [虚构网页返修](examples/landing-page.md)。纯文字访谈不能保证最终审美满意，最终仍要看实际作品。

本包独立包含方法、参考、依赖辅助脚本与 [MIT 许可](LICENSE)。不依赖作者的私人聊天、Clear Feedback 或另一套件目录。来源见 [SOURCES.md](SOURCES.md)。
