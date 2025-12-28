# Research Assistant with LangGraph Workflow

A customized research assistance system that uses LangGraph to orchestrate a multi-step workflow for fetching and summarizing information from the web.

## Features

- 📝 Takes natural-language research requests
- 🔍 Fetches information from the web using Google Search API
- 🤖 Uses Ollama (local LLM) for query refinement and summarization
- 🔄 LangGraph workflow orchestrates: refine query → fetch sources → summarize → output
- 📊 Returns structured, formatted output with citations

## New Features

- **Issue 1:** Source and search result caching now keeps repeated queries from hammering the Google Custom Search API.
- **Issue 2:** Summary caching with a capped ordered list lets repeated requests reuse earlier Ollama responses without extra prompts.
- **Issue 3:** `retry_with_backoff` wraps key service calls so rate limits and transient failures automatically retry.
- **Issue 4:** A `--check` flag reports configuration validity and exits before running the workflow.
- **Issue 5:** `--export` pairs with `ExportService` to persist results to Markdown and JSON with consistent filenames.
- **Issue 6:** Logging writes to `logs/research_assistant.log`, capturing DEBUG-level traces alongside console output.
- **Issue 7:** `ConfigValidator` now offers explicit feedback for Google and Ollama settings, reducing setup friction.
- **Issue 8:** `ResearchWorkflow` enforces request length bounds and uses the typed `ResearchState` throughout its nodes for safer transitions.
- **Issue 9:** Expanded documentation (README, CONTRIBUTING, API_DOCS) clarifies the full stack and developer expectations.

## Architecture

The system uses a LangGraph workflow with the following nodes:

1. **refine_query**: Refines the user's natural language request into an optimized search query
2. **fetch_sources**: Uses Google Custom Search API to fetch relevant web sources
3. **summarize**: Uses Ollama LLM to extract key facts and create a summary
4. **format_output**: Formats the results into a structured output with citations

## Setup

### Prerequisites

- Conda (recommended) or Python 3.10+
- Ollama installed and running locally (default: http://localhost:11434)
- A model installed in Ollama (default: llama3.2)
- Google Custom Search API key and Custom Search Engine ID

### Installation

#### Option 1: Using Conda (Recommended)

1. **Create and activate the conda environment:**
```bash
conda env create -f environment.yml
conda activate research_assistant
```

Alternatively, if you want to create it manually:
```bash
conda create -n research_assistant python=3.10 -y
conda activate research_assistant
pip install -r requirements.txt
```

#### Option 2: Using pip

1. **Install dependencies:**
```bash
pip install -r requirements.txt
```

2. **Activate the environment (if using conda):**
```bash
conda activate research_assistant
```

3. **Set up Google Custom Search API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Enable the Custom Search API
   - Create credentials (API Key)
   - Create a Custom Search Engine at [Programmable Search Engine](https://programmablesearchengine.google.com/)
   - Note your API Key and Search Engine ID

4. **Configure environment variables:**
   - Create a `.env` file in the project root directory
   - Add your credentials:
   ```env
   GOOGLE_API_KEY=your_google_api_key_here
   GOOGLE_CSE_ID=your_custom_search_engine_id_here
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   ```
   - **Note:** The `.env` file is gitignored for security. Create it manually or use this PowerShell command:
   ```powershell
   @"
   GOOGLE_API_KEY=your_google_api_key_here
   GOOGLE_CSE_ID=your_custom_search_engine_id_here
   OLLAMA_BASE_URL=http://localhost:11434
   OLLAMA_MODEL=llama3.2
   "@ | Out-File -FilePath .env -Encoding utf8
   ```

5. **Ensure Ollama is running:**
```bash
# Start Ollama service
ollama serve

# Pull a model if needed (e.g., llama3.2)
ollama pull llama3.2
```

## Usage

### Interactive Mode

```bash
python main.py
```

Then enter your research query when prompted.

### Command Line Mode

```bash
python main.py --export "Find 3 facts about AI safety"
```

Running the same command without `--export` will still print results to the console.

### Example Queries

- "Find 3 facts about AI safety"
- "What are 5 key developments in quantum computing?"
- "Summarize the latest news about renewable energy"

### Command Line Flags

- `--export`: Save the workflow output to Markdown and JSON files using `ExportService`. The auto-generated filename is based on the query and timestamp, and both formats appear in the `outputs/` directory by default.
- `--check`: Validate Google and Ollama configuration before running the workflow to ensure credentials, URLs, and models meet expectations.

## Logging

- **Location**: `logs/research_assistant.log` (created automatically by `logger.py`). If the `logs/` directory does not exist, it is created at startup.
- **Detail level**: Console output stays at INFO, while the file captures DEBUG traces for Graph nodes, service calls, retries, and export events. Review the log for timestamps, module names, and stack traces when troubleshooting.

## Workflow Details

The LangGraph workflow processes requests through these steps:

1. **Query Refinement**: The LLM refines your natural language request into a search-optimized query
2. **Source Fetching**: Google Search API retrieves relevant web pages (default: 5 results)
3. **Summarization**: The LLM extracts key facts and creates a structured summary
4. **Output Formatting**: Results are formatted with citations and source links

## Project Structure

```
.
├── main.py              # Entry point
├── workflow.py          # LangGraph workflow definition
├── search_service.py    # Google Search API integration
├── llm_service.py       # Ollama LLM integration
├── export_service.py    # Markdown/JSON export helpers
├── config.py            # Configuration management
├── config_validator.py  # Detailed configuration validation
├── retry_handler.py     # Retry/backoff helpers
├── logger.py            # Structured logging setup (writes to logs/)
├── requirements.txt     # Python dependencies
├── environment.yml      # Conda environment specification
├── README.md            # Core documentation
├── CONTRIBUTING.md      # Contribution guide
├── API_DOCS.md          # API reference
├── logs/                # Runtime log files (created automatically)
├── outputs/             # Exported Markdown/JSON (created via --export)
└── .env                 # Runtime overrides (gitignored)
```

## Customization

### Changing the LLM Model

Edit `.env`:
```env
OLLAMA_MODEL=your_preferred_model
```

### Adjusting Search Results

Modify `num_results` in `workflow.py` → `_fetch_sources_node`:
```python
results = self.search_service.search(state['refined_query'], num_results=10)
```

### Modifying Output Format

Edit the `_format_output_node` method in `workflow.py` to customize the output structure.

## Performance Tips

- **Leverage caching**: The workflow caches search queries (`_source_cache`) and summaries (`_summary_cache`) when `use_cache` is true. Pass `use_cache=False` only if you need fresh data for every run.
- **Respect retry behavior**: Services like `GoogleSearchService` and `OllamaLLMService` use `retry_with_backoff`. Wait a few seconds between retries if you hit rate limits, then rerun the same query.
- **Use auto-export for reproducibility**: Running with `--export` freezes the workflow output into files under `outputs/`; share those files instead of rerunning if you want stable references.

## Troubleshooting

### Configuration validation (`--check`)
- Run `python main.py --check` to surface missing Google or Ollama values before launching the workflow.
- Follow the printed hints in `Configuration Validation` (and re-run with `--check`) until all checks show ✓.

### Missing Google credentials
- Ensure your `.env` file contains `GOOGLE_API_KEY` and `GOOGLE_CSE_ID` in the project root.
- Double-check the credentials in the Google Cloud Console match the ones in `.env`.

### Ollama connectivity
- Ensure Ollama is running: `ollama serve`.
- Verify your model is installed: `ollama list` (or `ollama pull llama3.2` if missing).
- Confirm `OLLAMA_BASE_URL` in `.env` matches the server you started.

### Search API errors
- Confirm your API key is enabled for the Custom Search JSON API.
- Verify the Custom Search Engine ID matches the value stored in `.env`.
- Watch quota usage in the Google Cloud Console; quota hits surface as `dailyLimitExceeded` or `quotaExceeded`.

### Export file issues
- If exports fail, inspect `logs/research_assistant.log` for `PermissionError` or `OSError`.
- Ensure the default `outputs/` directory is writable (adjust `ExportService` constructor with a custom directory if needed).

### Logs for deeper diagnostics
- `logs/research_assistant.log` captures traceback-level detail for retries, workflow nodes, exports, and validation errors.
- Reproduce the issue and then open the log file to trace the exact module and message that failed.

## License

MIT
