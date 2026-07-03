# Git 与 GitHub 操作文档

> 你可以把这个文件当作完整的操作手册，照着步骤做就能把代码推上 GitHub。

---

## 一、前提知识

### GitHub 是什么

远程代码仓库。代码放在 GitHub 的服务器上，别人可以下载，你 push 上传。

### Git 是什么

本地版本管理工具。记录每次改动，生成 commit（一个快照），再把 commit 推送到 GitHub。

### GitHub 怎么认出你提交的

Git 用 `user.email` 匹配 GitHub 账号。你提交时带了一个邮箱，GitHub 收到后去它的数据库查 —— 如果这个邮箱在你 GitHub 的 Verified Emails 里，就显示你的头像和用户名；否则显示灰色默认头像。

```bash
# 查看当前配置
git config user.name   # → Kris Lan
git config user.email  # → 必须和 GitHub 已绑定的邮箱一致
```

---

## 二、本项目的 Git 配置

```bash
cd /home/robot/bid_tool
git config user.name "Kris Lan"
git config user.email "你的GitHub验证邮箱"
```

### 确认你的邮箱

1. 打开 https://github.com/settings/emails
2. 看 Primary email address 是什么
3. 把它设为 user.email

---

## 三、完整提交流程

### 第 1 步：改代码

在 VSCode 里编辑文件，保存。

### 第 2 步：查看改动

```bash
git status          # 看哪些文件改了
git diff            # 看具体改了什么
```

输出示例：
```
修改：     desktop.py
新文件：   docs/new-file.md
```

### 第 3 步：添加到暂存区

```bash
git add -A          # 添加所有改动
# 或只加某个文件
git add desktop.py
```

### 第 4 步：提交

```bash
git commit -m "这里写一句话说明改了什么"
```

### 第 5 步：推送到 GitHub

```bash
git push
```

如果网络到 GitHub 被拒（经常发生在这台 VM 上），等几秒重试：
```bash
sleep 5 && git push
```

---

## 四、提交流程图解

```
你的代码改动
    ↓ git add
暂存区 (Stage)
    ↓ git commit
本地仓库 (.git/)
    ↓ git push
GitHub (远程仓库)
```

---

## 五、常用操作速查

| 操作 | 命令 |
|------|------|
| 查看状态 | `git status` |
| 查看改动 | `git diff` |
| 添加全部 | `git add -A` |
| 提交 | `git commit -m "说明"` |
| 推送 | `git push` |
| 看提交历史 | `git log --oneline` |
| 撤销未 add 的改动 | `git checkout -- 文件名` |
| 撤销 add | `git reset HEAD 文件名` |
| 丢弃所有本地改动 | `git checkout .` |
| 修改最后一次提交 | `git commit --amend` |

---

## 六、网络问题处理

这台 VM 到 GitHub 的网络不稳定，常见错误：

| 错误信息 | 处理 |
|---------|------|
| `GnuTLS recv error (-54)` | 网络波动，`sleep 5 && git push` 重试 |
| `Failed to connect to github.com` | 同上，等 5 秒重试 |
| `could not read Username` | Git 凭据过期，用 `gh auth setup-git` 重新授权 |
| `403 / 401` | Token 权限不足或过期 |

---

## 七、Token 管理

### 什么是 Personal Access Token

你的 GitHub 密码不能直接用在命令行 git push 里。Token 是替代密码用的——一个长字符串，只能用在 CLI 环境。

### 创建 Token

1. 打开 https://github.com/settings/tokens
2. → Generate new token (classic)
3. 勾选 `repo` 和 `workflow`
4. 设置过期（7-30 天）
5. 生成后复制保存

### Token 过期怎么办

重新生成一个，然后在 VM 里更新凭据文件。

---

## 八、本项目用过的 Token 记录

| 用途 | 说明 |
|------|------|
| 第 1 个 | `ghp_jmVzb5...` — 只有 repo 权限，不能创建 workflow |
| 第 2 个 | `ghp_UWs84s...` — 加了 workflow 权限 |

这些 Token 现在都已过期或删除。你需要用的时候重新生成。

---

## 九、常见问题 FAQ

**Q: 为什么 push 时说 "refusing to allow a Personal Access Token to create or update workflow"？**

A: Token 没勾选 `workflow` 权限。重新生成 Token 时勾上。

**Q: 为什么 push 上去后还是灰色头像？**

A: `git config user.email` 和你 GitHub 验证邮箱不匹配。

**Q: 怎么修改已经 push 的 commit 信息？**

A: `git commit --amend --reset-author` 然后 `git push --force`（危险，不推荐）。

**Q: Claude Code 能不能替我 push？**

A: 能，但有安全限制——Token 不能明文出现在命令行里。需要存为凭据文件。
