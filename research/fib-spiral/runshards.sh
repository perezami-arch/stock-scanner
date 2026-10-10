cd /workspace/fib-spiral
for k in 0 1 2 3 4 5; do SHARD=$k NSHARD=6 nohup venv/bin/python fetch_crypto.py > fetch_crypto_$k.log 2>&1 & done
