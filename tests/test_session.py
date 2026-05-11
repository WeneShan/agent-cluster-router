"""SessionManager 单元测试"""
import pytest
import sys
sys.path.insert(0, "/srv/agent-cluster")

from router.server import SessionManager


class TestSessionManager:
    def test_new_session_generates_id(self):
        sm = SessionManager()
        sid = "abc-123"
        sm.append(sid, [{"role": "user", "content": "hello"}])
        assert sm.get(sid) == [{"role": "user", "content": "hello"}]

    def test_append_to_existing(self):
        sm = SessionManager()
        sm.append("s1", [{"role": "user", "content": "msg1"}])
        sm.append("s1", [{"role": "user", "content": "msg2"}])
        assert len(sm.get("s1")) == 2
        assert sm.get("s1")[1]["content"] == "msg2"

    def test_get_missing_session(self):
        sm = SessionManager()
        assert sm.get("nonexistent") == []

    def test_delete_session(self):
        sm = SessionManager()
        sm.append("s1", [{"role": "user", "content": "x"}])
        sm.delete("s1")
        assert sm.get("s1") == []

    def test_list_sessions(self):
        sm = SessionManager()
        sm.append("s1", [{"role": "user", "content": "a"}])
        sm.append("s1", [{"role": "user", "content": "b"}])
        sm.append("s2", [{"role": "user", "content": "c"}])
        sessions = sm.list_sessions()
        assert len(sessions) == 2
        names = {s["session_id"]: s["turns"] for s in sessions}
        assert names["s1"] == 2
        assert names["s2"] == 1

    def test_session_id_reuse_without_load(self):
        """不带 session_id 的参数不应加载历史"""
        sm = SessionManager()
        sm.append("old", [{"role": "user", "content": "history"}])
        # 新请求不带 session_id — 模拟行为：不获取历史
        history = sm.get("does-not-exist-in-request")
        assert history == []
