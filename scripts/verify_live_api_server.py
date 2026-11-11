"""
AgriMind Stage A Closure Audit — Live Server Verification Script.
Starts Uvicorn on 0.0.0.0:8000 in background, executes live HTTP GET /health
and POST /diagnose with a real PlantVillage tomato leaf image, validates latency
measurements, and shuts down cleanly.
"""
import os
import sys
import time
import json
import subprocess
import requests

WORKSPACE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_BIN = "/home/jaskirat/agrimind-rag-env/bin/python"
UVICORN_CMD = [
    PYTHON_BIN,
    "-m", "uvicorn",
    "src.api.app:app",
    "--host", "0.0.0.0",
    "--port", "8000"
]
SAMPLE_REAL_IMAGE = "/mnt/c/Users/asus/PlantVillage-Dataset/raw/color/Tomato___Bacterial_spot/00416648-be6e-4bd4-bc8d-82f43f8a7240___GCREC_Bact.Sp 3110.JPG"


def main():
    print(f"=== AgriMind Live Server Verification ===")
    print(f"Workspace: {WORKSPACE_DIR}")
    print(f"Python:    {PYTHON_BIN}")
    print(f"Uvicorn:   {' '.join(UVICORN_CMD)}")
    print(f"Test Image:{SAMPLE_REAL_IMAGE}")

    if not os.path.exists(SAMPLE_REAL_IMAGE):
        print(f"ERROR: Test image missing at {SAMPLE_REAL_IMAGE}")
        sys.exit(1)

    print("\n[Step 1] Launching Uvicorn server process...")
    server_proc = subprocess.Popen(
        UVICORN_CMD,
        cwd=WORKSPACE_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    try:
        # Wait for server readiness
        base_url = "http://127.0.0.1:8000"
        health_url = f"{base_url}/health"
        is_ready = False
        print("Polling GET /health for server readiness...")
        for i in range(25):
            time.sleep(1)
            try:
                r = requests.get(health_url, timeout=2)
                if r.status_code == 200:
                    is_ready = True
                    print(f"Server became ready after {i+1} seconds!")
                    break
            except requests.RequestException:
                pass

        if not is_ready:
            print("ERROR: Server failed to start within timeout.")
            stdout, stderr = server_proc.communicate(timeout=5)
            print("Server stdout:\n", stdout)
            print("Server stderr:\n", stderr)
            sys.exit(1)

        # -------------------------------------------------------------
        # 1. Test GET /health
        # -------------------------------------------------------------
        print("\n[Step 2] Executing live HTTP GET /health...")
        health_resp = requests.get(health_url, timeout=5)
        print(f"HTTP Status: {health_resp.status_code}")
        health_data = health_resp.json()
        print(f"Response Payload:\n{json.dumps(health_data, indent=2)}")

        assert health_resp.status_code == 200, f"Expected 200, got {health_resp.status_code}"
        assert health_data["status"] == "healthy", f"Status not healthy: {health_data['status']}"
        assert health_data["models_available"]["resnet50"] is True
        assert health_data["models_available"]["rag_chromadb"] is True
        assert health_data["rag_chunks"] == 50

        # -------------------------------------------------------------
        # 2. Test POST /diagnose with real image
        # -------------------------------------------------------------
        print("\n[Step 3] Executing live HTTP POST /diagnose with real image file...")
        diagnose_url = f"{base_url}/diagnose"
        start_client_time = time.perf_counter()

        with open(SAMPLE_REAL_IMAGE, "rb") as f:
            files = {"file": ("bacterial_spot_sample.jpg", f, "image/jpeg")}
            data = {
                "leaf_damage_percentage": "12.0",
                "affected_organs": "leaves",
                "canopy_spread": "lower_canopy",
                "weather_conditions": "warm_humid",
                "field_notes": "Live HTTP verification test using genuine PlantVillage leaf."
            }
            diag_resp = requests.post(diagnose_url, files=files, data=data, timeout=90)

        total_client_latency_ms = round((time.perf_counter() - start_client_time) * 1000, 2)
        print(f"HTTP Status: {diag_resp.status_code}")
        assert diag_resp.status_code == 200, f"Expected 200, got {diag_resp.status_code}: {diag_resp.text}"

        diag_data = diag_resp.json()
        print(f"\n[Diagnostic Response Summary]")
        print(f"  Case ID:                {diag_data.get('case_id')}")
        print(f"  Workflow Status:        {diag_data.get('workflow_status')}")
        print(f"  Primary Diagnosis:      {diag_data.get('primary_diagnosis')}")
        print(f"  Diagnosis Confidence:   {diag_data.get('diagnosis_confidence')}")
        print(f"  Class Probabilities:    {diag_data.get('class_probabilities')}")
        print(f"  Assigned Severity:      {diag_data.get('assigned_severity')}")
        print(f"  Epidemic Risk:          {diag_data.get('epidemic_risk')}")
        print(f"  Plan Urgency:           {diag_data.get('plan_urgency')}")
        print(f"  Critic Verified:        {diag_data.get('is_verified')}")
        print(f"  Verification Status:    {diag_data.get('verification_status')}")
        print(f"  Citations Count:        {len(diag_data.get('citations') or [])}")

        latency = diag_data.get("latency_breakdown", {})
        model_inf_ms = latency.get("model_inference_ms")
        workflow_ms = latency.get("total_workflow_ms")

        print(f"\n[Latency Breakdown - High Resolution Timers]")
        print(f"  Model Inference Latency (server): {model_inf_ms:.2f} ms")
        print(f"  Total Workflow Latency  (server): {workflow_ms:.2f} ms")
        print(f"  Total Round-Trip Latency(client): {total_client_latency_ms:.2f} ms")

        assert model_inf_ms is not None and model_inf_ms > 0, "Model inference latency must be > 0"
        assert workflow_ms is not None and workflow_ms > model_inf_ms, "Workflow latency must exceed inference latency"
        assert total_client_latency_ms >= workflow_ms, "Client latency must exceed server latency"

        print("\n=== Live Server Verification Succeeded! ===")

    finally:
        print("\n[Step 4] Shutting down live Uvicorn server...")
        server_proc.terminate()
        try:
            server_proc.wait(timeout=5)
            print("Server process terminated cleanly.")
        except subprocess.TimeoutExpired:
            server_proc.kill()
            print("Server process forcefully killed.")


if __name__ == "__main__":
    main()

