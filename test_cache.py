"""Test caching functionality for Issue 5."""
from workflow import ResearchWorkflow

print("=" * 60)
print("TESTING CACHE FUNCTIONALITY (Issue 5)")
print("=" * 60)

w = ResearchWorkflow()

print("\n1. First run - should MISS both caches:")
result1 = w.run("Find 3 facts about Python programming")

print("\n" + "=" * 60)
print("\n2. Second identical run - should HIT both caches:")
result2 = w.run("Find 3 facts about Python programming")

print("\n" + "=" * 60)
print("\n3. Third run with cache disabled - should BYPASS cache:")
result3 = w.run("Find 3 facts about Python programming", use_cache=False)

print("\n" + "=" * 60)
print("\nCheck research_assistant.log for cache hit/miss messages")
print("=" * 60)
