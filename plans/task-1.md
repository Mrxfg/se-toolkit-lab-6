# Task 1 Plan

## LLM Provider
Qwen Code API

## Model
qwen3-coder-plus

## Architecture
User Question → agent.py → Qwen API → JSON Output

## Steps
1. Parse command-line argument (user question)
2. Load environment variables from `.env.agent.secret`
3. Send request to OpenAI-compatible API
4. Extract the answer from the response
5. Output JSON with fields:
   - answer
   - tool_calls