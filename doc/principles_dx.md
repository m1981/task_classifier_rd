## 1. The "Get Out of the Way" Principle
Developers use tools to ship code, not to admire the tool itself. The best tool is invisible until it is needed.

*   **Speed is a Feature:** Local hooks (pre-commit/pre-push) must run in milliseconds, not seconds. If a check takes >2 seconds, it belongs in CI, not on the local machine.
*   **Silence is Golden:** On success, print nothing or a single green checkmark. Do not spam `stdout` with "Checking file 1... Checking file 2..." unless `--verbose` is requested.
*   **The "Not My Job" Rule:** If a tool is configured to check Python files, and the user commits only CSS files, the tool must exit immediately with `0` (Success). Do not spin up heavy engines to check nothing.

## 2. Failure Modes: Fail Open vs. Fail Closed
How the tool behaves when *it* breaks (not when the code breaks) determines if developers will uninstall it.

*   **Fail Closed on Logic:** If the tool detects a genuine bug or security flaw in the code, it **must** block the process (Exit 1).
*   **Fail Open on Infrastructure:** If the tool crashes because the API is down, the internet is flaky, or a config file is unreadable, it should **Warn and Pass** (Exit 0).
    *   *Reasoning:* A developer should never be blocked from deploying a hotfix just because your linting server is down.
*   **The Escape Hatch:** Always provide a mechanism to bypass the tool without disabling it entirely.
    *   *Example:* `git commit -m "wip [skip-ai]"` or `aireview run --force`.

## 3. The "Sherlock Holmes" Debugging Rule
When a tool fails, the developer's immediate reaction is "Why?" and "How do I fix it?".

*   **Actionable Error Messages:** Never print "Error: Check failed."
    *   *Bad:* `Error: 400 Bad Request`
    *   *Good:* `Error: Invalid API Key. Please check your OPENAI_API_KEY environment variable.`
*   **The Dry Run:** Every integration tool must have a `--dry-run` flag. This allows the developer to see *what would happen* (what prompt is sent, what files are scanned) without actually triggering side effects or costs.
*   **Verbose Mode:** Always implement a `--verbose` or `-v` flag that reveals the internal state (paths resolved, commands executed) for debugging.

## 4. Configuration: Batteries Included, but Swappable
*   **Sensible Defaults:** The tool should run with zero configuration if possible.
*   **Config as Code:** Configuration (`ai-checks.yaml`) must live in the repository, not in the user's home folder. This ensures every developer on the team runs the exact same checks.
*   **Environment Variables for Secrets:** Never require secrets (API keys) in files. Always read from `os.environ`.

## 5. Idempotency and Determinism
*   **Same Input, Same Output:** Running the tool twice on the same code should produce the exact same result.
*   **No Ghost State:** Do not rely on hidden temp files that persist between runs. If you use a cache, provide a command to clear it (`aireview clean`).

## 6. The "Least Surprise" Principle
*   **Standard Arguments:** Use standard CLI flags.
    *   Use `--help`, `--version`, `--verbose`.
    *   Don't use `-p` for "print" if everyone expects it to mean "port" or "path".
*   **Respect the Ecosystem:** If you are a Python tool, respect `venv`. If you are a Node tool, respect `node_modules`. Don't try to reinvent package management.

## 7. Cost Awareness (Specific to AI Tools)
*   **Don't Burn Cash:** Never send a request to an LLM if the input hasn't changed. Implement hashing/caching of inputs.
*   **Context Window Safety:** Always check if the input size exceeds the model's context window *before* sending the request. Fail gracefully with a "File too large to review" warning rather than an API crash.

---