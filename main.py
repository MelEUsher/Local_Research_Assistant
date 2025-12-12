"""Main entry point for the research assistant."""
import sys
from workflow import ResearchWorkflow


def main():
    """Run the research assistant."""
    if len(sys.argv) > 1:
        # Command line mode
        query = " ".join(sys.argv[1:])
    else:
        # Interactive mode
        print("🤖 Research Assistant with LangGraph Workflow")
        print("=" * 50)
        query = input("\nEnter your research query: ").strip()
    
    if not query:
        print("❌ Error: Please provide a research query")
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
        
    except ValueError as e:
        print(f"❌ Configuration Error: {e}")
        print("\nPlease ensure you have set up your .env file with:")
        print("- GOOGLE_API_KEY")
        print("- GOOGLE_CSE_ID")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

