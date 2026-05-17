echo "running presio scraper"
cat /dev/null > server.log

python main.py \
  --supermarket wong \
  --output out.json \
  --loglevel INFO \
  "$@" 2>&1 | tee server.log
