#!/bin/bash
cd "/Users/mini/Documents/New project —股票爱分析"
source venv/bin/activate
echo "🚀 启动中... http://localhost:8000"
sleep 1
open http://localhost:8000
python main.py --serve-only --port 8000
