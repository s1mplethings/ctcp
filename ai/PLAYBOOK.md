# PLAYBOOK (Scan → Diagnose → Apply → Verify → Record)

## 目标
把“成功修改”变成 **可复用 recipe**，从而对任何项目做到：
1) 扫描项目结构 → 找到问题（findings）
2) 匹配预设 recipe → 自动生成 patch
3) 校验/验证 → 输出迁移包（zip）
4) 记录经验 → 下次直接套用

---

## 流程图
```
[Select Target Repo]
        |
        v
[Scan Repo] -> report.json / report.md
        |
        v
[Diagnose + Recommend Recipes]
        |
        v
[Resolve Tokens (paths/names)]
        |
        v
[Build Patch Bundle]
        |
        v
[Apply (optional) + Verify]
        |
        v
[Record as Recipe + Update Index]
```

---

## 关键对象
- **Detector**：从 repo 扫描出 findings（问题/特征）并给出建议 recipes。
- **Recipe**：可套用预设（适用条件、锚点、patch、verify）。
- **Bundle**：对外输出的标准包：report + plan + patches + verify/rollback。

---

## 你要实现“把成功案例复制到别的项目上”的最小闭环（MVP）
- 具备 scan + bundle 两个命令
- recipe 先从结构相似项目开始（不用复杂 token）
- 输出 zip，外部项目能直接 `git apply` 或复制文件使用
