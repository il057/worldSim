from fastapi.testclient import TestClient
from app.main import app


def test_full_pipeline():
    with TestClient(app) as client:
        # 1. 健康检查
        health_res = client.get("/api/health")
        assert health_res.status_code == 200
        assert health_res.json()["status"] == "ok"

        # 2. 检查默认角色与列表
        chars_res = client.get("/api/v1/characters")
        assert chars_res.status_code == 200
        chars = chars_res.json()
        assert len(chars) >= 1
        char_id = chars[0]["id"]
        print(f"Loaded character: {chars[0]['name']} (ID: {char_id})")

        # 3. 检查角色详情与看板
        detail_res = client.get(f"/api/v1/characters/{char_id}/detail")
        assert detail_res.status_code == 200
        detail = detail_res.json()
        assert "name" in detail
        assert "circadian_profile" in detail
        assert "chronotype" in detail["circadian_profile"]

        # 4. 测试时间线流水拉取
        time_res = client.get(f"/api/v1/characters/{char_id}/timeline")
        assert time_res.status_code == 200
        timeline = time_res.json()
        assert timeline["total"] >= 0
        print(f"Initial timeline slices count: {timeline['total']}")

        # 5. 测试单步推演 (+1h)
        step_res = client.post("/api/v1/sim/step", json={"character_id": char_id, "hours": 1})
        assert step_res.status_code == 200
        step_data = step_res.json()
        assert "story_log" in step_data
        assert "current_state" in step_data
        assert len(step_data["story_log"]["narrative_prose"]) > 0
        print(f"Step successful: Tick #{step_data['story_log']['tick_index']}, Prose length: {len(step_data['story_log']['narrative_prose'])}")

        # 6. 测试阶段快进 (+6h)
        ff_res = client.post("/api/v1/sim/fast-forward", json={"character_id": char_id, "step_type": "hour_6"})
        assert ff_res.status_code == 200
        ff_data = ff_res.json()
        assert "story_log" in ff_data
        print(f"Fast forward successful: New virtual time: {ff_data['current_state']['virtual_time']}")

        # 7. 测试纯按钮突发事件触发 (无用户文本输入)
        incident_res = client.post("/api/v1/sim/trigger-incident", json={"character_id": char_id})
        assert incident_res.status_code == 200
        incident_data = incident_res.json()
        assert "story_log" in incident_data
        print(f"Incident triggered successfully: {incident_data['story_log']['plot_beat']}")

        # 8. 测试极简表单 AI 快速衍生
        quick_res = client.post("/api/v1/characters/generate-quick", json={
            "name": "达里尔",
            "role": "密函信使",
            "archetype": "警觉敏捷，少言寡语",
            "initial_situation": "暴风雪中在旧灯塔外避难",
        })
        assert quick_res.status_code == 201
        new_char_id = quick_res.json()["character_id"]
        print(f"Quick character created: {new_char_id}")

        # 9. 测试静态 SPA 通配回退
        spa_res = client.get("/")
        assert spa_res.status_code == 200
        assert "text/html" in spa_res.headers.get("content-type", "")

        print("\nAll integration tests passed successfully!")


if __name__ == "__main__":
    test_full_pipeline()
