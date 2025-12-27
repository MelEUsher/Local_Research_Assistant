"""Main entry point for the research assistant."""
import argparse
import sys

from workflow import ResearchWorkflow
from config import OLLAMA_MODEL, validate_config
from logger import logger


def _print_validation_summary(validation_result):
    """Display validation checks with passing/failing icons."""
    details = validation_result.get("details", {})
    checks = (
        ("Google configuration", details.get("google", [])),
        ("Ollama configuration", details.get("ollama", [])),
    )

    print("\nConfiguration Validation")
    print("=" * 26)
    for label, issues in checks:
        icon = "✓" if not issues else "✗"
        print(f"{icon} {label}")
        for issue in issues:
            print(f"   - {issue}")

    return validation_result.get("valid", True)


def _run_with_args(args):
    validation_result = validate_config()

    if args.check:
        print("\nConfiguration validation results:")
        valid = _print_validation_summary(validation_result)
        logger.info("Configuration check requested; valid=%s", valid)
        sys.exit(0 if valid else 1)

    if not validation_result["valid"]:
        print("\nConfiguration validation failed:")
        _print_validation_summary(validation_result)
        print("\n❌ Fix the configuration issues above before starting the assistant.")
        logger.error("Configuration validation failed: %s", validation_result["issues"])
        sys.exit(1)

    if args.query:
        query_input = " ".join(args.query)
    else:
        print("🤖 Research Assistant with LangGraph Workflow")
        print("=" * 50)
        query_input = input("\nEnter your research query: ")

    query = query_input.strip()
    if not query:
        logger.warning("Received empty research query")
        print("❌ Unable to continue: research query cannot be empty or whitespace only.")
        return
    if len(query) < 3:
        logger.warning("Research query too short: %s", query)
        print("❌ Unable to continue: research query must be at least 3 characters long.")
        return
    if len(query) > 500:
        logger.warning("Research query too long: %s", query)
        print("❌ Unable to continue: research query must be 500 characters or less.")
        return

    try:
        logger.info("Processing research query: %s", query)
        print(f"\n🚀 Processing: {query}\n")
        workflow = ResearchWorkflow()
        result = workflow.run(query)

        print("\n" + "=" * 50)
        print("📊 RESEARCH RESULTS")
        print("=" * 50 + "\n")
        print(result)
        print("\n" + "=" * 50)
        logger.info("Research workflow completed for query: %s", query)

    except ConnectionError as e:
        logger.error("Connection error during processing query: %s", query, exc_info=True)
        print(f"❌ Connection Error: {e}")
        print("\n💡 Make sure Ollama is running:")
        print("   1. Run: ollama serve")
        print("   2. Verify your model is installed: ollama list")
        print(f"   3. If needed, pull the model: ollama pull {OLLAMA_MODEL}")
    except ValueError as e:
        logger.error("Validation error during processing query: %s", query, exc_info=True)
        print(f"❌ Validation Error: {e}")
        if "GOOGLE" in str(e).upper():
            print("\n💡 This appears to be a configuration issue. Check your .env file includes:")
            print("- GOOGLE_API_KEY")
            print("- GOOGLE_CSE_ID")
    except Exception as e:
        logger.error("Unexpected error during processing query: %s", query, exc_info=True)
        print(f"❌ Error: {e}")
        import traceback

        traceback.print_exc()


def main():
    parser = argparse.ArgumentParser(description="Run the local research assistant.")
    parser.add_argument("-c", "--check", action="store_true", help="Validate configuration and exit.")
    parser.add_argument("query", nargs="*", help="Research query text (omit to use the interactive prompt).")
    args = parser.parse_args()

    logger.info("Application starting")
    try:
        _run_with_args(args)
    finally:
        logger.info("Application completed")


if __name__ == "__main__":
    main()
