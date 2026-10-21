# 可选的宿主接入规则

规则与安装步骤都随完整 `get-clear` 文件夹提供，单独安装该 Skill 也能使用：

- [可复制的规则片段](../skills/get-clear/assets/agents-snippet.md)
- [接入、验证与撤销步骤](../skills/get-clear/references/host-integration.md)

由使用者选择项目或用户范围，保留原有指令并合并本段。复制 Skill 文件夹不会自动写入全局配置。

这把技能读取接入宿主的日常工作规则，避免仅依靠技能描述参与可选匹配。它仍依赖宿主实际加载并遵循指令，不能宣称所有未来运行必然成功。验证时必须区分“只安装 Skill”和“Skill 加宿主规则”，不混报自动选择结果。
