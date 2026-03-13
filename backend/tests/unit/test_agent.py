import subprocess
import json

def test_agent():

    result = subprocess.run(
        ["uv", "run", "agent.py", "What is REST?"],
        capture_output=True,
        text=True
    )

    data = json.loads(result.stdout)

    assert "answer" in data
    assert "tool_calls" in data