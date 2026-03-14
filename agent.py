import sys
import json
import os
import re
import urllib.request
import urllib.error
from pathlib import Path
from dotenv import dotenv_values

PROJECT_ROOT = Path(__file__).parent.resolve()
MAX_TOOL_CALLS = 15
MAX_CORRECTIONS = 3


def load_env():
    env = {**dotenv_values(".env.agent.secret"), **dotenv_values(".env.docker.secret")}
    env.update(os.environ)
    return env


# ─── Tool implementations ─────────────────────────────────────────────────────

def safe_path(path):
    p = (PROJECT_ROOT / path).resolve()
    if not str(p).startswith(str(PROJECT_ROOT)):
        return None
    return p


def tool_read_file(path):
    p = safe_path(path)
    if not p:
        return "Error: access denied (path outside project root)"
    try:
        return p.read_text(encoding="utf-8")
    except FileNotFoundError:
        return f"Error: file not found: {path}"
    except Exception as e:
        return f"Error: {e}"


def tool_list_files(path):
    p = safe_path(path)
    if not p:
        return "Error: access denied (path outside project root)"
    try:
        entries = sorted(f.name for f in p.iterdir())
        return "\n".join(entries)
    except FileNotFoundError:
        return f"Error: directory not found: {path}"
    except Exception as e:
        return f"Error: {e}"


def tool_query_api(env, method, path, body=None, no_auth=False):
    base = env.get("AGENT_API_BASE_URL", "http://localhost:42002").rstrip("/")
    url = f"{base}{path}"
    data = body.encode("utf-8") if body else None
    headers = {"Content-Type": "application/json"}
    if not no_auth:
        headers["Authorization"] = f"Bearer {env.get('LMS_API_KEY', '')}"
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.dumps({"status_code": resp.status, "body": resp.read().decode()})
    except urllib.error.HTTPError as e:
        return json.dumps({"status_code": e.code, "body": e.read().decode()})
    except Exception as e:
        return json.dumps({"error": str(e)})


# ─── Tool schemas ─────────────────────────────────────────────────────────────

TOOL_SCHEMAS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Read the contents of a file from the project repository. "
                "Use this to inspect source code, config files, or wiki documentation."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path from project root, e.g. 'wiki/git-workflow.md' or 'backend/app/main.py'.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "List files and directories at a path inside the project repository. "
                "Use ONLY for discovery — always follow up with read_file to read the actual contents."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative directory path from project root, e.g. 'wiki' or 'backend/app/routers'.",
                    }
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "query_api",
            "description": (
                "Send an HTTP request to the deployed backend API. "
                "Use for ALL questions about live data: item counts, scores, analytics, completion rates, etc. "
                "Also use to check API behaviour like status codes and authentication. "
                "Returns JSON with 'status_code' and 'body'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "method": {
                        "type": "string",
                        "description": "HTTP method: GET, POST, PUT, DELETE, PATCH.",
                    },
                    "path": {
                        "type": "string",
                        "description": "API path with optional query string, e.g. '/items/' or '/analytics/completion-rate?lab=lab-04'.",
                    },
                    "no_auth": {
                        "type": "boolean",
                        "description": "Set true to send WITHOUT Authorization header. Use when testing unauthenticated requests.",
                    },
                    "body": {
                        "type": "string",
                        "description": "Optional JSON request body string (for POST/PUT).",
                    },
                },
                "required": ["method", "path"],
            },
        },
    },
]


# ─── System prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful assistant for a software engineering course project.
You have three tools: list_files, read_file, query_api.

## RULES (follow strictly)

1. ALWAYS call at least one tool before giving your final answer. No exceptions.
2. NEVER say "I need to...", "I will...", "Let me..." — just call the tool immediately.
3. After list_files, you MUST call read_file on the relevant file before answering.
4. NEVER answer from memory or assumptions — use tools to verify everything.

## Tool selection guide

- Wiki/documentation questions:
  list_files("wiki"), then read_file on the right file

- Source code / framework questions:
  read_file on relevant files (e.g. backend/app/main.py)

- Architecture / request lifecycle / deployment:
  read_file("docker-compose.yml"), read_file("Dockerfile") or read_file("backend/Dockerfile"),
  read_file("backend/app/main.py"), read_file("frontend/Caddyfile") — read ALL of these

- Live data (counts, scores, analytics):
  query_api — NEVER guess numbers

- HTTP status / auth behaviour:
  query_api; use no_auth=true for unauthenticated requests

- Debugging errors:
  query_api to get the error, then read_file on the source code

- Router modules:
  list_files("backend/app/routers"), then read_file each .py file

## Output format (MANDATORY)

After using tools, your ENTIRE response must be this JSON and nothing else:
{"answer": "your answer as plain text", "source": "file path or api path or empty string"}

- Start with { end with } — no prose before or after, no markdown fences
- "answer" must be a plain string (never a list or object)
- "source" must be a string"""


# ─── LLM call ─────────────────────────────────────────────────────────────────

def call_llm(env, messages):
    api_key = env.get("LLM_API_KEY", "")
    api_base = env.get("LLM_API_BASE", "https://api.openai.com/v1").rstrip("/")
    model = env.get("LLM_MODEL", "gpt-4o-mini")

    payload = {
        "model": model,
        "messages": messages,
        "tools": TOOL_SCHEMAS,
        "tool_choice": "auto",
        "max_tokens": 2048,
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    req = urllib.request.Request(
        f"{api_base}/chat/completions",
        data=data,
        method="POST",
        headers=headers,
    )

    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        print(f"LLM HTTP error {e.code}: {body}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"LLM request failed: {e}", file=sys.stderr)
        sys.exit(1)


# ─── JSON extraction ──────────────────────────────────────────────────────────

def extract_json(content):
    """Try multiple strategies to extract answer JSON from LLM content."""
    # 1) Whole content as JSON
    try:
        p = json.loads(content)
        if isinstance(p, dict) and "answer" in p:
            return p
    except json.JSONDecodeError:
        pass

    # 2) Fenced block
    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", content, re.DOTALL)
    if m:
        try:
            p = json.loads(m.group(1))
            if isinstance(p, dict) and "answer" in p:
                return p
        except json.JSONDecodeError:
            pass

    # 3) Last simple {...} block with "answer" key
    for block in reversed(list(re.finditer(r"\{[^{}]*\}", content, re.DOTALL))):
        try:
            p = json.loads(block.group())
            if isinstance(p, dict) and "answer" in p:
                return p
        except json.JSONDecodeError:
            continue

    # 4) Substring from last {"answer"
    idx = content.rfind('{"answer"')
    if idx != -1:
        try:
            p = json.loads(content[idx:])
            if isinstance(p, dict):
                return p
        except json.JSONDecodeError:
            pass

    return None


# ─── Agentic loop ─────────────────────────────────────────────────────────────

PLAN_PHRASES = [
    "i need to", "i will ", "let me ", "i'll read", "i'll check",
    "i'll look", "i'll examine", "i'll query", "i'll call", "i'll start",
    "i'll explore", "i'll investigate", "i should ",
]


def run_agent(env, question):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]

    tool_calls_log = []
    total_calls = 0
    correction_attempts = 0

    while total_calls < MAX_TOOL_CALLS:
        print(f"[agent] calling LLM (turn {total_calls + 1})", file=sys.stderr)
        response = call_llm(env, messages)

        choice = response["choices"][0]
        msg = choice["message"]
        messages.append(msg)

        has_tool_calls = bool(msg.get("tool_calls"))

        # ── Execute tool calls ────────────────────────────────────────────────
        if has_tool_calls:
            tool_results = []
            for tc in msg.get("tool_calls", []):
                if total_calls >= MAX_TOOL_CALLS:
                    break
                total_calls += 1
                tc_id = tc["id"]
                fn_name = tc["function"]["name"]
                try:
                    fn_args = json.loads(tc["function"]["arguments"])
                except json.JSONDecodeError:
                    fn_args = {}

                print(f"[agent] tool: {fn_name}({fn_args})", file=sys.stderr)

                if fn_name == "read_file":
                    result = tool_read_file(fn_args.get("path", ""))
                elif fn_name == "list_files":
                    result = tool_list_files(fn_args.get("path", ""))
                elif fn_name == "query_api":
                    result = tool_query_api(
                        env,
                        fn_args.get("method", "GET"),
                        fn_args.get("path", "/"),
                        fn_args.get("body"),
                        fn_args.get("no_auth", False),
                    )
                else:
                    result = f"Error: unknown tool '{fn_name}'"

                print(f"[agent] result: {result[:200]}", file=sys.stderr)
                tool_calls_log.append({"tool": fn_name, "args": fn_args, "result": result[:1000]})
                tool_results.append({"role": "tool", "tool_call_id": tc_id, "content": result})

            messages.extend(tool_results)
            continue

        # ── No tool calls — potential final answer ────────────────────────────
        content = re.sub(r"<think>.*?</think>", "", (msg.get("content") or ""), flags=re.DOTALL).strip()

        # Guard 1: No tools used at all
        if not tool_calls_log:
            print("[agent] no tools used yet — forcing tool use", file=sys.stderr)
            messages.append({
                "role": "user",
                "content": "You have not called any tools yet. Call a tool RIGHT NOW — do not explain, just act."
            })
            continue

        # Guard 2: Last tool was list_files — must read a file before answering
        if tool_calls_log[-1]["tool"] == "list_files":
            last_result = tool_calls_log[-1].get("result", "")
            print("[agent] last tool was list_files — forcing read_file", file=sys.stderr)
            messages.append({
                "role": "user",
                "content": f"You must call read_file on a relevant file before answering. Files available:\n{last_result}"
            })
            continue

        # Guard 3: Response looks like a plan, not an answer
        if any(p in content.lower() for p in PLAN_PHRASES):
            print("[agent] LLM gave a plan — forcing tool use", file=sys.stderr)
            messages.append({
                "role": "user",
                "content": "Stop planning. Call a tool RIGHT NOW."
            })
            continue

        # Try to extract JSON answer
        parsed = extract_json(content)
        if parsed is not None:
            raw_answer = parsed.get("answer", content)
            if isinstance(raw_answer, (dict, list)):
                raw_answer = json.dumps(raw_answer)
            return {
                "answer": str(raw_answer),
                "source": str(parsed.get("source", "") or ""),
                "tool_calls": tool_calls_log,
            }

        # No JSON found — request correction
        correction_attempts += 1
        if correction_attempts > MAX_CORRECTIONS:
            return {"answer": content, "source": "", "tool_calls": tool_calls_log}

        print(f"[agent] prose response — requesting JSON correction ({correction_attempts}/{MAX_CORRECTIONS})", file=sys.stderr)
        messages.append({
            "role": "user",
            "content": (
                'Respond with JSON only:\n'
                '{"answer": "your answer here", "source": "file path or empty string"}\n'
                'Start with { and end with }. Nothing else.'
            )
        })

    print("[agent] hit max tool calls", file=sys.stderr)
    return {"answer": "Unable to determine answer within tool call limit.", "source": "", "tool_calls": tool_calls_log}


# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    env = load_env()
    if len(sys.argv) < 2:
        print("Usage: uv run agent.py \"<question>\"", file=sys.stderr)
        sys.exit(1)
    question = sys.argv[1]
    print(f"[agent] question: {question}", file=sys.stderr)
    result = run_agent(env, question)
    print(json.dumps(result))


if __name__ == "__main__":
    main()