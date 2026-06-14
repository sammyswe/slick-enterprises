"""Tests for plan-driven operational workflow decomposition."""

from slick_shared.ops_workflow import (
    default_ops_state,
    extract_ops_questions,
    fallback_decompose,
    match_operating_workflow,
    parse_decompose_response,
    workflow_to_steps,
)


def _sample_plan():
    return {
        "name": "Test Biz",
        "slug": "test-biz",
        "operating_loop": ["sense", "decide", "act", "verify"],
        "agents": [
            {"role": "business-manager", "name": "BM", "concern": "orchestration"},
            {"role": "lead-researcher", "name": "Researcher", "concern": "research"},
            {"role": "operator", "name": "Operator", "concern": "ops"},
            {"role": "qa", "name": "QA", "concern": "quality"},
        ],
        "operating_workflows": [
            {
                "id": "default-cycle",
                "trigger_phrases": ["run cycle"],
                "steps": [
                    {"agent_role": "lead-researcher", "title": "Research", "concern": "gather"},
                    {"agent_role": "operator", "title": "Execute", "concern": "act"},
                    {"agent_role": "qa", "title": "Verify", "task_type": "verify"},
                ],
            }
        ],
    }


def test_match_operating_workflow():
    plan = _sample_plan()
    wf = match_operating_workflow(plan, "please run cycle for this week")
    assert wf is not None
    assert wf["id"] == "default-cycle"


def test_workflow_to_steps():
    plan = _sample_plan()
    wf = plan["operating_workflows"][0]
    steps = workflow_to_steps(wf)
    assert len(steps) == 3
    assert steps[0]["agent_role"] == "lead-researcher"


def test_fallback_decompose():
    plan = _sample_plan()
    steps = fallback_decompose(plan, "find opportunities")
    assert len(steps) >= 1
    assert all(s["agent_role"] != "business-manager" for s in steps)


def test_parse_decompose_response():
    text = '{"steps": [{"agent_role": "operator", "title": "Do thing", "description": "x"}]}'
    steps = parse_decompose_response(text)
    assert len(steps) == 1
    assert steps[0]["agent_role"] == "operator"


def test_extract_ops_questions():
    text = "1. What is the goal?\n2. Any budget limits?\n3. When is it due?"
    qs = extract_ops_questions(text)
    assert len(qs) == 3


def test_default_ops_state():
    state = default_ops_state()
    assert state["mode"] == "idle"
    assert state["pending_questions"] == []
