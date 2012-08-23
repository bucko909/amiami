#!/usr/bin/python

import urllib2
import os
import os.path
import re
import httplib
import datetime
import time
import psycopg2
import sys

dsn = psycopg2.connect('dbname=amiami')
qs = os.environ.get('QUERY_STRING', '')
param = dict()
for q in qs.split(';'):
	if '=' in q:
		q, v = q.split('=')
	else:
		v = True
	param[q] = v
curs = dsn.cursor()


if 'instock' in param:
	instock_str = """ and p.stock!='Sold out'"""
else:
	instock_str = ''

if 'newonly' in param:
	instock_str += """ and pu.diff = 'exists:True,'"""

if 'rss' in param:
	rss = True
else:
	rss = False

if 'update' in param:
	curs.execute('select product_id from product_updates where id=%s', [param['update']])
	(param['id'],), = curs.fetchall()

if 'id' in param:
	curs.execute("select pu.id, name, p.url, image, price, stock, pu.cr_date, pu.diff from products p join product_updates pu on pu.product_id = p.id where pu.product_id = %s order by pu.cr_date desc limit 50", [param['id']])
	catname = 'Item %s' % [param['id']]
elif 'cat' in param and re.match('^[0-9]+$', param['cat']):
	curs.execute("select name from categories where id=%s", [param['cat']])
	(catname,), = curs.fetchall()
	curs.execute("select pu.id, name, p.url, image, price, stock, pu.cr_date, pu.diff from products p join product_updates pu on pu.product_id = p.id join product_categories pc on pc.product_id = p.id where pc.category_id = %s and pu.cr_date > '2011-10-24'" + instock_str + " order by pu.cr_date desc limit 50", [param['cat']])
elif param.get('cat') == 'all':
	catname = 'All'
	curs.execute("select pu.id, name, p.url, image, price, stock, pu.cr_date, pu.diff from products p join product_updates pu on pu.product_id = p.id where pu.cr_date > '2011-10-24'" + instock_str + " order by pu.cr_date desc limit 50")
elif param.get('cat') == 'none':
	catname = 'No category'
	curs.execute("select pu.id, name, p.url, image, price, stock, pu.cr_date, pu.diff from products p join product_updates pu on pu.product_id = p.id left join product_categories pc on pc.product_id = p.id where pc.category_id is null and pu.cr_date > '2011-10-24'" + instock_str + " order by pu.cr_date desc limit 50", [param['cat']])
else:
	print "Content-type: text/html; charset=utf-8"
	print
	print "<html><body><h1>AmiAmi updates</h1><table>"
	print "<h2>Categories</h2><ul>"
	curs.execute("select name, '' as descr, id from categories order by name")
	for name, descr, id in list(curs.fetchall()) + [('Everything', '', 'all'), ('Items with no category', '(often includes very new items)', 'none')]:
		print """<li><a href="?cat=%s">%s</a> %s (<a href="?cat=%s;instock">Stock only</a>) (<a href="?cat=%s;newonly">New additions</a>)</li>""" % (id, name, descr, id, id)
	print """</ul></body></html>"""
	sys.exit()
	
if rss:
	print "Content-type: application/rss+xml; charset=utf-8"
	print
	print """<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
        <title>AmiAmi Updates (%s)</title>
        <description>AmiAmi Updates</description>
        <link>http://amiami.incumbent.co.uk/</link>
        <pubDate>%s</pubDate>
        <ttl>1800</ttl>
""" % (catname, datetime.datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0000"),)
else:
	rssurl = "?" + qs + ';rss'
	print "Content-type: text/html; charset=utf-8"
	print
	print """<html><body><h1>AmiAmi Updates (%s) [<a href="%s">RSS</a>]</h1><table>""" % (catname, rssurl)


for id, name, url, image, price, stock, update_date, recent_diff in curs.fetchall():
	url = url.replace('&', '&amp;')
	if rss:
		if recent_diff == 'added':
			diff = 'New'
		else:
			diff = '&lt;ul&gt;'
			for cname, cnew, cold in re.findall(r'([a-z0-9_-]*?):((?:[^;,\\]|\\.)*),((?:[^;,\\]|\\.)*)', recent_diff or ''):
				diff += '&lt;li&gt;%s: %s -&amp;gt; %s&lt;/li&gt;' % (cname, cold, cnew)
			diff += '&lt;/ul&gt;'
		if image:
			img = '&lt;img src="%s"&gt; ' % (image)
		else:
			img = ''
		print """
        <item>
                <title>%s</title>
                <description>&lt;a href="%s"&gt;%s%s&lt;/a&gt;</description>
                <link>%s/</link>
                <guid>http://amiami.incumbent.co.uk/?update=%s</guid>
                <pubDate>%s</pubDate>
        </item>
""" % (name, url, img, diff, url, id, update_date.strftime("%a, %d %b %Y %H:%M:%S +0000"))
	else:
		if recent_diff == 'added':
			diff = 'New'
		else:
			diff = '<ul>'
			for cname, cnew, cold in re.findall(r'([a-z0-9_-]*?):((?:[^;,\\]|\\.)*),((?:[^;,\\]|\\.)*)', recent_diff or ''):
				diff += '<li>%s: %s -&gt; %s</li>' % (cname, cold, cnew)
			diff += '</ul>'
		format_date = update_date.strftime("%Y-%m-%d (%H:00 ish)")
		if stock == 'Sold out':
			print '''<tr style="background: grey;">'''
		else:
			print '''<tr>'''
		if image:
			print '''<td>%s</td><td><img src="%s"></td><td><a href="%s">%s</a></td><td>%i JPY</td><td>%s</td><td>%s</td></a></li>''' % (format_date, image, url, name, price, stock, diff)
		else:
			print '''<td>%s</td><td></td><td><a href="%s">%s</a></td><td>%i JPY</td><td>%s</td><td>%s</td></a></li>''' % (format_date, url, name, price, stock, diff)
if rss:
	print "</channel></rss>"
else:
	print "</table></body></html>"
	
