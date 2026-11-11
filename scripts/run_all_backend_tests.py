"""
Test execution script to run all 30 backend test files in AgriMind,
recording exact pass/fail/error counts, durations, and failure reasons.
"""
import os
import sys
import time
import unittest
from io import StringIO

WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

TEST_DIR = os.path.join(WORKSPACE, "tests")

def run_tests():
    test_files = sorted([f for f in os.listdir(TEST_DIR) if f.startswith("test_") and f.endswith(".py")])
    print(f"Discovered {len(test_files)} test files in {TEST_DIR}\n")

    total_discovered = 0
    total_passed = 0
    total_failed = 0
    total_errors = 0
    total_skipped = 0

    results_table = []
    failure_details = []

    start_all = time.time()

    for idx, fname in enumerate(test_files, 1):
        mod_name = f"tests.{fname[:-3]}"
        loader = unittest.TestLoader()
        try:
            suite = loader.loadTestsFromName(mod_name)
            test_count = suite.countTestCases()
            total_discovered += test_count

            stream = StringIO()
            runner = unittest.TextTestRunner(stream=stream, verbosity=1)
            t0 = time.time()
            res = runner.run(suite)
            dt = time.time() - t0

            passed = test_count - len(res.failures) - len(res.errors) - len(res.skipped)
            failed = len(res.failures)
            errors = len(res.errors)
            skipped = len(res.skipped)

            total_passed += passed
            total_failed += failed
            total_errors += errors
            total_skipped += skipped

            status_str = "PASS" if (failed == 0 and errors == 0) else "FAIL"
            print(f"[{idx:02d}/{len(test_files)}] {fname:<36} | {status_str} | {passed:2d} passed, {failed:2d} failed, {errors:2d} errors | {dt:6.2f}s")

            results_table.append({
                "file": fname,
                "tests": test_count,
                "passed": passed,
                "failed": failed,
                "errors": errors,
                "skipped": skipped,
                "time": dt,
                "status": status_str
            })

            if failed > 0 or errors > 0:
                for test, err in res.failures:
                    failure_details.append(f"FAIL [{fname}] {test.id()}:\n{err}\n")
                for test, err in res.errors:
                    failure_details.append(f"ERROR [{fname}] {test.id()}:\n{err}\n")

        except Exception as e:
            print(f"[{idx:02d}/{len(test_files)}] {fname:<36} | LOAD_ERROR: {e}")
            failure_details.append(f"LOAD_ERROR [{fname}]: {e}\n")

    total_time = time.time() - start_all

    print("\n" + "="*80)
    print("BACKEND TEST SUITE EXECUTION SUMMARY")
    print("="*80)
    print(f"Total Test Files Discovered: {len(test_files)}")
    print(f"Total Test Cases Discovered: {total_discovered}")
    print(f"Total Tests Executed:        {total_passed + total_failed + total_errors + total_skipped}")
    print(f"Total Tests Passed:          {total_passed}")
    print(f"Total Tests Failed:          {total_failed}")
    print(f"Total Tests Errored:         {total_errors}")
    print(f"Total Tests Skipped:         {total_skipped}")
    print(f"Total Suite Duration:        {total_time:.2f}s")
    print("="*80)

    if failure_details:
        print("\nFAILURE & ERROR DETAILS (First 10):")
        for detail in failure_details[:10]:
            print(detail)
            print("-" * 60)

    # Save summary to docs/test_run_raw.txt
    summary_path = os.path.join(WORKSPACE, "docs", "test_run_raw.txt")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"Total Discovered: {total_discovered}\n")
        f.write(f"Passed: {total_passed}\nFailed: {total_failed}\nErrors: {total_errors}\nSkipped: {total_skipped}\nDuration: {total_time:.2f}s\n\n")
        for r in results_table:
            f.write(f"{r['file']:<38} | Tests: {r['tests']:2d} | Passed: {r['passed']:2d} | Failed: {r['failed']:2d} | Errors: {r['errors']:2d} | {r['time']:6.2f}s\n")
        f.write("\n\nFAILURES:\n")
        for d in failure_details:
            f.write(d + "\n")

    print(f"\nDetailed test report written to: {summary_path}")

if __name__ == "__main__":
    run_tests()

