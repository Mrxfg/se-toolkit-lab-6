import subprocess
import json


def test_merge_conflict_question():

    result = subprocess.run(
        ["uv", "run", "agent.py", "How do you resolve a merge conflict?"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    assert "answer" in data
    assert "tool_calls" in data
    assert isinstance(data["tool_calls"], list)


def test_list_wiki_files():

    result = subprocess.run(
        ["uv", "run", "agent.py", "What files are in the wiki?"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    assert "tool_calls" in data