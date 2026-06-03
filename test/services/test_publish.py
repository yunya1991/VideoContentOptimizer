"""
UploadPostClient + PublishManager 单元测试

测试范围:
  UploadPostClient:
    - 上传成功路径 → 返回 request_id / platforms / skipped
    - douyin → tiktok 平台映射
    - xiaohongshu / weixin 被跳过，记录警告
    - 多平台: platform[0] / platform[1] 出现在 form data
    - api_key 为空 → ValueError
    - 视频文件不存在 → FileNotFoundError
    - HTTP 4xx → RuntimeError
    - check_status 成功 → 返回 dict
    - check_status 404 → None
    - check_status HTTP 错误 → RuntimeError
    - 所有平台均不支持 → ValueError
    - 未知平台原样传递

  PublishManager:
    - enabled=False → publish() 返回 {}，不抛异常
    - enabled=True 但 api_key 空 → ValueError
    - 视频文件不存在 → FileNotFoundError
    - 成功发布 → 调用 UploadPostClient.upload
    - from_settings() 读取配置
"""

import os
from unittest.mock import MagicMock, patch, call

import pytest


# ─── helpers ──────────────────────────────────────────────────────────────────

def _make_response(status_code: int = 200, json_data: dict = None, text: str = ""):
    resp = MagicMock()
    resp.status_code = status_code
    resp.text = text or str(json_data or {})
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = Exception("no json")
    return resp


# ═══════════════════════════════════════════════════════════════════════════════
# Section 1 — UploadPostClient 基础上传
# ═══════════════════════════════════════════════════════════════════════════════

class TestUploadPostClientUpload:

    @pytest.fixture
    def client(self):
        from app.services.publish.upload_post_client import UploadPostClient
        return UploadPostClient(api_key="test_key", username="test_user")

    def test_upload_success(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00" * 64)

        mock_resp = _make_response(200, {"request_id": "abc123"})
        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = client.upload(str(video), "My Video", ["tiktok"])

        assert result["request_id"] == "abc123"
        assert result["platforms"] == ["tiktok"]
        assert result["skipped"] == []
        mock_post.assert_called_once()

    def test_upload_douyin_maps_to_tiktok(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00" * 64)

        mock_resp = _make_response(200, {"request_id": "r1"})
        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = client.upload(str(video), "Title", ["douyin"])

        assert "tiktok" in result["platforms"]
        form_data = mock_post.call_args[1]["data"]
        assert form_data.get("platform[0]") == "tiktok"

    def test_upload_missing_file_raises(self, client):
        with pytest.raises(FileNotFoundError, match="视频文件不存在"):
            client.upload("/no/such/file.mp4", "T", ["tiktok"])

    def test_upload_http_error_raises_runtime(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00" * 64)

        with patch("requests.post", return_value=_make_response(401, text="Unauthorized")):
            with pytest.raises(RuntimeError, match="401"):
                client.upload(str(video), "T", ["tiktok"])

    def test_upload_500_raises_runtime(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00" * 64)

        with patch("requests.post", return_value=_make_response(500, text="Server Error")):
            with pytest.raises(RuntimeError, match="500"):
                client.upload(str(video), "T", ["tiktok"])

    def test_missing_api_key_raises_value_error(self):
        from app.services.publish.upload_post_client import UploadPostClient
        with pytest.raises(ValueError, match="UPLOAD_POST_API_KEY"):
            UploadPostClient(api_key="", username="user")

    def test_all_platforms_unsupported_raises(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00" * 64)

        with pytest.raises(ValueError, match="不受支持"):
            client.upload(str(video), "T", ["xiaohongshu", "weixin"])

    def test_title_truncated_to_2200(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00" * 64)
        long_title = "A" * 3000

        mock_resp = _make_response(200, {"request_id": "r2"})
        with patch("requests.post", return_value=mock_resp) as mock_post:
            client.upload(str(video), long_title, ["tiktok"])

        form_data = mock_post.call_args[1]["data"]
        assert len(form_data["title"]) == 2200

    def test_auth_header_set(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00" * 64)

        mock_resp = _make_response(200, {"request_id": "r3"})
        with patch("requests.post", return_value=mock_resp) as mock_post:
            client.upload(str(video), "T", ["tiktok"])

        headers = mock_post.call_args[1]["headers"]
        assert headers.get("Authorization") == "Apikey test_key"


# ═══════════════════════════════════════════════════════════════════════════════
# Section 2 — 平台映射
# ═══════════════════════════════════════════════════════════════════════════════

class TestPlatformMapping:

    @pytest.fixture
    def client(self):
        from app.services.publish.upload_post_client import UploadPostClient
        return UploadPostClient(api_key="k", username="u")

    def _do_upload(self, client, video_path, platforms):
        mock_resp = _make_response(200, {"request_id": "ok"})
        with patch("requests.post", return_value=mock_resp) as mock_post:
            result = client.upload(str(video_path), "T", platforms)
        form_data = mock_post.call_args[1]["data"]
        return result, form_data

    def test_xiaohongshu_skipped(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00")
        result, form_data = self._do_upload(client, video, ["tiktok", "xiaohongshu"])
        assert "xiaohongshu" in result["skipped"]
        assert "tiktok" in result["platforms"]

    def test_weixin_skipped(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00")
        result, form_data = self._do_upload(client, video, ["weixin", "youtube"])
        assert "weixin" in result["skipped"]
        assert "youtube" in result["platforms"]

    def test_multi_platform_form_fields(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00")
        _, form_data = self._do_upload(client, video, ["tiktok", "youtube"])
        assert form_data.get("platform[0]") in ("tiktok", "youtube")
        assert form_data.get("platform[1]") in ("tiktok", "youtube")
        assert form_data.get("platform[0]") != form_data.get("platform[1]")

    def test_douyin_dedup_with_tiktok(self, client, tmp_path):
        """douyin 和 tiktok 都映射为 tiktok，应去重只提交一次。"""
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00")
        result, form_data = self._do_upload(client, video, ["douyin", "tiktok"])
        assert result["platforms"].count("tiktok") == 1

    def test_unknown_platform_passed_as_is(self, client, tmp_path):
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00")
        result, form_data = self._do_upload(client, video, ["snapchat"])
        assert "snapchat" in result["platforms"]


# ═══════════════════════════════════════════════════════════════════════════════
# Section 3 — check_status
# ═══════════════════════════════════════════════════════════════════════════════

class TestCheckStatus:

    @pytest.fixture
    def client(self):
        from app.services.publish.upload_post_client import UploadPostClient
        return UploadPostClient(api_key="k", username="u")

    def test_check_status_success(self, client):
        mock_resp = _make_response(200, {"status": "published"})
        with patch("requests.get", return_value=mock_resp):
            result = client.check_status("req123")
        assert result["status"] == "published"

    def test_check_status_404_returns_none(self, client):
        mock_resp = _make_response(404, text="Not Found")
        with patch("requests.get", return_value=mock_resp):
            result = client.check_status("nonexistent")
        assert result is None

    def test_check_status_error_raises_runtime(self, client):
        mock_resp = _make_response(500, text="Server Error")
        with patch("requests.get", return_value=mock_resp):
            with pytest.raises(RuntimeError, match="500"):
                client.check_status("req456")


# ═══════════════════════════════════════════════════════════════════════════════
# Section 4 — PublishManager
# ═══════════════════════════════════════════════════════════════════════════════

class TestPublishManager:

    def test_disabled_returns_empty_dict(self, tmp_path):
        from app.services.publish.upload_post_client import PublishManager
        pm = PublishManager(enabled=False)
        result = pm.publish(str(tmp_path / "v.mp4"), "T")
        assert result == {}

    def test_disabled_no_file_check(self):
        """未启用时不应触发文件存在检查。"""
        from app.services.publish.upload_post_client import PublishManager
        pm = PublishManager(enabled=False)
        result = pm.publish("/no/such/file.mp4", "T")
        assert result == {}

    def test_enabled_no_api_key_raises(self, tmp_path):
        from app.services.publish.upload_post_client import PublishManager
        # enabled=True 但构造时 api_key 空 → _client is None
        pm = PublishManager(enabled=True, api_key="")
        with pytest.raises(ValueError, match="UPLOAD_POST_API_KEY"):
            pm.publish(str(tmp_path / "v.mp4"), "T")

    def test_enabled_missing_file_raises(self, tmp_path):
        from app.services.publish.upload_post_client import PublishManager
        pm = PublishManager(enabled=True, api_key="k", username="u")
        with pytest.raises(FileNotFoundError):
            pm.publish(str(tmp_path / "nonexistent.mp4"), "T")

    def test_enabled_success_delegates_to_client(self, tmp_path):
        from app.services.publish.upload_post_client import PublishManager
        video = tmp_path / "v.mp4"
        video.write_bytes(b"\x00")

        pm = PublishManager(enabled=True, api_key="k", username="u",
                            default_platforms=["tiktok"])

        mock_resp = _make_response(200, {"request_id": "pub1"})
        with patch("requests.post", return_value=mock_resp):
            result = pm.publish(str(video), "My Title")

        assert result["request_id"] == "pub1"

    def test_from_settings_reads_config(self, mock_settings):
        from app.services.publish.upload_post_client import PublishManager
        mock_settings.UPLOAD_POST_ENABLED = False
        mock_settings.UPLOAD_POST_API_KEY = ""
        mock_settings.UPLOAD_POST_USERNAME = ""
        mock_settings.UPLOAD_POST_PLATFORMS = ["tiktok"]

        with patch("app.config.get_settings", return_value=mock_settings):
            pm = PublishManager.from_settings()

        assert pm.enabled is False

    def test_from_settings_creates_client_when_enabled(self, mock_settings):
        from app.services.publish.upload_post_client import PublishManager
        mock_settings.UPLOAD_POST_ENABLED = True
        mock_settings.UPLOAD_POST_API_KEY = "real_key"
        mock_settings.UPLOAD_POST_USERNAME = "user1"
        mock_settings.UPLOAD_POST_PLATFORMS = ["tiktok"]

        with patch("app.config.get_settings", return_value=mock_settings):
            pm = PublishManager.from_settings()

        assert pm.enabled is True
        assert pm._client is not None
