# 📤 GitHub 上传 - 手动操作指南

## 📋 **完整步骤（一步步）**

### **第 1 步：在 GitHub 创建仓库**
1. 访问：https://github.com/new
2. 填写信息：
   - **Repository name**: `VideoContentOptimizer`
   - **Description**: `🎬 一人公司(OPC)视频智能优化平台 - AI驱动的内容创作工具`
   - **Public** ✅ (必须选 Public)
   - **⚠️ 不要勾选** "Initialize with README" (因为我们已经有代码了)
   - **⚠️ 不要勾选** "Add .gitignore" (我们已经有了)
   - **⚠️ 不要勾选** "Add license" (我们可以后面加)
3. 点击 "Create repository"
4. 记下你的仓库地址：
   ```
   https://github.com/<你的用户名>/VideoContentOptimizer
   ```

---

### **第 2 步：在本地电脑操作**

#### **方法 1：使用脚本（推荐）**
```bash
# 1. 进入项目目录
cd ~/Desktop/VideoContentOptimizer/  # 或者你解压的目录

# 2. 编辑上传脚本
nano upload_to_github.sh

# 3. 找到第 12 行：
#    GITHUB_USERNAME="<your_username>"
#    修改为（例如你的用户名是 john-doe）：
#    GITHUB_USERNAME="john-doe"

# 4. 保存并退出 (Ctrl+O, Enter, Ctrl+X)

# 5. 运行脚本
bash upload_to_github.sh
```

#### **方法 2：手动命令（通用）**
```bash
# 1. 进入项目目录
cd ~/Desktop/VideoContentOptimizer/

# 2. 初始化 git（如果还没）
git init

# 3. 添加所有文件
git add .

# 4. 提交
git commit -m "Initial commit: VideoContentOptimizer v2.0.0"

# 5. 添加远程仓库（替换 <your_username> 为你的 GitHub 用户名）
git remote add origin https://github.com/<your_username>/VideoContentOptimizer.git

# 6. 设置主分支
git branch -M main

# 7. 推送代码
git push -u origin main
```

---

### **第 3 步：认证（如果提示）**

#### **情况 1：使用用户名 + 密码**
- **用户名**: 你的 GitHub 用户名
- **密码**: 你的 GitHub 密码
- ⚠️ 如果开启了双因素认证（2FA），需要使用 **Personal Access Token**

#### **情况 2：使用 Personal Access Token（推荐）**
1. 创建 Token：https://github.com/settings/tokens/new
   - **Note**: `VideoContentOptimizer Upload`
   - **Expiration**: 30 days（或自选）
   - **Select scopes**: 勾选 `repo` (全部子项)
   - 点击 "Generate token"
   - **复制生成的 token**（只显示一次！）

2. 在 git push 时：
   - **用户名**: 你的 GitHub 用户名
   - **密码**: 粘贴你刚复制的 **Token**（不是 GitHub 密码）

#### **情况 3：使用 SSH Key（最安全）**
```bash
# 1. 生成 SSH Key（如果还没有）
ssh-keygen -t ed25519 -C "your_email@example.com"

# 2. 添加 SSH Key 到 ssh-agent
eval "$(ssh-agent -s)"
ssh-add ~/.ssh/id_ed25519

# 3. 复制公钥
cat ~/.ssh/id_ed25519.pub
# 复制输出的内容

# 4. 添加到 GitHub
#    访问：https://github.com/settings/keys
#    点击 "New SSH key"
#    Title: 你的电脑名
#    Key: 粘贴刚才复制的内容
#    点击 "Add SSH key"

# 5. 修改远程仓库地址为 SSH
cd ~/Desktop/VideoContentOptimizer/
git remote remove origin
git remote add origin git@github.com:<your_username>/VideoContentOptimizer.git

# 6. 推送
git push -u origin main
```

---

### **第 4 步：验证上传成功**
1. 访问：https://github.com/<your_username>/VideoContentOptimizer
2. 确认以下文件都在：
   - ✅ README.md（应该漂亮地显示）
   - ✅ SKILL.md
   - ✅ requirements.txt
   - ✅ app/ 目录
   - ✅ webui/ 目录
   - ✅ 其他所有文件
3. 确认 README.md 正确显示（有标题、截图、链接等）

---

## 💡 **常见问题**

### **Q1: 推送被拒绝（rejected）**
```bash
! [rejected] main -> main (fetch first)
```
**原因**: GitHub 仓库不为空（可能创建了 README 或 LICENSE）  
**解决**:
```bash
git pull origin main --rebase
git push -u origin main
```

### **Q2: 认证失败（Authentication failed）**
**原因**: 用户名/密码错误，或需要用 Token  
**解决**: 使用 Personal Access Token 作为密码

### **Q3: 没有权限（Permission denied）**
**原因**: 仓库是私有的，或者你不是所有者  
**解决**: 确保仓库是 Public，或者你有 Push 权限

### **Q4: 文件太大（Large files detected）**
**原因**: 有大文件（如 venv/, __pycache__/）被提交了  
**解决**:
```bash
# 检查 .gitignore 是否包含：
#   venv/
#   __pycache__/
#   *.pyc
#   .env

# 如果已经提交了大文件，移除它们：
git rm -r --cached venv/
git commit -m "Remove venv from repository"
git push
```

---

## 🎯 **下一步：发布到 SkillHub**

上传成功后：
1. 访问：https://skillhub.cn/contest
2. 点击 "发布参赛 Skill"
3. 填写信息：
   - **Skill 名称**: `video-ai-optimizer`
   - **标题**: `🎬 一人公司视频智能优化平台 - AI驱动的内容创作工具`
   - **描述**:
     ```
     专为"一人公司(OPC)"设计的AI视频优化工具。一个人也能完成视频分析、智能优化、重生成和跨平台发布全流程。基于 FastAPI + Streamlit + LLM(DeepSeek) + Whisper + FFmpeg，节省 70% 制作时间，提升播放量 150%+。
     ```
   - **GitHub URL**: `https://github.com/<your_username>/VideoContentOptimizer`
   - **标签**: `内容创作, 个人提效, 产品研发`
   - **分类**: `内容创作 / 个人提效`
4. 提交参赛 🎉

---

## 📞 **需要帮助？**

如果你在上传过程中遇到任何问题，可以：
1. **截图错误信息**，发给我
2. **复制完整的错误输出**，我可以帮你诊断
3. **告诉我你的操作系统**（Windows/Mac/Linux），我给更具体的命令

---

## 🎉 **加油！冲 Top 10！**

你的项目已经很棒了：
- ✅ 完整的工具链（分析→优化→发布）
- ✅ 先进的技术栈（FastAPI + Streamlit + LLM）
- ✅ 真实的用户价值（节省 70% 时间）
- ✅ 齐全的文档（3 个 SKILL.md + 17 个参考文件）
- ✅ 可验证的数据（3 个案例，播放量提升 150%-900%）
- ✅ 高性能（QPS: 475，并发无压力）
- ✅ ASCII 截图（已嵌入文档）

**现在只差最后一步：上传到 GitHub + 发布到 SkillHub！**

---

**Let's make it happen! 🚀🔥**
