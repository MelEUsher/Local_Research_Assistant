# API Documentation

## GoogleSearchService
Handles Google Custom Search API calls with retries, caching, and credential validation.

**Key methods**

- `search(query: str, num_results: int = 5) -> List[Dict[str, str]]`
  - Performs a search request with `num_results` capped at 10 per request.
  - Retries transient errors via `retry_with_backoff` and raises `RateLimitError` for quota problems.
- `format_results_for_llm(results)`
  - Renders each result as Markdown that Ollama can consume.
- `test_connection()`
  - Sends a tiny request to confirm the configured API key and CSE ID work before performing larger workflows.

**Usage example**
```python
from search_service import GoogleSearchService

search_service = GoogleSearchService()
results = search_service.search("AI accountability trends", num_results=3)
formatted = search_service.format_results_for_llm(results)
```

## OllamaLLMService
Wraps the Ollama LangChain integration and adds validation/formatting helpers.

**Key methods**

- `__init__(model_name=None, base_url=None)`
  - Verifies the Ollama server and requested model exist, raising `ConnectionError` or `ValueError` if not.
- `verify_connection() -> bool`
  - Contacts `/api/models` to ensure the service is reachable and the model is listed.
- `summarize_search_results(query, search_results, num_facts=3)`
  - Builds a prompt that asks for a structured summary and citations, then invokes the Ollama LLM.
- `refine_query(research_request)`
  - Converts the user's query into a concise search string optimized for `GoogleSearchService`.

**Usage example**
```python
from llm_service import OllamaLLMService

llm_service = OllamaLLMService()
refined_query = llm_service.refine_query("Explain recent AI regulations")
summary = llm_service.summarize_search_results("Explain recent AI regulations", formatted_results, num_facts=4)
```

## ExportService
Exports workflow output to Markdown or JSON while sanitizing filenames and directories.

**Key methods**

- `save_to_markdown(result: str, filename: str, directory=None)`
  - Writes the formatted Markdown to the given directory (default `outputs/`).
- `save_to_json(state: dict, filename: str, directory=None)`
  - Dumps the full workflow state for downstream analysis or rehydration.
- `auto_generate_filename(query: str) -> str`
  - Builds a safe filename combining the sanitized query and a timestamp.

**Usage example**
```python
from export_service import ExportService

export_service = ExportService()
markdown_path = export_service.save_to_markdown(summary, "AI_summary")
json_path = export_service.save_to_json(workflow_state, "AI_summary")
```

## ResearchState (TypedDict)
Defines the shape of the LangGraph workflow state so nodes share the same typed fields:

| Field | Description |
| --- | --- |
| `original_query` | Original text entered by the user. |
| `refined_query` | LLM-generated search-optimized query. |
| `search_results` | List of dictionaries containing `title`, `link`, and `snippet`. |
| `formatted_results` | String prepared for the LLM summarizer. |
| `summary` | Ollama-generated summary or facts section. |
| `output` | Final Markdown output returned by `ResearchWorkflow.run`. |
| `export_filename` | File path generated when `--export` is used. |

## ResearchWorkflow
Coordinates the LangGraph nodes and services to produce final research output.

**Key properties/methods**

- `run(research_request: str, use_cache: bool = True, auto_export: bool = False) -> str`
  - Drives the state graph and optionally exports Markdown/JSON when `auto_export` is true.
  - Raises `ValueError` for empty or overly long queries (>500 characters).
  - Respects `use_cache` to reuse cached search results and summaries.
- `last_state` (property)
  - Allows callers to inspect the final `ResearchState` after `run` finishes.

**Usage example**
```python
from workflow import ResearchWorkflow
from export_service import ExportService

workflow = ResearchWorkflow(export_service=ExportService())
output = workflow.run("Describe quantum computing milestones", auto_export=True)
print(output)
```

## Configuration options
Configuration is handled via environment variables and validated by `ConfigValidator`.

| Variable | Default | Purpose |
| --- | --- | --- |
| `GOOGLE_API_KEY` | (required) | Enables Google Custom Search API calls. Must start with `AIza`. |
| `GOOGLE_CSE_ID` | (required) | Custom Search Engine identifier tied to the API key. |
| `OLLAMA_BASE_URL` | `http://localhost:11434` | URL for the Ollama service. Must be `http://` or `https://`. |
| `OLLAMA_MODEL` | `llama3.2` | Model name to invoke via Ollama. Contains only alphanumerics, dots, colons, underscores, or hyphens. |

Use `validate_config()` to return a dict with `valid`, `issues`, and `details` before invoking the workflow, or call `validate_google_credentials()` to block execution until both Google values are set.

## Export formats
- **Markdown**: Default output format from `ResearchWorkflow`. Saved under `outputs/`, sanitized filename via `ExportService._sanitize_name`, and suffixed with `.md`.
- **JSON**: Captures the full `ResearchState` for later inspection. JSON exports use the same sanitized base filename but append `.json`.

## Workflow diagram
```mermaid
graph TD
    A[User query] --> B[Refine query (LLM)]
    B --> C[Fetch sources (Google Search)]
    C --> D[Summarize (Ollama)]
    D --> E[Format output & optional export]
```

Adjust the LangGraph nodes or insert new ones via `workflow.py` if you need additional preprocessing or post-processing steps.
