import sys
import json
import os
import requests
from dotenv import load_dotenv

load_dotenv(".env.agent.secret")

API_KEY = os.getenv("LLM_API_KEY")
API_BASE = os.getenv("LLM_API_BASE")
MODEL = os.getenv("LLM_MODEL")


def main():

    if len(sys.argv) < 2:
        print("Question required", file=sys.stderr)
        sys.exit(1)

    question = sys.argv[1]

    try:
        response = requests.post(
            f"{API_BASE}/chat/completions",
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": MODEL,
                "messages": [
                    {"role": "user", "content": question}
                ]
            },
            timeout=60
        )

        data = response.json()

        if "choices" not in data:
            print(data, file=sys.stderr)
            sys.exit(1)

        answer = data["choices"][0]["message"]["content"]

        output = {
            "answer": answer,
            "tool_calls": []
        }

        print(json.dumps(output))

    except Exception as e:
        print(str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()