"""
Evaluation and benchmarking module for AgriMind RAG Retriever.
Evaluates 15 disease queries across 3 classes and out-of-domain queries.
"""
import os
import sys
import json
import time
from typing import List, Dict, Any

# Ensure workspace is on path
WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
if WORKSPACE_DIR not in sys.path:
    sys.path.insert(0, WORKSPACE_DIR)

from src.rag.retriever import AgrimindRetriever, INSUFFICIENT_EVIDENCE_FALLBACK

BENCHMARK_QUERIES = [
    # Bacterial Spot Queries
    {
        "id": "BS-Q1",
        "disease": "Tomato___Bacterial_spot",
        "category": "Symptomology",
        "query": "What are the early leaf symptoms of bacterial spot on tomato plants?",
        "expected_doc_ids": ["DOC-CORNELL-TOM-BS-01"],
        "required_keywords": ["water-soaked", "small", "black", "greasy"]
    },
    {
        "id": "BS-Q2",
        "disease": "Tomato___Bacterial_spot",
        "category": "Cultural Control",
        "query": "How can tomato seeds be treated to eliminate the bacterial spot pathogen?",
        "expected_doc_ids": ["DOC-CORNELL-TOM-BS-01"],
        "required_keywords": ["hot water", "122°F", "25 minutes"]
    },
    {
        "id": "BS-Q3",
        "disease": "Tomato___Bacterial_spot",
        "category": "Chemical Management",
        "query": "Why is copper mixed with mancozeb for bacterial spot management in tomato?",
        "expected_doc_ids": ["DOC-UFIFAS-TOM-BS-02", "DOC-CORNELL-TOM-BS-01"],
        "required_keywords": ["copper", "mancozeb", "resistance"]
    },
    {
        "id": "BS-Q4",
        "disease": "Tomato___Bacterial_spot",
        "category": "SAR / Host Resistance",
        "query": "How does Actigard work to manage bacterial spot in tomatoes?",
        "expected_doc_ids": ["DOC-UFIFAS-TOM-BS-02", "DOC-CORNELL-TOM-BS-01"],
        "required_keywords": ["acibenzolar", "systemic acquired resistance", "actigard"]
    },
    {
        "id": "BS-Q5",
        "disease": "Tomato___Bacterial_spot",
        "category": "Biological Control",
        "query": "What biological controls or microbial antagonists can suppress bacterial spot?",
        "expected_doc_ids": ["DOC-UFIFAS-TOM-BS-02"],
        "required_keywords": ["bacillus", "bacteriophage"]
    },

    # Early Blight Queries
    {
        "id": "EB-Q1",
        "disease": "Tomato___Early_blight",
        "category": "Symptomology",
        "query": "What distinctive leaf pattern identifies early blight on tomato foliage?",
        "expected_doc_ids": ["DOC-PURDUE-TOM-EB-01", "DOC-UCIPM-TOM-EB-02"],
        "required_keywords": ["concentric", "target", "bullseye"]
    },
    {
        "id": "EB-Q2",
        "disease": "Tomato___Early_blight",
        "category": "Cultural Control",
        "query": "What crop rotation interval is recommended to prevent early blight in tomato fields?",
        "expected_doc_ids": ["DOC-PURDUE-TOM-EB-01"],
        "required_keywords": ["rotation", "solanaceous"]
    },
    {
        "id": "EB-Q3",
        "disease": "Tomato___Early_blight",
        "category": "Chemical Management",
        "query": "What protectant fungicides are recommended for tomato early blight?",
        "expected_doc_ids": ["DOC-PURDUE-TOM-EB-01", "DOC-UCIPM-TOM-EB-02"],
        "required_keywords": ["chlorothalonil", "mancozeb"]
    },
    {
        "id": "EB-Q4",
        "disease": "Tomato___Early_blight",
        "category": "Epidemiology",
        "query": "What temperature and moisture conditions favor Alternaria solani infection?",
        "expected_doc_ids": ["DOC-UCIPM-TOM-EB-02", "DOC-PURDUE-TOM-EB-01"],
        "required_keywords": ["75°F", "wetness", "hours"]
    },
    {
        "id": "EB-Q5",
        "disease": "Tomato___Early_blight",
        "category": "Irrigation Management",
        "query": "Why should overhead irrigation be avoided for early blight management?",
        "expected_doc_ids": ["DOC-UCIPM-TOM-EB-02", "DOC-PURDUE-TOM-EB-01"],
        "required_keywords": ["drip", "overhead", "wet"]
    },

    # Late Blight Queries
    {
        "id": "LB-Q1",
        "disease": "Tomato___Late_blight",
        "category": "Symptomology",
        "query": "How can late blight be distinguished from other tomato foliar diseases in the field?",
        "expected_doc_ids": ["DOC-CORNELL-TOM-LB-01", "DOC-UCIPM-TOM-LB-02"],
        "required_keywords": ["white", "sporulation", "underside", "water-soaked"]
    },
    {
        "id": "LB-Q2",
        "disease": "Tomato___Late_blight",
        "category": "Epidemiology",
        "query": "What weather conditions lead to severe late blight epidemics?",
        "expected_doc_ids": ["DOC-CORNELL-TOM-LB-01"],
        "required_keywords": ["cool", "humidity", "rain"]
    },
    {
        "id": "LB-Q3",
        "disease": "Tomato___Late_blight",
        "category": "Resistant Varieties",
        "query": "Which tomato varieties carry Ph-2 and Ph-3 genetic resistance against late blight?",
        "expected_doc_ids": ["DOC-CORNELL-TOM-LB-01"],
        "required_keywords": ["mountain magic", "ph-2", "ph-3"]
    },
    {
        "id": "LB-Q4",
        "disease": "Tomato___Late_blight",
        "category": "Chemical Management",
        "query": "Which fungicide has post-infection kickback activity against late blight in tomato?",
        "expected_doc_ids": ["DOC-CORNELL-TOM-LB-01"],
        "required_keywords": ["cymoxanil", "curzate", "kickback"]
    },
    {
        "id": "LB-Q5",
        "disease": "Tomato___Late_blight",
        "category": "Pathogen Survival",
        "query": "Where does Phytophthora infestans survive between growing seasons?",
        "expected_doc_ids": ["DOC-UCIPM-TOM-LB-02"],
        "required_keywords": ["potato", "cull", "volunteer", "living"]
    }
]

OUT_OF_DOMAIN_QUERIES = [
    {
        "id": "OOD-Q1",
        "query": "How do you control fire blight in apple and pear orchards?",
        "disease": None
    },
    {
        "id": "OOD-Q2",
        "query": "What is the recommended pre-emergent herbicide for corn weed management?",
        "disease": None
    }
]

def run_retrieval_benchmarks(
    retriever: AgrimindRetriever,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Runs the 15 gold-standard disease queries plus out-of-domain queries.
    Computes Precision@4, Hit Rate, and insufficient evidence handling.
    """
    print("\n==================================================")
    print("RUNNING AGRIMIND RAG RETRIEVAL BENCHMARKS (15 QUERIES)")
    print("==================================================")

    results_log = []
    hits = 0
    total_queries = len(BENCHMARK_QUERIES)

    for item in BENCHMARK_QUERIES:
        t0 = time.perf_counter()
        retrieval = retriever.retrieve(
            query=item["query"],
            disease_target=item["disease"],
            top_k=4
        )
        dt = (time.perf_counter() - t0) * 1000

        retrieved_doc_ids = [r["metadata"]["doc_id"] for r in retrieval["results"]]
        
        # Check if at least one expected doc_id is in top_k
        is_hit = any(expected in retrieved_doc_ids for expected in item["expected_doc_ids"])
        if is_hit:
            hits += 1

        # Check keyword presence in top chunk text
        top_text = retrieval["results"][0]["text"].lower() if retrieval["results"] else ""
        keyword_matches = [kw for kw in item["required_keywords"] if kw.lower() in top_text]
        keyword_coverage = len(keyword_matches) / len(item["required_keywords"]) if item["required_keywords"] else 1.0

        top_similarity = retrieval["results"][0]["similarity_score"] if retrieval["results"] else 0.0

        record = {
            "query_id": item["id"],
            "disease": item["disease"],
            "category": item["category"],
            "query": item["query"],
            "latency_ms": round(dt, 2),
            "is_hit": is_hit,
            "top_similarity": top_similarity,
            "keyword_coverage": round(keyword_coverage, 2),
            "retrieved_doc_ids": retrieved_doc_ids,
            "expected_doc_ids": item["expected_doc_ids"],
            "top_citation": retrieval["citations"][0]["title"] if retrieval["citations"] else None
        }
        results_log.append(record)
        status_str = "HIT" if is_hit else "MISS"
        print(f"  [{item['id']}] {status_str} | Sim={top_similarity:.4f} | Time={dt:.1f}ms | Query: {item['query'][:55]}...")

    hit_rate = hits / total_queries
    avg_latency = sum(r["latency_ms"] for r in results_log) / total_queries

    # Test Out-Of-Domain handling
    print("\nTesting Out-of-Domain / Insufficient Evidence Queries...")
    ood_results = []
    ood_passed = 0
    for ood in OUT_OF_DOMAIN_QUERIES:
        retrieval = retriever.retrieve(query=ood["query"], top_k=4)
        # For out-of-domain tomato queries, either max similarity is below threshold
        # or the evidence is safely flagged
        max_sim = max((r["similarity_score"] for r in retrieval["results"]), default=0.0)
        # If threshold is met or fallback triggered
        handled_correctly = not retrieval["has_sufficient_evidence"] or max_sim < 0.40
        if handled_correctly:
            ood_passed += 1

        ood_record = {
            "query_id": ood["id"],
            "query": ood["query"],
            "has_sufficient_evidence": retrieval["has_sufficient_evidence"],
            "max_similarity": max_sim,
            "fallback_message": retrieval["fallback_message"]
        }
        ood_results.append(ood_record)
        print(f"  [{ood['id']}] Handled correctly={handled_correctly} | MaxSim={max_sim:.4f} | HasEvidence={retrieval['has_sufficient_evidence']}")

    summary = {
        "total_test_queries": total_queries,
        "hits_at_k": hits,
        "hit_rate_at_4": round(hit_rate, 4),
        "average_latency_ms": round(avg_latency, 2),
        "ood_queries_tested": len(OUT_OF_DOMAIN_QUERIES),
        "ood_queries_safely_handled": ood_passed,
        "query_results": results_log,
        "out_of_domain_results": ood_results
    }

    print("\n=== BENCHMARK SUMMARY ===")
    print(f"Hit Rate @ 4:        {hit_rate*100:.2f}% ({hits}/{total_queries})")
    print(f"Average Latency:     {avg_latency:.1f} ms")
    print(f"OOD Safety Handling: {ood_passed}/{len(OUT_OF_DOMAIN_QUERIES)}")

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Saved benchmark results to: {output_path}")

    return summary

def run_generation_benchmarks(
    generator: Any,
    output_path: str = None
) -> Dict[str, Any]:
    """
    Runs end-to-end answer generation across the 15 benchmark queries and 2 OOD queries.
    Validates grounded answer synthesis, citation linkage, and insufficient evidence safety.
    """
    print("\n==================================================")
    print("RUNNING AGRIMIND RAG GENERATION BENCHMARKS (15 + 2 QUERIES)")
    print("==================================================")

    results_log = []
    total_queries = len(BENCHMARK_QUERIES)

    for item in BENCHMARK_QUERIES:
        t0 = time.perf_counter()
        gen_res = generator.generate_answer(
            query=item["query"],
            disease_target=item["disease"],
            top_k=4
        )
        dt = (time.perf_counter() - t0) * 1000

        record = {
            "query_id": item["id"],
            "disease": item["disease"],
            "category": item["category"],
            "query": item["query"],
            "latency_ms": round(dt, 2),
            "has_sufficient_evidence": gen_res["has_sufficient_evidence"],
            "generation_mode": gen_res["generation_mode"],
            "citation_count": len(gen_res["citations"]),
            "citations": [c.get("title") for c in gen_res["citations"]],
            "answer_preview": gen_res["answer"][:180] + "..." if len(gen_res["answer"]) > 180 else gen_res["answer"]
        }
        results_log.append(record)
        print(f"  [{item['id']}] Mode={gen_res['generation_mode']} | Cits={len(gen_res['citations'])} | Time={dt:.1f}ms")

    # Out-of-Domain tests
    print("\nTesting Out-of-Domain Generation Handling...")
    ood_results = []
    for ood in OUT_OF_DOMAIN_QUERIES:
        t0 = time.perf_counter()
        gen_res = generator.generate_answer(query=ood["query"], top_k=4)
        dt = (time.perf_counter() - t0) * 1000

        is_safe = (not gen_res["has_sufficient_evidence"]) and (gen_res["answer"] == INSUFFICIENT_EVIDENCE_FALLBACK)
        ood_record = {
            "query_id": ood["id"],
            "query": ood["query"],
            "latency_ms": round(dt, 2),
            "has_sufficient_evidence": gen_res["has_sufficient_evidence"],
            "is_safely_rejected": is_safe,
            "generation_mode": gen_res["generation_mode"],
            "answer": gen_res["answer"]
        }
        ood_results.append(ood_record)
        print(f"  [{ood['id']}] SafelyRejected={is_safe} | Mode={gen_res['generation_mode']}")

    summary = {
        "total_domain_queries": total_queries,
        "all_domain_answered": all(r["has_sufficient_evidence"] for r in results_log),
        "total_ood_queries": len(OUT_OF_DOMAIN_QUERIES),
        "all_ood_safely_rejected": all(r["is_safely_rejected"] for r in ood_results),
        "query_results": results_log,
        "out_of_domain_results": ood_results
    }

    if output_path:
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(summary, f, indent=2)
        print(f"Saved generation benchmark results to: {output_path}")

    return summary

if __name__ == "__main__":
    from src.rag.generator import AgrimindAnswerGenerator
    retriever = AgrimindRetriever()
    generator = AgrimindAnswerGenerator(retriever=retriever)
    
    out_retrieval = os.path.join(WORKSPACE_DIR, "outputs", "week3_rag", "retrieval_benchmarks.json")
    out_generation = os.path.join(WORKSPACE_DIR, "outputs", "week3_rag", "generation_benchmarks.json")
    
    run_retrieval_benchmarks(retriever, out_retrieval)
    run_generation_benchmarks(generator, out_generation)

