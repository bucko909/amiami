#!/bin/sh

PYTHONIOENCODING=utf-8 python -u /home/amiami/git/spider/spider.py >> /home/amiami/spiderlog/$(date +%s)
