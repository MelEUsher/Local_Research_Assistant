# Research Assistant with LangGraph Workflow

A customized research assistance system that uses LangGraph to orchestrate a multi-step workflow for fetching and summarizing information from the web.

## Features

- 📝 Takes natural-language research requests
- 🔍 Fetches information from the web using Google Search API
- 🤖 Uses Ollama (local LLM) for query refinement and summarization
- 🔄 LangGraph workflow orchestrates: refine query → fetch sources → summarize → output
- 📊 Returns structured, formatted output with citations

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
python main.py "Find 3 facts about AI safety"
```

### Example Queries

- "Find 3 facts about AI safety"
- "What are 5 key developments in quantum computing?"
- "Summarize the latest news about renewable energy"

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
├── config.py            # Configuration management
├── requirements.txt     # Python dependencies
├── environment.yml      # Conda environment specification
└── README.md           # This file
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

## Troubleshooting

### "Error: GOOGLE_API_KEY and GOOGLE_CSE_ID must be set"
- Ensure your `.env` file exists and contains valid credentials
- Verify the file is in the project root directory

### "Connection refused" or Ollama errors
- Ensure Ollama is running: `ollama serve`
- Verify the model exists: `ollama list`
- Pull the model if needed: `ollama pull llama3.2`
- Check `OLLAMA_BASE_URL` in `.env` matches your Ollama instance


### Search API errors
- Verify your API key is valid and has the Custom Search API enabled
- Check that your Custom Search Engine ID is correct
- Ensure you haven't exceeded API quotas

## License

MIT
