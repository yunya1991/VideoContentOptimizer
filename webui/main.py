"""
Streamlit Web UI 主应用
"""

import os
import sys
import json
import streamlit as st
import requests

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# API 配置
API_URL = os.environ.get("API_URL", "http://localhost:8080")

# 页面配置
st.set_page_config(
    page_title="视频AI优化器",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded",
)


def main():
    """主函数"""
    st.title("🎬 Video AI Optimizer")
    st.markdown("### 智能视频分析与优化平台")

    # 侧边栏
    st.sidebar.title("功能导航")
    page = st.sidebar.radio(
        "选择功能",
        ["📊 视频分析", "🧠 智能优化", "🎬 视频重生成", "ℹ️ 关于"],
    )

    # 检查 API 状态
    if not _check_api():
        st.sidebar.error(f"⚠️ API 服务未连接 ({API_URL})")
        st.sidebar.info("请先启动 API 服务:\n```\nuvicorn app.main:app --port 8080\n```")
    else:
        st.sidebar.success(f"✅ API 已连接")

    # 页面路由
    if page == "📊 视频分析":
        show_analysis_page()
    elif page == "🧠 智能优化":
        show_optimization_page()
    elif page == "🎬 视频重生成":
        show_regeneration_page()
    elif page == "ℹ️ 关于":
        show_about_page()


def _check_api() -> bool:
    """检查 API 服务是否可用"""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=5)
        return resp.status_code == 200
    except (requests.ConnectionError, requests.Timeout, Exception):
        return False


def show_analysis_page():
    """视频分析页面 — 调用真实 API"""
    st.header("📊 视频分析")
    st.info("上传视频，自动分析内容、识别意图、评估质量")

    uploaded_file = st.file_uploader(
        "上传视频文件",
        type=["mp4", "mov", "avi", "mkv"],
        help="支持 MP4, MOV, AVI, MKV 格式",
    )

    if uploaded_file is not None:
        st.video(uploaded_file)
        file_size_mb = uploaded_file.size / (1024 * 1024)
        st.caption(f"📁 {uploaded_file.name} ({file_size_mb:.1f} MB)")

        if st.button("🚀 开始分析", type="primary"):
            with st.spinner("📋 正在分析视频，请稍候..."):
                try:
                    # 调用真实 API
                    files = {"video": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    resp = requests.post(
                        f"{API_URL}/api/v2/analyzer/analyze",
                        files=files,
                        params={"extract_keywords": True, "predict_trend": True},
                        timeout=120,
                    )

                    if resp.status_code == 200:
                        data = resp.json()

                        # 缓存到 session_state 供优化页面使用
                        st.session_state["analysis_result"] = data

                        _render_analysis_result(data)
                        st.success("✅ 分析完成！")
                    else:
                        error = resp.json().get("detail", resp.text)
                        st.error(f"❌ 分析失败: {error}")

                except requests.ConnectionError:
                    st.error("❌ 无法连接到 API 服务，请确认服务已启动")
                except requests.Timeout:
                    st.error("❌ 请求超时，视频分析可能需要较长时间")
                except Exception as e:
                    st.error(f"❌ 未知错误: {e}")

    # 如果有缓存结果，也展示
    elif "analysis_result" in st.session_state:
        st.info("📌 显示上次分析结果")
        _render_analysis_result(st.session_state["analysis_result"])


def _render_analysis_result(data: dict):
    """渲染分析结果"""
    # 元数据
    metadata = data.get("metadata")
    if metadata:
        st.subheader("📹 视频元数据")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⏱️ 时长", f"{metadata.get('duration', 0):.1f}秒")
        with col2:
            st.metric("📐 分辨率", metadata.get("resolution", "N/A"))
        with col3:
            st.metric("🎞️ 帧率", f"{metadata.get('fps', 0)} FPS")
        with col4:
            size_mb = (metadata.get("file_size") or 0) / (1024 * 1024)
            st.metric("📁 大小", f"{size_mb:.1f} MB" if size_mb > 0 else "N/A")

    # 转录文本
    transcript = data.get("transcript")
    if transcript:
        st.subheader("📝 音频转录")
        st.text_area("转录文本", transcript, height=150)

    # 意图识别
    intent = data.get("intent")
    if intent:
        st.subheader("🎯 视频意图")
        col1, col2 = st.columns(2)
        with col1:
            st.info(f"**分类**: {intent.get('category', 'N/A')}")
            st.info(f"**子类别**: {intent.get('sub_category', 'N/A')}")
        with col2:
            st.info(f"**情感基调**: {intent.get('emotion', 'N/A')}")
            st.info(f"**置信度**: {intent.get('confidence', 0) * 100:.0f}%")

    # 质量评分
    quality = data.get("quality_score")
    if quality:
        st.subheader("⭐ 质量评分")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("制作质量", f"{quality.get('production_quality', 0):.1f}/10")
        with col2:
            st.metric("互动潜力", f"{quality.get('engagement_potential', 0):.1f}/10")
        with col3:
            st.metric("原创度", f"{quality.get('originality', 0):.1f}/10")
        with col4:
            overall = quality.get("overall_score") or 0
            st.metric("综合评分", f"{overall:.1f}/10")


_PLATFORM_LABELS = {"douyin": "抖音", "xiaohongshu": "小红书", "weixin": "微信视频号"}
_GOAL_LABELS = {"engagement": "互动提升", "ctr": "点击率(CTR)", "brand": "品牌建设", "viral": "传播裂变"}
_TONE_LABELS = {"energetic": "活泼有趣", "professional": "专业干货", "casual": "生活日常", "emotional": "情感共鸣"}

_DEFAULT_PARAMS = {
    "target_platform": "douyin",
    "optimization_goal": "engagement",
    "tone": "energetic",
    "num_variants": 5,
    "optimization_types": ["script", "title"],
}


def _record_param_choice(
    optimization_id: str,
    interaction_mode: str,
    chosen_profile_id,
    was_ai_recommended: bool,
    final_params: dict,
):
    """fire-and-forget：失败静默，不阻塞主优化流程"""
    try:
        requests.post(
            f"{API_URL}/api/v2/optimizer/record-param-choice",
            json={
                "optimization_id": optimization_id,
                "interaction_mode": interaction_mode,
                "chosen_profile_id": chosen_profile_id,
                "was_ai_recommended": was_ai_recommended,
                "final_params": final_params,
            },
            timeout=5,
        )
    except Exception:
        pass


def show_optimization_page():
    """智能优化页面 — 询问模式（单视频）+ 执行模式（批量）"""
    st.header("🧠 智能优化")

    # 模式切换
    mode = st.radio(
        "选择处理模式",
        ["📝 单视频（询问模式）", "📦 批量处理（执行模式）"],
        horizontal=True,
        key="opt_mode_radio",
    )
    st.session_state["opt_mode"] = "inquiry" if "单视频" in mode else "execution"

    st.divider()

    if st.session_state["opt_mode"] == "inquiry":
        _show_inquiry_mode()
    else:
        _show_execution_mode()


def _show_inquiry_mode():
    """单视频询问模式：Step 1 参数确认 → 执行优化"""
    analysis = st.session_state.get("analysis_result", {})
    default_transcript = analysis.get("transcript", "")

    transcript = st.text_area(
        "📝 视频转录文本 / 原始文案",
        value=default_transcript,
        height=120,
        help="可直接输入文案，或从视频分析页面自动获取转录文本",
        key="inquiry_transcript",
    )

    if not transcript.strip():
        st.info("请先输入文案，再进行参数配置")
        return

    st.markdown("#### Step 1 · 请选择参数配置方式")
    interaction = st.radio(
        "配置方式",
        ["🎴 推荐卡片（省力，AI 生成方向供选择）", "⚙️ 参数表单（精细，手动调整）"],
        key="opt_interaction_radio",
        label_visibility="collapsed",
    )
    is_cards = "推荐卡片" in interaction

    if is_cards:
        st.caption(
            "⚠️ 推荐卡片需额外调用 LLM，多消耗约 500–1000 tokens。"
            "若 LLM 不可用，将自动降级为 3 个预置方向。"
        )

    # 获取/生成参数
    params = _get_inquiry_params(transcript, is_cards, analysis)
    if params is None:
        return  # 用户尚未确认

    # 确认后展示参数摘要 + 执行按钮
    st.markdown("#### Step 2 · 确认后开始优化")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("目标平台", _PLATFORM_LABELS.get(params["target_platform"], params["target_platform"]))
    with col2:
        st.metric("优化目标", _GOAL_LABELS.get(params["optimization_goal"], params["optimization_goal"]))
    with col3:
        st.metric("内容调性", _TONE_LABELS.get(params["tone"], params["tone"]))
    with col4:
        st.metric("标题变体数", params["num_variants"])

    if st.button("🚀 开始优化", type="primary", use_container_width=True, key="inquiry_run"):
        st.session_state["last_opt_params"] = params
        _run_optimization(transcript, params)


def _get_inquiry_params(transcript: str, is_cards: bool, analysis: dict):
    """
    询问模式下获取确认的参数。
    推荐卡片路径：调 API 得到 3 张卡，用户点选后返回 params dict。
    参数表单路径：展示表单，用户确认后返回 params dict。
    未确认时返回 None。
    """
    if is_cards:
        return _show_profile_cards(transcript, analysis)
    else:
        return _show_params_form()


def _show_profile_cards(transcript: str, analysis: dict):
    """展示 AI 推荐卡片，用户点选后返回对应 params"""
    if "opt_profiles" not in st.session_state:
        st.session_state["opt_profiles"] = None

    if st.button("✨ 生成推荐方向", key="gen_profiles"):
        with st.spinner("AI 正在分析内容并生成推荐方向..."):
            try:
                intent = analysis.get("intent")
                payload = {
                    "transcript": transcript,
                    "keywords": [k.get("keyword", "") for k in analysis.get("keywords", [])],
                }
                if intent:
                    payload["intent"] = intent
                resp = requests.post(
                    f"{API_URL}/api/v2/optimizer/suggest-params",
                    json=payload,
                    timeout=30,
                )
                if resp.status_code == 200:
                    st.session_state["opt_profiles"] = resp.json()
                else:
                    st.error(f"生成推荐失败: {resp.json().get('detail', resp.text)}")
                    return None
            except requests.ConnectionError:
                st.error("❌ 无法连接到 API 服务")
                return None

    profiles_data = st.session_state.get("opt_profiles")
    if not profiles_data:
        return None

    profiles = profiles_data.get("profiles", [])
    default_idx = profiles_data.get("default_index", 0)

    st.markdown("**AI 根据你的内容推荐了以下 3 个优化方向，请选择一个：**")

    cols = st.columns(3)
    selected_params = None
    for i, (col, profile) in enumerate(zip(cols, profiles)):
        with col:
            is_default = i == default_idx
            border_style = "border: 2px solid #ff4b4b;" if is_default else "border: 1px solid #ddd;"
            label = f"{'⭐ 推荐 · ' if is_default else ''}{profile['name']}"
            st.markdown(
                f"<div style='{border_style} border-radius:8px; padding:12px; margin-bottom:8px;'>"
                f"<b>{profile['name']}</b><br/>"
                f"<small>{profile['description']}</small><br/><br/>"
                f"<i>💡 {profile['why']}</i>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if st.button(f"选择此方向", key=f"pick_profile_{i}", use_container_width=True):
                st.session_state["opt_params"] = profile["params"]
                st.session_state["opt_profiles"] = None
                import time
                _record_param_choice(
                    optimization_id=f"opt_ui_{int(time.time())}",
                    interaction_mode="cards",
                    chosen_profile_id=profile.get("id"),
                    was_ai_recommended=(i == default_idx),
                    final_params=profile["params"],
                )

    if "opt_params" in st.session_state and st.session_state["opt_params"]:
        return st.session_state.pop("opt_params")
    return None


def _show_params_form():
    """展示参数表单，用户确认后返回 params dict"""
    last = st.session_state.get("last_opt_params", _DEFAULT_PARAMS)

    col1, col2 = st.columns(2)
    with col1:
        platform = st.selectbox(
            "📱 目标平台",
            list(_PLATFORM_LABELS.keys()),
            index=list(_PLATFORM_LABELS.keys()).index(last.get("target_platform", "douyin")),
            format_func=lambda x: _PLATFORM_LABELS[x],
            key="form_platform",
        )
        goal = st.selectbox(
            "🎯 优化目标",
            list(_GOAL_LABELS.keys()),
            index=list(_GOAL_LABELS.keys()).index(last.get("optimization_goal", "engagement")),
            format_func=lambda x: _GOAL_LABELS[x],
            key="form_goal",
        )
    with col2:
        tone = st.selectbox(
            "🎨 内容调性",
            list(_TONE_LABELS.keys()),
            index=list(_TONE_LABELS.keys()).index(last.get("tone", "energetic")),
            format_func=lambda x: _TONE_LABELS[x],
            key="form_tone",
        )
        num_variants = st.slider("📝 标题变体数", 1, 8, last.get("num_variants", 5), key="form_variants")

    opt_types = []
    c1, c2 = st.columns(2)
    with c1:
        if st.checkbox("✍️ 文案优化", value="script" in last.get("optimization_types", ["script", "title"]), key="form_script"):
            opt_types.append("script")
    with c2:
        if st.checkbox("📝 标题生成", value="title" in last.get("optimization_types", ["script", "title"]), key="form_title"):
            opt_types.append("title")

    if st.button("✅ 确认参数", key="confirm_form"):
        import time
        confirmed = {
            "target_platform": platform,
            "optimization_goal": goal,
            "tone": tone,
            "num_variants": num_variants,
            "optimization_types": opt_types or ["script", "title"],
        }
        _record_param_choice(
            optimization_id=f"opt_ui_{int(time.time())}",
            interaction_mode="form",
            chosen_profile_id=None,
            was_ai_recommended=False,
            final_params=confirmed,
        )
        return confirmed
    return None


def _show_execution_mode():
    """批量执行模式：可选参数预设，多行文案批量优化"""
    last = st.session_state.get("last_opt_params", _DEFAULT_PARAMS)
    # 预设默认值，expander 内部控件赋值后覆盖
    batch_params = dict(last)

    with st.expander("⚙️ 批量参数预设（可选，收起时使用默认值）", expanded=False):
        col1, col2 = st.columns(2)
        with col1:
            platform = st.selectbox(
                "📱 目标平台",
                list(_PLATFORM_LABELS.keys()),
                index=list(_PLATFORM_LABELS.keys()).index(last.get("target_platform", "douyin")),
                format_func=lambda x: _PLATFORM_LABELS[x],
                key="batch_platform",
            )
            goal = st.selectbox(
                "🎯 优化目标",
                list(_GOAL_LABELS.keys()),
                index=list(_GOAL_LABELS.keys()).index(last.get("optimization_goal", "engagement")),
                format_func=lambda x: _GOAL_LABELS[x],
                key="batch_goal",
            )
        with col2:
            tone = st.selectbox(
                "🎨 内容调性",
                list(_TONE_LABELS.keys()),
                index=list(_TONE_LABELS.keys()).index(last.get("tone", "energetic")),
                format_func=lambda x: _TONE_LABELS[x],
                key="batch_tone",
            )
            num_variants = st.slider("📝 标题变体数", 1, 8, last.get("num_variants", 5), key="batch_variants")
        batch_params = {
            "target_platform": platform,
            "optimization_goal": goal,
            "tone": tone,
            "num_variants": num_variants,
            "optimization_types": ["script", "title"],
        }

    st.markdown("#### 输入批量文案")
    st.caption("每行一段独立文案，空行自动忽略")
    raw_text = st.text_area(
        "批量文案输入",
        height=200,
        placeholder="第一段文案内容...\n第二段文案内容...\n第三段文案内容...",
        key="batch_transcripts",
        label_visibility="collapsed",
    )

    transcripts = [line.strip() for line in raw_text.splitlines() if line.strip()]
    if transcripts:
        st.caption(f"已识别 {len(transcripts)} 段文案")

    if st.button("🚀 批量执行", type="primary", use_container_width=True, key="batch_run", disabled=not transcripts):
        if not transcripts:
            st.warning("⚠️ 请输入至少一段文案")
            return
        st.session_state["last_opt_params"] = batch_params
        _run_batch_optimization(transcripts, batch_params)


def _run_optimization(transcript: str, params: dict):
    """执行单次优化并渲染结果"""
    with st.spinner("🧠 正在优化..."):
        _render_optimization_results(transcript, params)
    st.success("🎉 优化完成！")


def _run_batch_optimization(transcripts: list, params: dict):
    """批量执行优化"""
    progress = st.progress(0, text="批量优化中...")
    results_container = st.container()

    for i, transcript in enumerate(transcripts):
        progress.progress((i + 1) / len(transcripts), text=f"正在处理第 {i+1}/{len(transcripts)} 段...")
        with results_container:
            st.markdown(f"---\n**第 {i+1} 段**")
            _render_optimization_results(transcript, params, key_suffix=f"batch_{i}")

    progress.empty()
    st.success(f"🎉 批量优化完成！共处理 {len(transcripts)} 段文案")


def _render_optimization_results(transcript: str, params: dict, key_suffix: str = ""):
    """调用 API 并渲染优化结果"""
    platform = params.get("target_platform", "douyin")
    num_variants = params.get("num_variants", 5)
    opt_types = params.get("optimization_types", ["script", "title"])

    if "script" in opt_types:
        try:
            resp = requests.post(
                f"{API_URL}/api/v2/optimizer/optimize-script",
                json={"transcript": transcript, "target_platform": platform},
                timeout=60,
            )
            if resp.status_code == 200:
                result = resp.json()
                # 缓存优化结果供重生成页面使用
                st.session_state["last_optimized_script"] = result.get("optimized_script", "")
                st.session_state["last_original_transcript"] = transcript
                st.subheader("✍️ 文案优化")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("**原文案**")
                    st.text_area("原文", transcript, height=150, key=f"orig_{key_suffix}")
                with col2:
                    st.markdown("**优化后**")
                    st.text_area("优化", result.get("optimized_script", ""), height=150, key=f"opt_{key_suffix}")
                changes = result.get("changes", [])
                if changes:
                    with st.expander("📋 改进说明"):
                        for c in changes:
                            st.markdown(f"- {c}")
            else:
                st.error(f"文案优化失败: {resp.json().get('detail', resp.text)}")
        except requests.ConnectionError:
            st.error("❌ 无法连接到 API 服务")

    if "title" in opt_types:
        try:
            resp = requests.post(
                f"{API_URL}/api/v2/optimizer/generate-titles",
                json={
                    "transcript": transcript,
                    "keywords": [],
                    "num_titles": num_variants,
                    "target_platform": platform,
                },
                timeout=60,
            )
            if resp.status_code == 200:
                titles = resp.json()
                st.subheader("📝 标题生成")
                style_labels = {
                    "curiosity_gap": "好奇心缺口", "emotional": "情感共鸣",
                    "practical": "实用价值", "controversy": "争议讨论",
                    "fomo": "紧迫感", "benefit": "收益承诺",
                    "celebrity": "名人效应", "number": "数字列表",
                }
                for j, t in enumerate(titles, 1):
                    with st.expander(f"标题 {j}: {t.get('title', '')}"):
                        c1, c2 = st.columns(2)
                        with c1:
                            st.markdown(f"**风格**: {style_labels.get(t.get('style',''), t.get('style',''))}")
                            st.markdown(f"**预估CTR**: {t.get('estimated_ctr', 0) * 100:.1f}%")
                        with c2:
                            st.markdown(f"**理由**: {t.get('rationale', '')}")
            else:
                st.error(f"标题生成失败: {resp.json().get('detail', resp.text)}")
        except requests.ConnectionError:
            st.error("❌ 无法连接到 API 服务")


def show_regeneration_page():
    """视频重生成页面 — 分析→优化→重生成 完整链路"""
    st.header("🎬 视频重生成")
    st.info("基于优化文案重新生成视频：TTS 语音合成 → 音视频合并 → 字幕烧录")

    # Step 1: 选择原始视频
    st.subheader("📹 Step 1 · 选择原始视频")
    analysis = st.session_state.get("analysis_result", {})
    cached_video_path = analysis.get("video_path", "")

    video_path = st.text_input(
        "原始视频路径",
        value=cached_video_path or "/home/ubuntu/微信视频2026-06-02_225420_701.mp4",
        help="输入服务器上的视频文件绝对路径",
    )

    # 验证视频路径（通过 API 侧检查，此处仅做前端提示）
    if video_path:
        st.caption(f"📁 视频路径: `{video_path}`")
    else:
        st.warning("⚠️ 请输入原始视频路径")
        return

    st.divider()

    # Step 2: 配置优化文案
    st.subheader("✍️ Step 2 · 配置优化文案")
    cached_opt_script = st.session_state.get("last_optimized_script", "")
    cached_orig_transcript = st.session_state.get("last_original_transcript", "")

    original_transcript = st.text_area(
        "原文案",
        value=cached_orig_transcript,
        height=80,
        help="原始视频的转录文本（可选，用于对比）",
        key="regen_orig_transcript",
    )

    optimized_script = st.text_area(
        "优化后文案（将用于 TTS 语音合成）",
        value=cached_opt_script,
        height=120,
        help="优化后的文案将转为语音并合成到新视频中",
        key="regen_opt_script",
    )

    if not optimized_script.strip():
        st.warning("⚠️ 请输入优化后的文案，或先在「智能优化」页面生成优化文案")
        return

    st.divider()

    # Step 3: 重生成参数
    st.subheader("⚙️ Step 3 · 重生成参数")
    col1, col2 = st.columns(2)
    with col1:
        variant_id = st.text_input("变体 ID", value="v1", key="regen_variant")
    with col2:
        platforms = st.multiselect(
            "目标平台",
            ["douyin", "xiaohongshu", "weixin"],
            default=["douyin"],
            format_func=lambda x: _PLATFORM_LABELS.get(x, x),
            key="regen_platforms",
        )

    analysis_id = analysis.get("task_id", "")
    if analysis_id:
        st.caption(f"关联分析任务: `{analysis_id}`")

    st.divider()

    # Step 4: 执行重生成
    if st.button("🎬 开始重生成", type="primary", use_container_width=True, key="regen_start"):
        if not platforms:
            st.warning("⚠️ 请至少选择一个目标平台")
            return

        with st.spinner("🎬 正在重生成视频，请耐心等待（TTS合成+FFmpeg合并可能需要1-3分钟）..."):
            try:
                resp = requests.post(
                    f"{API_URL}/api/v2/regenerator/regenerate",
                    json={
                        "original_video_path": video_path,
                        "optimized_script": optimized_script,
                        "original_transcript": original_transcript,
                        "analysis_id": analysis_id,
                        "variant_id": variant_id,
                        "target_platforms": platforms,
                    },
                    timeout=300,
                )

                if resp.status_code == 200:
                    result = resp.json()
                    st.session_state["last_regen_result"] = result
                    _render_regen_result(result)
                    st.success("🎉 视频重生成完成！")
                else:
                    error = resp.json().get("detail", resp.text)
                    st.error(f"❌ 重生成失败: {error}")

            except requests.ConnectionError:
                st.error("❌ 无法连接到 API 服务，请确认服务已启动")
            except requests.Timeout:
                st.error("❌ 请求超时，视频重生成可能需要较长时间，请稍后查看任务状态")
            except Exception as e:
                st.error(f"❌ 未知错误: {e}")

    # 显示上次重生成结果
    elif "last_regen_result" in st.session_state:
        st.subheader("📋 上次重生成结果")
        _render_regen_result(st.session_state["last_regen_result"])


def _render_regen_result(result: dict):
    """渲染重生成结果"""
    status = result.get("status", "unknown")
    task_id = result.get("task_id", "")
    message = result.get("message", "")

    # 状态指示
    status_icons = {"completed": "✅", "processing": "⏳", "partial": "⚠️", "failed": "❌"}
    st.markdown(f"**任务状态**: {status_icons.get(status, '❓')} {status}")
    st.caption(f"任务 ID: `{task_id}`")

    if message:
        st.info(message)

    # 重生成视频信息
    videos = result.get("regenerated_videos") or {}
    if videos:
        st.subheader("📹 重生成视频")
        for platform, info in videos.items():
            platform_label = _PLATFORM_LABELS.get(platform, platform)
            with st.expander(f"{platform_label}", expanded=True):
                col1, col2 = st.columns(2)
                with col1:
                    video_path = info.get("video_path", "")
                    if video_path:
                        st.markdown(f"**文件路径**: `{video_path}")
                    file_size = info.get("file_size", 0)
                    if file_size > 0:
                        size_mb = file_size / (1024 * 1024)
                        st.metric("文件大小", f"{size_mb:.1f} MB")
                with col2:
                    duration = info.get("duration", 0)
                    if duration > 0:
                        st.metric("时长", f"{duration:.1f} 秒")
                    video_url = info.get("video_url")
                    if video_url:
                        st.markdown(f"**访问链接**: [点击播放]({video_url})")

                # 如果有视频路径，尝试在页面上播放
                if video_path:
                    try:
                        st.video(video_path)
                    except Exception:
                        st.caption("💡 视频文件在服务器上，可通过路径下载查看")


def show_about_page():
    """关于页面"""
    st.header("ℹ️ 关于 Video AI Optimizer")

    st.markdown("""
    ## 🎬 Video AI Optimizer

    **面向中国短视频创作者的 AI 驱动视频优化平台**

    ### ✨ 核心功能
    - 📊 **智能视频分析** — 元数据提取、音频转录、意图识别、质量评分
    - 🧠 **AI 文案优化** — LLM 驱动的文案重写与标题生成
    - 📱 **平台适配** — 抖音/小红书/微信格式自适应
    - 🎬 **视频重生成** — TTS语音合成 + FFmpeg音视频合并 + 字幕烧录

    ### 🏗️ 技术栈
    - **后端**: FastAPI + Pydantic
    - **前端**: Streamlit
    - **AI**: DeepSeek/OpenAI (LLM) + Faster Whisper (ASR)
    - **视频处理**: OpenCV + FFmpeg

    ### 🚀 启动方式
    ```bash
    # 终端 1: 启动 API
    cd /home/ubuntu/VideoContentOptimizer
    source venv/bin/activate
    uvicorn app.main:app --port 8080

    # 终端 2: 启动 Web UI
    streamlit run webui/main.py --server.port 8501
    ```

    ### 📡 API 文档
    - Swagger UI: http://localhost:8080/docs
    - ReDoc: http://localhost:8080/redoc
    """)


if __name__ == "__main__":
    main()
