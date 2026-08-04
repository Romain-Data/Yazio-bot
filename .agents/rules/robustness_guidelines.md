# Guidelines for Robust API Clients and Deployment Scripts

Follow these rules when writing API integration clients or system deployment scripts to ensure reliability and prevent silent failures.

## 1. Robust LLM and Third-Party API Clients
When integrating external LLM APIs (such as Mammouth AI, OpenAI, or Gemini) for structured JSON outputs:
* **Explicit Output Token Limits**: Always set `max_tokens` (or `max_completion_tokens`) explicitly to a high limit (e.g. `2048` or `4096`). Many API gateways default to low limits (e.g. `256` tokens) when omitted, causing truncated JSON outputs and Pydantic validation failures (`EOF while parsing`).
* **Timeouts**: Always set a timeout on HTTP requests (e.g., `timeout=60`) to avoid threads hanging indefinitely.
* **Automatic Retry Logic**: Implement a retry mechanism (e.g., up to 3 attempts) around the API call and JSON/Pydantic validation. This automatically handles temporary network drops, timeouts, or transient generation failures from the LLM.

## 2. Robust CI/CD and Remote Deployment Scripts (n8n/SSH/Docker)
When writing shell scripts to be executed remotely via orchestrators or SSH nodes:
* **Decoupled Background Tasks**: When launching a command in the background (`&`), always redirect both `stdout` and `stderr` (e.g. `> /dev/null 2>&1 &` or to a dedicated log file). Otherwise, the SSH session will remain open waiting for the background outputs to close.
* **Delayed Service Restarts**: If a deployment script needs to restart the service running the script itself (e.g. restarting the `n8n` container from a workflow run by `n8n`), run the restart asynchronously with a delay (e.g., `nohup bash -c "sleep 3 && docker restart n8n" >/dev/null 2>&1 &`). This gives the calling node enough time to receive the success code and terminate the connection cleanly before the service goes down.
* **Explicit Exit Codes**: Ensure script error paths use `exit 1` (or another non-zero code) so that the orchestrator is aware of the failure and can trigger appropriate notification systems (like email/Gmail alerts).
