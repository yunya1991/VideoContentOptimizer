"""
Streamlit Web UI 主应用 - 简化测试版
"""

import streamlit as st
import os
import sys

# 添加项目路径
project_root = os.path.dirname(os.path.dirname(__file__))
sys.path.append(project_root)

# 页面配置
st.set_page_config(
    page_title="视频AI优化器",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="expanded"
)

def main():
    """主函数"""
    st.title("🎬 Video AI Optimizer")
    st.markdown("### 智能视频分析与优化平台 - 测试版")
    
    # 侧边栏
    st.sidebar.title("功能导航")
    
    page = st.sidebar.radio(
        "选择功能",
        [
            "📊 视频分析",
            "🧠 智能优化",
            "ℹ️ 关于"
        ]
    )
    
    # 页面路由
    if page == "📊 视频分析":
        show_analysis_page()
    elif page == "🧠 智能优化":
        show_optimization_page()
    elif page == "ℹ️ 关于":
        show_about_page()

def show_analysis_page():
    """视频分析页面"""
    st.header("📊 视频分析")
    st.info("上传视频，自动分析内容、识别意图、评估质量")
    
    uploaded_file = st.file_uploader(
        "上传视频文件",
        type=['mp4', 'mov', 'avi', 'mkv'],
        help="支持 MP4, MOV, AVI, MKV 格式"
    )
    
    if uploaded_file is not None:
        st.video(uploaded_file)
        st.success(f"✅ 已上传: {uploaded_file.name}")
        
        if st.button("🚀 开始分析", type="primary"):
            st.info("📋 正在分析视频...")
            
            # 模拟分析结果
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("⏱️ 时长", "45.0秒")
            with col2:
                st.metric("📐 分辨率", "1920x1080")
            with col3:
                st.metric("🎞️ 帧率", "24 FPS")
            with col4:
                st.metric("📁 格式", "mp4")
            
            st.subheader("📝 音频转录")
            st.text_area(
                "转录文本",
                "这是一段测试转录文本，用于演示视频分析功能。实际应用中会调用 Faster Whisper 进行真实转录。",
                height=150
            )
            
            st.subheader("🎯 视频意图")
            col1, col2 = st.columns(2)
            with col1:
                st.info("**分类**: 教育")
                st.info("**子类别**: 编程教学")
            with col2:
                st.info("**情感基调**: 励志")
                st.info("**置信度**: 85%")
            
            st.subheader("⭐ 质量评分")
            col1, col2, col3, col4, col5 = st.columns(5)
            with col1:
                st.metric("内容质量", "8.5/10")
            with col2:
                st.metric("制作质量", "7.2/10")
            with col3:
                st.metric("互动潜力", "8.8/10")
            with col4:
                st.metric("原创度", "7.5/10")
            with col5:
                st.metric("综合评分", "8.0/10")
            
            st.success("✅ 分析完成！")

def show_optimization_page():
    """智能优化页面"""
    st.header("🧠 智能优化")
    st.info("基于 LLM 的文案优化、标题生成、平台适配")
    
    # 优化选项
    col1, col2, col3 = st.columns(3)
    with col1:
        enable_script = st.checkbox("✍️ 文案优化", value=True)
    with col2:
        enable_title = st.checkbox("📝 标题生成", value=True)
    with col3:
        enable_platform = st.checkbox("📱 平台适配", value=True)
    
    if st.button("🚀 开始优化", type="primary", use_container_width=True):
        st.info("🧠 正在优化...")
        
        if enable_script:
            st.subheader("✍️ 文案优化")
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**原文案**")
                st.text_area("", value="如何在30天内学会编程", height=150)
            with col2:
                st.markdown("**优化后**")
                st.text_area("", value="他用30天从0学会编程，年薪涨20万！", height=150)
        
        if enable_title:
            st.subheader("📝 标题生成")
            titles = [
                ("他用30天从0学会编程，年薪涨20万！", "benefit", "15%"),
                ("30天编程速成，已有10万人学会！", "fomo", "12%"),
                ("我后悔没有早点学编程", "emotional", "10%")
            ]
            for i, (title, style, ctr) in enumerate(titles, 1):
                with st.expander(f"标题 {i}: {title}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**风格**: {style}")
                        st.markdown(f"**预估CTR**: {ctr}")
                    with col2:
                        st.markdown("**理由**: 吸引人，有说服力")
        
        st.success("🎉 优化完成！")

def show_about_page():
    """关于页面"""
    st.header("ℹ️ 关于 Video AI Optimizer")
    
    st.markdown("""
    ## 🎬 Video AI Optimizer
    
    **面向中国短视频创作者的 AI 驱动视频优化平台**
    
    ### ✨ 核心功能
    - 📊 **智能视频分析** - 自动识别视频意图、提取关键词、评估质量
    - 🧠 **AI 文案优化** - 基于 LLM 的文案重写、标题生成
    - 🎬 **批量处理** - 支持批量视频分析与优化
    - 💡 **创意增强** - 多版本生成、A/B 测试
    - 📱 **平台适配** - 抖音/小红书/微信格式自适应
    
    ### 🏗️ 技术栈
    - **后端**: FastAPI + Pydantic
    - **前端**: Streamlit
    - **AI**: DeepSeek/OpenAI (LLM) + Faster Whisper (ASR)
    - **视频处理**: OpenCV + FFmpeg
    
    ### 📂 项目路径
    ```
    /home/ubuntu/VideoContentOptimizer
    ```
    
    ### 🚀 快速开始
    ```bash
    cd /home/ubuntu/VideoContentOptimizer
    source venv/bin/activate
    streamlit run webui/main.py --server.port 8501
    ```
    
    ### 📖 更多文档
    查看 [README.md](README.md) 获取完整文档。
    """)

if __name__ == "__main__":
    main()
