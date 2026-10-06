# Requirement: F-3
import asyncio
import json
import time
from datetime import datetime, timezone

from customer_briefing.adapter.outbound.model_briefing_adapter import ModelBriefingAdapter
from hub.app.dtos.customer_briefing_dto import (
    BriefingComposition, BriefingFacts, BriefingPurpose, PriorCall,
)
from hub.app.ports.output.customer_briefing_port import CustomerBriefingPort

T = datetime(2026, 10, 5, 5, 2, tzinfo=timezone.utc)
FACTS = BriefingFacts("now", True, (PriorCall(call_id="p1", started_at=T, inquiry_type="상하수도",
                                              summary_text="단수 처리 지연 문의", summary_confirmed=True,
                                              open_follow_ups=("담당 부서 회신",)),))
RULE = BriefingComposition(BriefingPurpose("후속 확인", "규칙 문장", "rule"), ("규칙 줄",))


class _Rule(CustomerBriefingPort):
    async def compose(self, facts):
        return RULE


class _Chat:
    model = "m"

    def __init__(self, payload=None, fail=False, delay=0.0):
        self.payload, self.fail, self.delay, self.calls = payload, fail, delay, 0

    def chat(self, messages, *, schema=None):
        self.calls += 1
        time.sleep(self.delay)
        if self.fail:
            raise OSError("down")

        class R:  # ChatResult 와 같은 모양
            content = json.dumps(self.payload, ensure_ascii=False)
        return R()


def _good(**over):
    p = {"category": "컴플레인", "purpose": "회신이 없어 다시 건 것으로 보입니다", "lines": ["지난 통화 10-05 상하수도"]}
    p.update(over)
    return p


def _run(adapter):
    return asyncio.run(adapter.compose(FACTS))


def test_model_output_used_when_clean():
    c = _run(ModelBriefingAdapter(_Rule(), chat=_Chat(_good())))
    assert c.purpose.source == "model" and c.purpose.category == "컴플레인"


def test_out_of_list_category_falls_back():
    assert _run(ModelBriefingAdapter(_Rule(), chat=_Chat(_good(category="서류보완")))) == RULE


def test_invented_digit_falls_back():
    assert _run(ModelBriefingAdapter(_Rule(), chat=_Chat(_good(purpose="7일째 지연으로 보입니다")))) == RULE


def test_broken_json_and_errors_fall_back():
    class Bad(_Chat):
        def chat(self, messages, *, schema=None):
            class R:
                content = "그냥 문장"
            return R()
    assert _run(ModelBriefingAdapter(_Rule(), chat=Bad())) == RULE
    assert _run(ModelBriefingAdapter(_Rule(), chat=_Chat(fail=True))) == RULE


def test_timeout_falls_back():
    a = ModelBriefingAdapter(_Rule(), chat=_Chat(_good(), delay=0.3), timeout_s=0.05)
    assert _run(a) == RULE


def test_no_chat_is_rule():
    assert _run(ModelBriefingAdapter(_Rule(), chat=None)) == RULE
