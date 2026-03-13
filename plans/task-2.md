# Task 2 Plan

## Goal
Extend the agent with tools to read project documentation.

## Tools
1. list_files(path)
Lists files in a directory.

2. read_file(path)
Reads the content of a file.

## Agentic Loop

1. Send user question + tool schemas to LLM
2. If LLM returns tool_calls:
   - execute tools
   - append results as messages
   - send back to LLM
3. If LLM returns text answer:
   - output JSON result
4. Stop after max 10 tool calls.

## Security
- Prevent "../" path traversal
- Restrict tools to project directory