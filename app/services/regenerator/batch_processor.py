"""
批量处理模块
"""

import os
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from app.config import get_settings
from app.models.schema import BatchAnalysisTask, VideoAnalysisResult
from app.services.analyzer.video_parser import VideoParser
from app.services.analyzer.audio_transcriber import AudioTranscriber
from app.services.analyzer.intent_detector import IntentDetector
from app.services.analyzer.quality_scorer import QualityScorer
from app.utils.logger import logger

settings = get_settings()

class BatchProcessor:
    """批量视频处理"""
    
    def __init__(
        self,
        max_workers: Optional[int] = None,
        batch_size: Optional[int] = None
    ):
        """
        初始化批量处理器
        
        Args:
            max_workers: 最大工作线程数
            batch_size: 批处理大小
        """
        self.max_workers = max_workers or settings.PARALLEL_WORKERS
        self.batch_size = batch_size or settings.BATCH_SIZE
        self.parser = VideoParser()
        self.transcriber = AudioTranscriber()
        self.detector = IntentDetector()
        self.scorer = QualityScorer()
    
    def process_batch(
        self,
        video_paths: List[str],
        task_id: str = "batch_task",
        enable_optimization: bool = False
    ) -> BatchAnalysisTask:
        """
        批量处理视频
        
        Args:
            video_paths: 视频路径列表
            task_id: 任务 ID
            enable_optimization: 是否启用优化
            
        Returns:
            BatchAnalysisTask: 批量任务对象
        """
        task = BatchAnalysisTask(
            task_id=task_id,
            status="processing",
            videos=[{"path": p, "name": os.path.basename(p)} for p in video_paths]
        )
        
        results = []
        total = len(video_paths)
        
        # 使用线程池并行处理
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            future_to_video = {
                executor.submit(self._process_single_video, path): path
                for path in video_paths[:settings.MAX_BATCH_VIDEOS]
            }
            
            for i, future in enumerate(as_completed(future_to_video), 1):
                video_path = future_to_video[future]
                try:
                    result = future.result()
                    results.append(result)
                    logger.info(f"处理完成 ({i}/{total}): {os.path.basename(video_path)}")
                except Exception as e:
                    logger.warning(f"处理失败 ({i}/{total}): {video_path} - {e}")
                    # 添加失败记录
                    results.append(self._create_failed_result(video_path, str(e)))
                
                # 更新进度
                task.progress = (i / total) * 100
        
        task.results = results
        task.status = "completed"
        task.progress = 100.0
        
        # 计算统计信息
        task.statistics = self._calculate_statistics(results)
        
        return task
    
    def _process_single_video(self, video_path: str) -> VideoAnalysisResult:
        """
        处理单个视频（分析）
        
        Returns:
            VideoAnalysisResult: 分析结果
        """
        from datetime import datetime
        
        # 1. 解析元数据
        metadata = self.parser.parse_video(video_path)
        
        # 2. 转录音频
        transcript = ""
        if settings.ENABLE_AUDIO_TRANSCRIPTION:
            try:
                transcript = self.transcriber.transcribe(video_path)
            except Exception as e:
                logger.warning(f"转录失败: {e}")
        
        # 3. 识别意图
        intent = self.detector.detect_intent(transcript)
        
        # 4. 质量评分
        quality_score = self.scorer.generate_quality_score(
            transcript=transcript,
            intent=intent,
            metadata=metadata
        )
        
        # 5. 构建分析结果
        from app.models.schema import VideoAnalysisResult, PlatformAnalysis, TrendPrediction
        
        result = VideoAnalysisResult(
            task_id=f"task_{hash(video_path) % 10000}",
            video_path=video_path,
            upload_time=datetime.now(),
            video_metadata=metadata,
            audio_transcript=transcript,
            video_intent=intent,
            quality_score=quality_score,
            platform_analysis=PlatformAnalysis(
                best_platform=settings.DEFAULT_PLATFORM,
                platform_scores=[]
            ),
            trend_prediction=TrendPrediction(
                trend_score=50.0,
                growth_potential="medium"
            )
        )
        
        return result
    
    def _create_failed_result(self, video_path: str, error: str) -> dict:
        """创建失败结果"""
        return {
            "video_path": video_path,
            "status": "failed",
            "error": error
        }
    
    def _calculate_statistics(self, results: List[VideoAnalysisResult]) -> dict:
        """计算统计信息"""
        if not results:
            return {}
        
        successful = [r for r in results if isinstance(r, VideoAnalysisResult)]
        
        if not successful:
            return {"total": len(results), "successful": 0}
        
        avg_quality = sum(r.quality_score.overall_score or 0 for r in successful) / len(successful)
        
        return {
            "total_videos": len(results),
            "processed_videos": len(successful),
            "avg_quality_score": round(avg_quality, 2),
            "avg_engagement_potential": 0.0  # TODO: 计算
        }
