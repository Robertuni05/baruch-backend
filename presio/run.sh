echo "running scrapy shell"
cat /dev/null > server.log
scrapy crawl hume  --loglevel INFO --logfile server.log

