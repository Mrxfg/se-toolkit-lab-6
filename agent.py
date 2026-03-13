import sys
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")

MAX_TOOL_CALLS = 10


def list_files(path):
    if ".." in path:
        return "Error: invalid path"

    try:
        return "\n".join(os.listdir(path))
    except Exception as e:
        return str(e)


def read_file(path):
    if ".." in path:
        return "Error: invalid path"

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return str(e)


tools = [
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files in a directory",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the repository",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"}
                },
                "required": ["path"]
            }
        }
    }
]


def call_llm(messages):
    response = requests.post(
        f"{API_BASE}/chat/completions",
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": MODEL,
            "messages": messages,
            "tools": tools
        },
        timeout=60
    )

    return response.json()


def main():

    if len(sys.argv) < 2:
        print("Question required", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    messages = [
        {"role": "system", "content": "Use list_files to explore wiki and read_file to read documentation."},
        {"role": "user", "content": question}
    ]

    tool_calls_log = []

    for _ in range(MAX_TOOL_CALLS):

        data = call_llm(messages)

        if "choices" not in data:
            print(data, file=sys.stderr)
            sys.exit(1)

        message = data["choices"][0]["message"]

        if "tool_calls" not in message:
            answer = message.get("content", "")
            output = {
                "answer": answer,
                "source": "",
                "tool_calls": tool_calls_log
            }
            print(json.dumps(output))
            return

        for call in message["tool_calls"]:

            name = call["function"]["name"]
            args = json.loads(call["function"]["arguments"])

            if name == "list_files":
                result = list_files(**args)

            elif name == "read_file":
                result = read_file(**args)

            else:
                result = "Unknown tool"

            tool_calls_log.append({
                "tool": name,
                "args": args,
                "result": result
            })

            messages.append(message)

            messages.append({
                "role": "tool",
                "tool_name": name,
                "content": result
            })

    output = {
        "answer": "Max tool calls reached",
        "source": "",
        "tool_calls": tool_calls_log
    }

    print(json.dumps(output))

if __name__ == "__main__":
    main()