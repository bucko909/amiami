#!/bin/sh

PYTHONIOENCODING=utf-8 python -u /home/amiami/git/spider/spider.py 2>&1 > /home/amiami/spiderlog/$(date +%s)
