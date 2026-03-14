import subprocess
import json


def test_framework_question():

    result = subprocess.run(
        ["uv", "run", "agent.py", "What framework does the backend use?"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    assert "answer" in data
    assert "tool_calls" in data


def test_items_query():

    result = subprocess.run(
        ["uv", "run", "agent.py", "How many items are in the database?"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    assert "tool_calls" in data