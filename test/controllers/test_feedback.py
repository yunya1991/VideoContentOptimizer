"""
测试 POST /api/v2/feedback 端点

测试覆盖：
- 正向信号（score=4,5）→ capture_success 被调用
- 中性信号（score=3）→ capture_success 以 0.5 权重调用
- 负向信号（score=1,2）→ capture_correction 被调用
- 404：task_id 不存在
- 503：进化引擎未初始化
- 400：不支持的 task_type
- 三种 task_type 路由（analyze/regenerate/optimize）
- _evolution_context 字段缺失时的优雅降级
- comment 字段为 None 时 capture_correction 兜底文案
"""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import FastAPI

from app.controllers.v2.feedback import router, FeedbackRequest


# --- 测试 App ---

app = FastAPI()
app.include_router(router, prefix="/api/v2")
client = TestClient(app)


# --- 辅助工具 ---

def _make_task_data(with_context: bool = True, task_type: str = "analyze") -> dict:
    if with_context:
        return {
            "status": "completed",
            "_evolution_context": {
                "task_type": task_type,
                "context": f"video=test.mp4, intent=tutorial",
                "approach": "whisper_transcription_llm_analysis",
            },
        }
    return {"status": "completed"}


# --- 测试：评分归一化 ---

class TestScoreNormalization:
    def test_score_5_normalized_to_1_0(self):
        assert (5 - 1) / 4.0 == 1.0

    def test_score_4_normalized_to_0_75(self):
        assert (4 - 1) / 4.0 == 0.75

    def test_score_3_normalized_to_0_5(self):
        assert (3 - 1) / 4.0 == 0.5

    def test_score_2_normalized_to_0_25(self):
        assert (2 - 1) / 4.0 == 0.25

    def test_score_1_normalized_to_0_0(self):
        assert (1 - 1) / 4.0 == 0.0


# --- 测试：正向信号 (score >= 3) ---

class TestPositiveFeedback:
    def _post(self, score, task_id="task_abc123", task_type="analyze"):
        return client.post(
            "/api/v2/feedback",
            json={"task_id": task_id, "score": score, "task_type": task_type},
        )

    def test_score_5_calls_capture_success(self):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = self._post(score=5)

        assert resp.status_code == 200
        body = resp.json()
        assert body["action"] == "capture_success"
        assert body["normalized_score"] == 1.0
        mock_evolution.capture_success.assert_called_once()
        call_kwargs = mock_evolution.capture_success.call_args[1]
        assert call_kwargs["quality_score"] == 1.0

    def test_score_4_calls_capture_success(self):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = self._post(score=4)

        assert resp.status_code == 200
        assert resp.json()["action"] == "capture_success"
        call_kwargs = mock_evolution.capture_success.call_args[1]
        assert call_kwargs["quality_score"] == pytest.approx(0.75)

    def test_score_3_calls_capture_success_with_half_weight(self):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = self._post(score=3)

        assert resp.status_code == 200
        assert resp.json()["action"] == "capture_success"
        call_kwargs = mock_evolution.capture_success.call_args[1]
        assert call_kwargs["quality_score"] == pytest.approx(0.5)
        mock_evolution.capture_correction.assert_not_called()


# --- 测试：负向信号 (score < 3) ---

class TestNegativeFeedback:
    def _post(self, score, comment=None, task_type="analyze"):
        payload = {"task_id": "task_abc123", "score": score, "task_type": task_type}
        if comment:
            payload["comment"] = comment
        return client.post("/api/v2/feedback", json=payload)

    def test_score_2_calls_capture_correction(self):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = self._post(score=2)

        assert resp.status_code == 200
        assert resp.json()["action"] == "capture_correction"
        mock_evolution.capture_correction.assert_called_once()
        mock_evolution.capture_success.assert_not_called()

    def test_score_1_calls_capture_correction(self):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = self._post(score=1)

        assert resp.status_code == 200
        assert resp.json()["action"] == "capture_correction"

    def test_comment_passed_as_reason(self):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = self._post(score=1, comment="结果不准确")

        call_kwargs = mock_evolution.capture_correction.call_args[1]
        assert call_kwargs["reason"] == "结果不准确"

    def test_no_comment_uses_fallback_reason(self):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = self._post(score=2, comment=None)

        call_kwargs = mock_evolution.capture_correction.call_args[1]
        assert "2/5" in call_kwargs["reason"]


# --- 测试：错误情况 ---

class TestErrorCases:
    def test_unknown_task_id_returns_404(self):
        mock_evolution = MagicMock()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=None):
            resp = client.post(
                "/api/v2/feedback",
                json={"task_id": "nonexistent", "score": 5, "task_type": "analyze"},
            )

        assert resp.status_code == 404

    def test_engine_none_returns_503(self):
        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=None):
            resp = client.post(
                "/api/v2/feedback",
                json={"task_id": "task_abc", "score": 5, "task_type": "analyze"},
            )

        assert resp.status_code == 503

    def test_invalid_task_type_returns_400(self):
        mock_evolution = MagicMock()

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution):
            resp = client.post(
                "/api/v2/feedback",
                json={"task_id": "task_abc", "score": 5, "task_type": "unknown_type"},
            )

        assert resp.status_code == 400

    def test_score_out_of_range_returns_422(self):
        mock_evolution = MagicMock()
        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution):
            resp = client.post(
                "/api/v2/feedback",
                json={"task_id": "task_abc", "score": 6, "task_type": "analyze"},
            )
        assert resp.status_code == 422


# --- 测试：task_type 路由 ---

class TestTaskTypeRouting:
    @pytest.mark.parametrize("task_type", ["analyze", "regenerate", "optimize"])
    def test_all_task_types_route_correctly(self, task_type):
        mock_evolution = MagicMock()
        mock_task_data = _make_task_data(task_type=task_type)

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = client.post(
                "/api/v2/feedback",
                json={"task_id": "task_xyz", "score": 4, "task_type": task_type},
            )

        assert resp.status_code == 200
        assert resp.json()["action"] == "capture_success"


# --- 测试：_evolution_context 缺失时的优雅降级 ---

class TestMissingEvolutionContext:
    def test_missing_context_falls_back_to_empty_strings(self):
        mock_evolution = MagicMock()
        # task_data without _evolution_context
        mock_task_data = {"status": "completed"}

        with patch("app.controllers.v2.feedback.get_evolution_engine", return_value=mock_evolution), \
             patch("app.controllers.v2.feedback._get_task_data", return_value=mock_task_data):
            resp = client.post(
                "/api/v2/feedback",
                json={"task_id": "task_abc", "score": 5, "task_type": "analyze"},
            )

        assert resp.status_code == 200
        call_kwargs = mock_evolution.capture_success.call_args[1]
        assert call_kwargs["approach"] == ""
        assert call_kwargs["task_type"] == "analyze"
