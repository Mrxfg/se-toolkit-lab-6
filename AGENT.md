# Documentation Agent

This agent answers questions about the project documentation by using tools.

## Architecture

User Question → agent.py → LLM → Tool Call → Tool Execution → LLM → JSON Output

The agent uses an agentic loop:

1. Send the user question and tool schemas to the LLM
2. If the LLM returns tool_calls:
   - execute the tool
   - append the result to the conversation
   - send the updated messages back to the LLM
3. If the LLM returns a text response:
   - return the final JSON output

Maximum 10 tool calls are allowed.

## Tools

### list_files

Lists files in a directory.

Parameters:
- path (string)

Returns:
- newline-separated file list

Security:
- prevents `../` path traversal

### read_file

Reads the content of a file.

Parameters:
- path (string)

Returns:
- file content as string

Security:
- prevents reading files outside the project directory

## Run

```bash
uv run agent.py "How do you resolve a merge conflict?"