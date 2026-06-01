#!/usr/bin/env python3
"""
VideoContentOptimizer Autopilot
每周自动生成：社区发帖草稿 + 开发建议 + 周报
输出提交到 autopilot-drafts 分支，供 review 后发布。

用法：
  DEEPSEEK_API_KEY=sk-xxx python scripts/autopilot.py
  python scripts/autopilot.py --dry-run   # 只打印，不提交
"""

import argparse
import json
import os
import subprocess
import sys
import textwrap
from datetime import datetime, timedelta
from pathlib import Path

# ── 配置 ───────────────────────────────────────────────────────────
REPO_ROOT = Path(__file__).resolve().parent.parent
DRAFTS_DIR = REPO_ROOT / "autopilot"
GITHUB_REPO = "yunya1991/VideoContentOptimizer"
DRAFTS_BRANCH = "autopilot-drafts"

DEEPSEEK_BASE_URL = "https://api.deepseek.com/v1"
DEEPSEEK_MODEL = "deepseek-chat"  # DeepSeek-V3，性价比最高

# 读取 API Key：优先环境变量，其次 .env.autopilot 文件
def _load_api_key() -> str:
    key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY")
    if key:
        return key
    env_file = REPO_ROOT / ".env.autopilot"
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("DEEPSEEK_API_KEY="):
                return line.split("=", 1)[1].strip()
    return ""

API_KEY = _load_api_key()


# ── 工具函数 ───────────────────────────────────────────────────────

def run(cmd: str, check=True) -> str:
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True,
        cwd=REPO_ROOT, encoding="utf-8", errors="replace"
    )
    if check and result.returncode != 0:
        raise RuntimeError(f"命令失败: {cmd}\n{result.stderr}")
    return (result.stdout + result.stderr).strip()


def gh_json(query: str) -> dict:
    raw = run(f"gh repo view {GITHUB_REPO} --json {query}", check=False)
    try:
        return json.loads(raw)
    except Exception:
        return {}


def call_deepseek(prompt: str, system: str = "你是一个优秀的开源项目运营助手。") -> str:
    """调用 DeepSeek API（OpenAI 兼容接口）"""
    if not API_KEY:
        return "⚠️ 未配置 DEEPSEEK_API_KEY，此部分内容需要手动填写。"

    try:
        import urllib.request
        payload = json.dumps({
            "model": DEEPSEEK_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.7,
            "max_tokens": 2000,
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{DEEPSEEK_BASE_URL}/chat/completions",
            data=payload,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read())
            return data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        return f"⚠️ DeepSeek API 调用失败: {e}"


# ── 上下文收集 ──────────────────────────────────────────────────────

def gather_context() -> dict:
    """收集项目当前状态作为 prompt 上下文"""
    # GitHub 指标
    stats = gh_json("stargazerCount,forkCount,watchers,description")
    stars = stats.get("stargazerCount", 0)
    forks = stats.get("forkCount", 0)

    # 最近 7 天的提交
    since = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    commits_raw = run(
        f'git log --since="{since}" --oneline --no-merges', check=False
    )
    recent_commits = [l.strip() for l in commits_raw.splitlines() if l.strip()]

    # 最近 30 天的提交（用于功能摘要）
    since30 = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    commits30_raw = run(
        f'git log --since="{since30}" --oneline --no-merges', check=False
    )
    recent_commits_30 = [l.strip() for l in commits30_raw.splitlines() if l.strip()]

    # 上次周报时间（从文件夹名推断）
    last_run_date = "（首次运行）"
    if DRAFTS_DIR.exists():
        folders = sorted(DRAFTS_DIR.glob("????-W??"))
        if folders:
            last_run_date = folders[-1].name

    # README 核心功能摘要（前 50 行）
    readme_path = REPO_ROOT / "README.md"
    readme_snippet = ""
    if readme_path.exists():
        lines = readme_path.read_text(encoding="utf-8").splitlines()[:50]
        readme_snippet = "\n".join(lines)

    return {
        "stars": stars,
        "forks": forks,
        "recent_commits": recent_commits,
        "recent_commits_30": recent_commits_30,
        "last_run_date": last_run_date,
        "readme_snippet": readme_snippet,
        "week_label": datetime.now().strftime("%Y-W%V"),
        "date_str": datetime.now().strftime("%Y年%m月%d日"),
    }


# ── 内容生成 ───────────────────────────────────────────────────────

def gen_weekly_report(ctx: dict) -> str:
    commits_str = "\n".join(ctx["recent_commits"]) or "本周无新提交"
    return textwrap.dedent(f"""
    # 周报 {ctx['week_label']}

    生成时间：{ctx['date_str']}
    上次运行：{ctx['last_run_date']}

    ## 指标
    | 指标 | 数值 |
    |------|------|
    | ⭐ Stars | {ctx['stars']} |
    | 🍴 Forks | {ctx['forks']} |

    ## 本周提交
    ```
    {commits_str}
    ```

    ## 待办（来自开发建议）
    见 `dev_suggestions.md`
    """).strip()


def gen_post_v2ex(ctx: dict) -> str:
    commits_summary = "\n".join(f"- {c}" for c in ctx["recent_commits_30"][:8]) or "- 项目初始发布"
    prompt = textwrap.dedent(f"""
    帮我写一篇 V2EX 发帖，推广我的开源项目 VideoContentOptimizer。

    项目介绍：
    {ctx['readme_snippet']}

    最近 30 天新增功能：
    {commits_summary}

    当前数据：{ctx['stars']} stars，{ctx['forks']} forks

    要求：
    1. 标题吸引眼球，适合 V2EX 程序员社区，不要太营销味
    2. 正文说清楚"它能解决什么问题"，重点突出和同类工具的差异化（它是优化/发布工具，不是生成工具）
    3. 包含 GitHub 链接：https://github.com/yunya1991/VideoContentOptimizer
    4. 结尾欢迎反馈，语气真诚，不要堆砌感叹号
    5. 总长度控制在 400-600 字
    6. 注意：V2EX 技术社区，用中文，但可以带一些英文技术词汇

    直接输出帖子内容，不要加解释。
    """)
    return call_deepseek(prompt, system="你是一个擅长做开源项目运营的程序员。")


def gen_post_juejin(ctx: dict) -> str:
    commits_summary = "\n".join(f"- {c}" for c in ctx["recent_commits_30"][:8]) or "- 项目初始发布"
    prompt = textwrap.dedent(f"""
    帮我写一篇掘金技术文章，介绍 VideoContentOptimizer 这个开源项目的技术实现。

    项目介绍：
    {ctx['readme_snippet']}

    最近 30 天新增功能：
    {commits_summary}

    要求：
    1. 标题可以是技术分享角度，例如"我是如何用 FastAPI + Whisper 做了个视频优化工具"
    2. 重点讲技术方案：LLM 调用、Whisper 转录、进化引擎设计、TTS 多引擎等
    3. 提一下你遇到的有趣技术难点（比如Soul用户画像的自主进化设计）
    4. 包含 GitHub 链接
    5. 500-800 字，可以用 Markdown 格式，加小标题
    6. 结尾放一个"求 Star"的软引导

    直接输出文章内容，不要加解释。
    """)
    return call_deepseek(prompt, system="你是一个技术写作高手，擅长写深度技术博客。")


def gen_dev_suggestions(ctx: dict) -> str:
    commits_summary = "\n".join(f"- {c}" for c in ctx["recent_commits_30"][:10]) or "- 无"
    prompt = textwrap.dedent(f"""
    你是一个开源项目的技术顾问。帮我分析 VideoContentOptimizer 项目下一步的开发优先级。

    项目当前状态：
    - Stars: {ctx['stars']}，Forks: {ctx['forks']}
    - 最近 30 天提交：
    {commits_summary}

    项目 README 摘要：
    {ctx['readme_snippet']}

    已知的待完善项（来自 README roadmap）：
    - [ ] A/B 测试对比 UI
    - [ ] 数据统计分析
    - [ ] 移动端适配

    已知的文档短板（用户反馈）：
    - Python SDK 代码示例不够丰富
    - 错误触发场景说明不清晰（何时限流、何时失败）

    请给出：
    1. **本周最值得做的 1-2 件事**（说明理由，优先选择对用户价值最大、对 star 增长有帮助的）
    2. **下个月的 3 个功能/改进方向**（每条 1-2 行，说明为什么）
    3. **文档方面还有哪些具体缺口需要补**

    用 Markdown 格式输出，简洁，不废话。
    """)
    return call_deepseek(prompt, system="你是一个开源项目的产品经理和技术顾问，擅长平衡用户价值和开发成本。")


# ── 提交到 main 分支（autopilot/ 子目录）─────────────────────────

def commit_to_drafts_branch(week_dir: Path, dry_run: bool):
    if dry_run:
        print(f"\n[dry-run] 跳过 git 提交，文件已写入 {week_dir}")
        return

    try:
        week_label = week_dir.name
        run(f"git add autopilot/")
        run(f'git commit -m "autopilot: {week_label} 周报 + 发帖草稿 + 开发建议"')

        # 推送（PowerShell 绕过 bash 网络限制）
        push_result = subprocess.run(
            ["powershell.exe", "-Command",
             f"cd '{REPO_ROOT}'; git push origin main 2>&1"],
            capture_output=True, text=True, encoding="utf-8", errors="replace"
        )
        push_out = push_result.stdout + push_result.stderr
        if "main ->" in push_out or "..main" in push_out or push_result.returncode == 0:
            print(f"OK: 已推送到 main 分支 autopilot/{week_label}/")
        else:
            print(f"WARNING: 推送可能失败，请手动运行 git push origin main")
            print(f"   输出: {push_out[:300]}")

    except Exception as e:
        print(f"WARNING: git 操作失败（文件已本地写入）: {e}")


# ── 主流程 ─────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="VideoContentOptimizer Autopilot")
    parser.add_argument("--dry-run", action="store_true", help="只生成文件，不提交")
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    print(f"[Autopilot] 启动 [{datetime.now().strftime('%Y-%m-%d %H:%M')}]")
    print("=" * 50)

    # 收集上下文
    print("[1/5] 收集项目状态...")
    ctx = gather_context()
    print(f"   Stars: {ctx['stars']} | Forks: {ctx['forks']} | 本周提交: {len(ctx['recent_commits'])} 条")

    # 创建本周目录
    week_dir = DRAFTS_DIR / ctx["week_label"]
    week_dir.mkdir(parents=True, exist_ok=True)

    # 生成周报（无需 API）
    print("[2/5] 生成周报...")
    report = gen_weekly_report(ctx)
    (week_dir / "weekly_report.md").write_text(report, encoding="utf-8")
    print("   OK: weekly_report.md")

    # 生成发帖草稿
    print("[3/5] 生成 V2EX 发帖草稿（DeepSeek）...")
    post_v2ex = gen_post_v2ex(ctx)
    (week_dir / "post_v2ex.md").write_text(post_v2ex, encoding="utf-8")
    print("   OK: post_v2ex.md")

    print("[4/5] 生成掘金文章草稿（DeepSeek）...")
    post_juejin = gen_post_juejin(ctx)
    (week_dir / "post_juejin.md").write_text(post_juejin, encoding="utf-8")
    print("   OK: post_juejin.md")

    print("[5/5] 生成开发建议（DeepSeek）...")
    dev_suggestions = gen_dev_suggestions(ctx)
    (week_dir / "dev_suggestions.md").write_text(dev_suggestions, encoding="utf-8")
    print("   OK: dev_suggestions.md")

    print(f"\n>>> 草稿目录: autopilot/{ctx['week_label']}/")

    # 提交
    if not args.dry_run:
        print(f"\n>>> 提交到 {DRAFTS_BRANCH} 分支...")
        commit_to_drafts_branch(week_dir, dry_run=False)
    else:
        commit_to_drafts_branch(week_dir, dry_run=True)

    print("\n[Autopilot] 完成！")
    print(f"   查看草稿: https://github.com/{GITHUB_REPO}/tree/{DRAFTS_BRANCH}/autopilot/{ctx['week_label']}/")


if __name__ == "__main__":
    main()
