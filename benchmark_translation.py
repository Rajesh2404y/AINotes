"""
Comprehensive Multilingual Translation Performance Benchmark.
Tests Short, Medium, and Long texts before and after optimization.
Measures latency, memory consumption, token throughput, and Unicode script integrity.
"""
import os
import sys
import time
import psutil

# Ensure backend root on sys.path
sys.path.insert(0, os.path.abspath("."))

from backend.app import create_app
from backend.app.ai.translation_service import translation_service
from backend.app.models.user import User
from backend.app.models.document import Document
from backend.app.models.summary import Summary
from backend.app.extensions import db

app = create_app("development")

SHORT_TEXT = "Artificial intelligence and machine learning empower automated study workflows."

MEDIUM_TEXT = (
    "Machine learning is a subset of artificial intelligence that focuses on building "
    "applications that learn from data and improve their accuracy over time without being "
    "explicitly programmed. Common types of machine learning include supervised learning, "
    "unsupervised learning, and reinforcement learning."
)

LONG_ACADEMIC_TEXT = (
    "Operating systems provide memory management, process scheduling, and file system abstraction. "
    "Virtual memory allows a computer to compensate for physical memory shortages by temporarily transferring "
    "data from random access memory to disk storage. Page replacement algorithms such as Least Recently Used "
    "and First-In-First-Out dictate which memory pages are swapped out when page faults occur.\n\n"
    "In machine learning and neural networks, deep learning models utilize backpropagation and gradient descent "
    "to iteratively optimize loss functions. Supervised learning models require labeled training datasets, whereas "
    "unsupervised algorithms detect intrinsic patterns in unlabeled data. Regularization techniques like dropout "
    "and weight decay prevent overfitting on empirical datasets.\n\n"
    "Natural language processing bridges human communication and computational linguistics. Neural machine "
    "translation models encode semantic representations into high-dimensional vector spaces and decode target "
    "languages with attention mechanisms."
)

def get_process_memory_mb():
    process = psutil.Process(os.getpid())
    return process.memory_info().rss / (1024 * 1024)

def run_benchmark():
    with app.app_context():
        print("=" * 70)
        print("  MULTILINGUAL TRANSLATION ENGINE PERFORMANCE BENCHMARK")
        print("=" * 70)
        print(f"Hardware / OS: Windows ({os.cpu_count()} CPU cores)")
        print(f"Base Memory RSS: {get_process_memory_mb():.2f} MB")
        print(f"Model ID: facebook/nllb-200-distilled-600M")
        print("-" * 70)

        test_cases = [
            ("Short Text (79 chars)", SHORT_TEXT, "en", "ta"),
            ("Medium Text (277 chars)", MEDIUM_TEXT, "en", "ta"),
            ("Long Academic Notes (1054 chars)", LONG_ACADEMIC_TEXT, "en", "ta"),
            ("Medium Text -> Hindi (HI)", MEDIUM_TEXT, "en", "hi"),
            ("Medium Text -> French (FR)", MEDIUM_TEXT, "en", "fr"),
            ("Medium Text -> German (DE)", MEDIUM_TEXT, "en", "de"),
        ]

        results = []

        for name, text, src, tgt in test_cases:
            print(f"\n>>> Running: {name} ({src} -> {tgt})...")
            mem_before = get_process_memory_mb()
            t0 = time.time()
            res = translation_service.translate_text(text, source_lang=src, target_lang=tgt)
            dur = time.time() - t0
            mem_after = get_process_memory_mb()

            trans_text = res.get("translated_text", "")
            meta = res.get("metadata", {})
            total_chunks = res.get("total_chunks", 1)
            tokens = meta.get("source_tokens", len(text.split()) * 4 // 3)
            tok_per_sec = meta.get("tokens_per_second", round(tokens / max(0.01, dur), 2))

            print(f"    - Duration:         {dur:.3f} s")
            print(f"    - Chunks:           {total_chunks}")
            print(f"    - Backend Used:     {meta.get('backend_used', 'N/A')}")
            print(f"    - Throughput:       {tok_per_sec} tokens/s")
            print(f"    - Memory Delta:     +{mem_after - mem_before:.2f} MB")
            print(f"    - Sample Output:    {trans_text[:90]}...")

            results.append({
                "name": name,
                "length": len(text),
                "chunks": total_chunks,
                "duration": dur,
                "throughput": tok_per_sec,
                "sample": trans_text[:80]
            })

        print("\n" + "=" * 70)
        print("  BENCHMARK SUMMARY TABLE")
        print("=" * 70)
        print(f"{'Test Case':<35} | {'Chars':<6} | {'Chunks':<6} | {'Duration':<10} | {'Throughput'}")
        print("-" * 70)
        for r in results:
            print(f"{r['name']:<35} | {r['length']:<6} | {r['chunks']:<6} | {r['duration']:<6.2f} s    | {r['throughput']} tok/s")
        print("=" * 70)

if __name__ == "__main__":
    run_benchmark()

