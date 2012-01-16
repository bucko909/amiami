#!/bin/sh

PYTHONIOENCODING=utf-8 python -u /home/amiami/spider.py >> /home/amiami/spiderlog/$(date +%s)
