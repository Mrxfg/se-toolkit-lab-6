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

## System Agent

In Task 3 the agent was extended with a new tool called `query_api`.
This tool allows the agent to communicate with the deployed backend
service instead of relying only on the documentation.

Previously the agent could only use the following tools:

- `list_files` — explore repository directories
- `read_file` — read documentation files

However documentation may become outdated. The real system state
exists in the backend service, therefore the agent must be able to
query the API directly.

### query_api tool

The `query_api` tool sends HTTP requests to the deployed backend API.

Parameters:
- method — HTTP method (GET, POST)
- path — endpoint path (example: `/items/`)
- body — optional JSON request body

The tool authenticates using the `LMS_API_KEY` environment variable.
The backend base URL is read from `AGENT_API_BASE_URL`. If the variable
is not set the agent uses `http://localhost:42002`.

The tool returns a JSON string containing:

- status_code
- body

Example:
{
"status_code": 200,
"body": "[{...}]"
}
### Tool selection strategy

The system prompt instructs the LLM to select tools depending on the
question type:

Documentation questions:
- use `list_files`
- then `read_file`

System questions:
- use `query_api`

Code questions:
- use `read_file`

### Benchmark

The agent was evaluated using `run_eval.py`, which runs 10 local
benchmark questions that cover documentation queries, system
information questions and data dependent queries.

The agent iteratively improves its answers by combining multiple
tool calls inside the agentic loop.