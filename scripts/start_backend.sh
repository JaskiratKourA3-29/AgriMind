#!/bin/bash
source /home/jaskirat/agrimind-rag-env/bin/activate
cd /mnt/c/Users/asus/Downloads/Agri_Mind_Minor_Project
exec python -m uvicorn src.api.app:app --host 0.0.0.0 --port 8000

