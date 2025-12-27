"""Main entry point for the research assistant."""
import sys
from workflow import ResearchWorkflow
from config import OLLAMA_MODEL


def main():
    """Run the research assistant."""
    if len(sys.argv) > 1:
        # Command line mode
        query_input = " ".join(sys.argv[1:])
    else:
        # Interactive mode
        print("🤖 Research Assistant with LangGraph Workflow")
        print("=" * 50)
        query_input = input("\nEnter your research query: ")

    query = query_input.strip()
    if not query:
        print("❌ Unable to continue: research query cannot be empty or whitespace only.")
        return
    if len(query) < 3:
        print("❌ Unable to continue: research query must be at least 3 characters long.")
        return
    if len(query) > 500:
        print("❌ Unable to continue: research query must be 500 characters or less.")
        return

    try:
        print(f"\n🚀 Processing: {query}\n")
        workflow = ResearchWorkflow()
        result = workflow.run(query)
        
        print("\n" + "=" * 50)
        print("📊 RESEARCH RESULTS")
        print("=" * 50 + "\n")
        print(result)
        print("\n" + "=" * 50)
        
    except ConnectionError as e:
        # Clean error message for Ollama connection issues
        print(f"❌ Connection Error: {e}")
        print("\n💡 Make sure Ollama is running:")
        print("   1. Run: ollama serve")
        print("   2. Verify your model is installed: ollama list")
        print(f"   3. If needed, pull the model: ollama pull {OLLAMA_MODEL}")
    except ValueError as e:
        print(f"❌ Validation Error: {e}")
        if "GOOGLE" in str(e).upper():
            print("\n💡 This appears to be a configuration issue. Check your .env file includes:")
            print("- GOOGLE_API_KEY")
            print("- GOOGLE_CSE_ID")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
