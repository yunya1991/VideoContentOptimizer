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
        ["📊 视频分析", "🧠 智能优化", "ℹ️ 关于"],
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
    elif page == "ℹ️ 关于":
        show_about_page()


def _check_api() -> bool:
    """检查 API 服务是否可用"""
    try:
        resp = requests.get(f"{API_URL}/health", timeout=3)
        return resp.status_code == 200
    except requests.ConnectionError:
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


def show_optimization_page():
    """智能优化页面 — 调用真实 API"""
    st.header("🧠 智能优化")
    st.info("基于 LLM 的文案优化、标题生成、平台适配")

    # 从分析结果中获取转录文本
    analysis = st.session_state.get("analysis_result", {})
    default_transcript = analysis.get("transcript", "")

    # 输入区域
    transcript = st.text_area(
        "📝 视频转录文本 / 原始文案",
        value=default_transcript,
        height=120,
        help="可直接输入文案，或从视频分析页面自动获取转录文本",
    )

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        target_platform = st.selectbox(
            "📱 目标平台", ["douyin", "xiaohongshu", "weixin"],
            format_func=lambda x: {"douyin": "抖音", "xiaohongshu": "小红书", "weixin": "微信视频号"}.get(x, x),
        )
    with col2:
        num_titles = st.slider("📝 标题变体数量", 1, 8, 5)
    with col3:
        st.write("")  # 占位
        st.write("")  # 占位

    enable_script = st.checkbox("✍️ 文案优化", value=True)
    enable_title = st.checkbox("📝 标题生成", value=True)

    if st.button("🚀 开始优化", type="primary", use_container_width=True):
        if not transcript.strip():
            st.warning("⚠️ 请先输入文案文本或上传视频获取转录结果")
            return

        with st.spinner("🧠 正在优化..."):
            # 文案优化
            if enable_script:
                try:
                    resp = requests.post(
                        f"{API_URL}/api/v2/optimizer/optimize-script",
                        json={
                            "transcript": transcript,
                            "target_platform": target_platform,
                        },
                        timeout=60,
                    )

                    if resp.status_code == 200:
                        result = resp.json()
                        st.subheader("✍️ 文案优化")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**原文案**")
                            st.text_area("原文", transcript, height=150, key="orig_script")
                        with col2:
                            st.markdown("**优化后**")
                            st.text_area(
                                "优化",
                                result.get("optimized_script", ""),
                                height=150,
                                key="opt_script",
                            )

                        changes = result.get("changes", [])
                        if changes:
                            with st.expander("📋 改进说明"):
                                for c in changes:
                                    st.markdown(f"- {c}")
                    else:
                        st.error(f"文案优化失败: {resp.json().get('detail', resp.text)}")

                except requests.ConnectionError:
                    st.error("❌ 无法连接到 API 服务")

            # 标题生成
            if enable_title:
                try:
                    resp = requests.post(
                        f"{API_URL}/api/v2/optimizer/generate-titles",
                        json={
                            "transcript": transcript,
                            "keywords": [],
                            "num_titles": num_titles,
                            "target_platform": target_platform,
                        },
                        timeout=60,
                    )

                    if resp.status_code == 200:
                        titles = resp.json()
                        st.subheader("📝 标题生成")

                        for i, t in enumerate(titles, 1):
                            title_text = t.get("title", "")
                            style = t.get("style", "")
                            ctr = t.get("estimated_ctr", 0)
                            rationale = t.get("rationale", "")

                            with st.expander(f"标题 {i}: {title_text}"):
                                col1, col2 = st.columns(2)
                                with col1:
                                    style_labels = {
                                        "curiosity_gap": "好奇心缺口",
                                        "emotional": "情感共鸣",
                                        "practical": "实用价值",
                                        "controversy": "争议讨论",
                                        "fomo": "紧迫感",
                                        "benefit": "收益承诺",
                                        "celebrity": "名人效应",
                                        "number": "数字列表",
                                    }
                                    st.markdown(f"**风格**: {style_labels.get(style, style)}")
                                    st.markdown(f"**预估CTR**: {ctr * 100:.1f}%")
                                with col2:
                                    st.markdown(f"**理由**: {rationale}")
                    else:
                        st.error(f"标题生成失败: {resp.json().get('detail', resp.text)}")

                except requests.ConnectionError:
                    st.error("❌ 无法连接到 API 服务")

        st.success("🎉 优化完成！")


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
    - 🎬 **视频重生成** — 基于优化方案重新合成（开发中）

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
