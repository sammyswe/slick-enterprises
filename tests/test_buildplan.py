"""Tests for the build-plan contract: parsing, fallback, and DAG waves."""

from slick_shared.buildplan import (
    compute_waves,
    extract_json_object,
    fallback_plan,
    iter_tasks,
    parse_plan,
    ready_tasks,
)

VALID_PLAN = """
Here is the plan:
```json
{
  "name": "Lead Scraper Pro",
  "slug": "lead-scraper-pro",
  "vision": "Scrape and sell qualified B2B leads.",
  "stack": ["Python", "FastAPI", "Postgres"],
  "agents": [
    {"role": "backend", "name": "API Engineer", "responsibility": "API + data"},
    {"role": "qa", "name": "Test Engineer", "responsibility": "tests"}
  ],
  "milestones": [
    {"id": "m1", "title": "Foundations", "tasks": [
      {"id": "t1", "title": "Scaffold", "agent_role": "backend", "depends_on": [],
       "acceptance_criteria": ["installs"], "verify_commands": ["pytest -q"]}
    ]},
    {"id": "m2", "title": "Feature", "tasks": [
      {"id": "t2", "title": "Scraper", "agent_role": "backend", "depends_on": ["t1"],
       "acceptance_criteria": ["scrapes"], "verify_commands": ["pytest -q"]},
      {"id": "t3", "title": "Tests", "agent_role": "qa", "depends_on": ["t1"],
       "acceptance_criteria": ["pass"], "verify_commands": ["pytest -q"]}
    ]}
  ]
}
```
"""


def test_parse_valid_fenced_plan():
    plan = parse_plan(VALID_PLAN, default_name="X", default_slug="x", idea="idea")
    assert plan is not None
    assert plan["name"] == "Lead Scraper Pro"
    assert plan["slug"] == "lead-scraper-pro"
    assert len(plan["agents"]) == 2
    tasks = iter_tasks(plan)
    assert [t["id"] for t in tasks] == ["t1", "t2", "t3"]


def test_parse_returns_none_without_json():
    assert parse_plan("no json here, just prose", default_name="X", default_slug="x", idea="i") is None


def test_extract_json_object_balances_braces():
    obj = extract_json_object('prefix {"a": {"b": 1}} suffix')
    assert obj == {"a": {"b": 1}}


def test_normalize_drops_bad_dependencies_and_dedups():
    raw = {
        "name": "N",
        "slug": "n",
        "milestones": [
            {"id": "m1", "tasks": [
                {"id": "t1", "title": "A", "depends_on": ["ghost"]},
                {"id": "t1", "title": "B", "depends_on": ["t1"]},
            ]}
        ],
    }
    import json

    plan = parse_plan(json.dumps(raw), default_name="N", default_slug="n", idea="i")
    tasks = iter_tasks(plan)
    ids = [t["id"] for t in tasks]
    assert len(ids) == len(set(ids))  # duplicate id was made unique
    # The ghost dependency was dropped because it isn't a known task id.
    assert tasks[0]["depends_on"] == []


def test_fallback_plan_is_well_formed():
    plan = fallback_plan(name="Acme", slug="acme", idea="do a thing")
    assert plan["name"] == "Acme"
    assert plan["agents"]
    assert plan["milestones"]
    for t in iter_tasks(plan):
        assert t["title"]
        assert isinstance(t["depends_on"], list)


def test_ready_tasks_respects_dependencies():
    tasks = [
        {"id": "t1", "depends_on": []},
        {"id": "t2", "depends_on": ["t1"]},
        {"id": "t3", "depends_on": ["t1"]},
    ]
    assert [t["id"] for t in ready_tasks(tasks, set())] == ["t1"]
    after_t1 = {t["id"] for t in ready_tasks(tasks, {"t1"})}
    assert after_t1 == {"t2", "t3"}


def test_compute_waves_parallelizes_independent_tasks():
    tasks = [
        {"id": "t1", "depends_on": []},
        {"id": "t2", "depends_on": ["t1"]},
        {"id": "t3", "depends_on": ["t1"]},
        {"id": "t4", "depends_on": ["t2", "t3"]},
    ]
    waves = compute_waves(tasks)
    assert waves[0] == ["t1"]
    assert set(waves[1]) == {"t2", "t3"}  # independent -> same wave
    assert waves[2] == ["t4"]


def test_compute_waves_breaks_cycles_without_deadlock():
    tasks = [
        {"id": "a", "depends_on": ["b"]},
        {"id": "b", "depends_on": ["a"]},
    ]
    waves = compute_waves(tasks)
    # A cycle can't be ordered; everything still surfaces in a final wave.
    flat = [tid for wave in waves for tid in wave]
    assert set(flat) == {"a", "b"}
