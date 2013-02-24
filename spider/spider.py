#!/usr/bin/python

import urllib2
import datetime
import os.path
import math
import re
from lxml import html
import pdb
import hashlib
import httplib
import time
import psycopg2

dsn = psycopg2.connect('dbname=amiami')
curs = dsn.cursor()

CACHE = "/home/amiami/cache/"


COOKIEFILE = 'cookies.lwp'

update_raise = False

DEBUG = 0
# the path and filename to save your cookies in

cj = None
ClientCookie = None
cookielib = None

# Let's see if cookielib is available
try:
	import cookielib
except ImportError:
	# If importing cookielib fails
	# let's try ClientCookie
	try:
		import ClientCookie
	except ImportError:
		# ClientCookie isn't available either
		urlopen = urllib2.urlopen
		Request = urllib2.Request
	else:
		# imported ClientCookie
		urlopen = ClientCookie.urlopen
		Request = ClientCookie.Request
		cj = ClientCookie.LWPCookieJar()

else:
	# importing cookielib worked
	urlopen = urllib2.urlopen
	Request = urllib2.Request
	cj = cookielib.LWPCookieJar()
	# This is a subclass of FileCookieJar
	# that has useful load and save methods

if cj is not None:
# we successfully imported
# one of the two cookie handling modules

	if os.path.isfile(COOKIEFILE):
		# if we have a cookie file already saved
		# then load the cookies into the Cookie Jar
		cj.load(COOKIEFILE)

	# Now we need to get our Cookie Jar
	# installed in the opener;
	# for fetching URLs
	if cookielib is not None:
		# if we use cookielib
		# then we get the HTTPCookieProcessor
		# and install the opener in urllib2
		opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cj), urllib2.HTTPHandler(debuglevel=DEBUG))
		urllib2.install_opener(opener)

	else:
		# if we use ClientCookie
		# then we get the HTTPCookieProcessor
		# and install the opener in ClientCookie
		opener = ClientCookie.build_opener(ClientCookie.HTTPCookieProcessor(cj), urllib2.HTTPHandler(debuglevel=DEBUG))
		ClientCookie.install_opener(opener)

def prepare_req(url):
	return urllib2.Request(url, headers={"User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:5.0) Gecko/20100101 Firefox/5.0 Iceweasel/5.0", 'Accept-Language': 'en-us,en;q=0.5'})

def cache_name(url):
	return hashlib.sha256(url).hexdigest()
	#.replace("_", "__").replace("/", "_s")
class login:
	done = False
def get_page(url, cached = True):
	cj.save(COOKIEFILE, ignore_discard=True, ignore_expires=True)

	c = cache_name(url)
	print "GET ", url, "->", c
	if cached and os.path.exists(CACHE + c):
		print "Use cache", CACHE + c
		return open(CACHE + cache_name(url), 'r')
	else:
		print "Fetch page"
		#if not login.done:
		#	print "Logging in"
		#	urllib2.urlopen(prepare_req("http://www.amiami.jp/shop/?set=english"))
		#	login.done = True
		x = urllib2.urlopen(prepare_req(url))
		if cached or True:
			f = open(CACHE + cache_name(url), 'w')
			f.write(x.read())
			f.close()
			return open(CACHE + cache_name(url), 'r')
		else:
			return x

def find_categories():
	return True # TODO fix
	content = get_page("http://www.amiami.com/shop/?set=english")
	uni_content = unicode(content.read(), 'utf-8', 'replace')
	xml = html.fromstring(uni_content)
	for item in xml.xpath('//map/area'):
		if item.getparent().get('name')[:9] != 'sidemenu-':
			continue
		url, = item.xpath('@href')
		m = re.search('vgvar_1_name=categorynickname&vgvar_1_value=(.*)&vgvar_1_operator=LIKE', url)
		if m:
			code, = m.groups()
		elif 'SimpleForm' in url:
			cat_content = get_page(url)
			cat_uni_content = unicode(cat_content.read(), 'utf-8', 'replace')
			cat_xml = html.fromstring(cat_uni_content)
			span = cat_xml.xpath('//a/span[text()="All Items"]') or cat_xml.xpath('//a/span[text()="All items"]')
			span, = span
			url = span.getparent().get('href')
			code, = re.search('vgvar_1_name=CategoryNickname&vgvar_1_value=(.*)&vgvar_1_operator=LIKE', url).groups()
		else:
			print "Skipping category"
			continue
		descr, = item.xpath('@alt')

		if not url:
			print "No url...", str(item)
			continue

		curs.execute('select id, code, name from categories where code=%s', [str(code)])
		rows = curs.fetchall()
		if len(rows) == 0:
			curs.execute("""insert into categories (code, name) values (%s, %s)""", [str(code), str(descr)])
		elif descr and rows[0][2] != descr:
			curs.execute("""update categories set name=%s where id=%s""", [str(descr), id])

def full_flush_all_categories(cached=False):
	curs.execute("truncate table product_categories")
	curs.execute("select code, var from categories")
	for cat, varname in list(curs.fetchall()):
		find_updates(full=True, cat=cat, no_seq=True, cat_var=varname, cached=cached, perpage=2000)

def find_updates(cat=None, cat_var='CategoryNickname', cached=False, full=False, perpage=1000):
	print "Finding updates on category", cat
	print "Cache:", cached
	print "Full:", full
	print "Per page:", perpage

	n = perpage

	if cat is not None:
		catpart = '%s=%s&' % (cat_var, cat)
	else:
		catpart = 's_condition_flg=0&'

	url = 'http://slist.amiami.com/top/search/list2?%spagemax=%i' % (catpart, n)
	content = get_page(url, cached=cached).read()
	if 'No item has found.' in content:
		print "Empty result set"
		raise Exception("No results")

	pages = sorted(list(set(int(x) for x in re.findall("&getcnt=0&pagecnt=([0-9]+)", content))))
	if pages:
		pages = range(1,max(pages)+1)
	else:
		pages = [1]

	if full:
		maxpage = len(pages)
	else:
		k = int(math.log(len(pages),2))+1
		modn = int(time.time() / 3600 + 1) % 2**k
		maxpage = 2**max([ x for x in range(k+1) if modn % 2**x == 0 ])

	print "Will fetch", maxpage, "pages"

	page_no = 0
	matchset = []
	if 'onsen' in content:
		print content
		raise Exception("WTF")
	while page_no < maxpage and page_no < len(pages):
		page_url = "%s&getcnt=0&pagecnt=%i" % (url, pages[page_no])
		page_no += 1
		if page_no == 1:
			# We already have page 1
			print "Using pre-fetched content at", url
			page_content = unicode(content, 'utf-8', 'replace')
		else:
			print "Fetching a new bunch of content."
			page_content = unicode(get_page(page_url, cached=cached).read(), 'utf-8', 'replace')

		xml = html.fromstring(page_content)
		itemlist = list()
		for item_xml in xml.xpath('//td[@class="product_box"]'):
			try:
				item = {}

				itemlink, = list(set(item_xml.xpath('div[@class="product_img"]/a/@href')))
				item['url'] = str(itemlink)
				url_match = re.search(r'gcode=(.*?)&', item['url'])
				if not url_match:
					raise Exception("Bad URL: %s" % item['url'])
				item['url'] = item['url'].split('&')[0]
				item['code'] = url_match.group(1)

				imgurl, = item_xml.xpath('div[@class="product_img"]/a/img/@src')
				item['image'] = str(imgurl).replace('thumbnail','qvga')
				if 'noimage.gif' in item['image']:
					item['image'] = None

				status_elts = item_xml.xpath('ul[@class="product_ul"]/li[@class="product_day"]//text()')
				item['stock'] = 'Now on sale'
				# Back-order?
				if len(status_elts) == 3:
					if 'Sold out' in str(status_elts[2]):
						item['stock'] = 'Sold out'
					status = str(status_elts[1])
				elif len(status_elts) < 2:
					item['stock'] = None
					status = ': '
				else:
					status = str(status_elts[1])

				if status == ': Preorder':
					item['status'] = 'preorder'
				elif status == ': Tentative Preorder':
					item['status'] = 'tentative-preorder'
				elif status == ': Provisional Preorder':
					item['status'] = 'tentative-preorder'
				elif status == ': Preorder(Tentative)':
					item['status'] = 'tentative-preorder'
				elif status == ': Reorder':
					item['status'] = 'reorder'
				elif status == ': Back-order':
					item['status'] = 'back-order'
				elif status == ': Released':
					item['status'] = 'released'
				elif status == ': ':
					item['status'] = None
				elif status == ': Sold out':
					item['status'] = 'soldout'
				else:
					raise Exception("Bad status: %r" % status)

				descr_zone = html.tostring(item_xml.xpath('ul[@class="product_ul"]/li[@class="product_name_list"]/a')[0])
				matcher = re.match(ur'.*?>(.*)<!-- &nbsp;&lt;&nbsp;(.*?)&nbsp;&gt; -->.*', unicode(descr_zone)) # Combat terrible HTML encoding
				if matcher:
					item['description'] = matcher.group(1)
					if len(item['description']) == 0:
						item['description'] = None
					item['release_date'] = matcher.group(2)
				else:
					item['description'] = None
					item['release_date'] = None


				price_bits = item_xml.xpath('ul[@class="product_ul"]/li[@class="product_price"]//text()')
				#item['discount'] = int(off)
				#item['price'] = int(re.sub('[^0-9]', '', price))
				if len(price_bits) == 3:
					if '%' not in str(price_bits[1]):
						raise Exception("Bad discount")
					item['discount'] = int(re.sub('[^0-9]', '', str(price_bits[1])))
					item['price'] = re.sub('[^0-9-]', '', str(price_bits[2]))
				else:
					item['discount'] = None
					item['price'] = re.sub('[^0-9-]', '', str(price_bits[0]))
				if '-' in item['price']:
					item['price'] = item['price'].split('-')[-1]
				item['price'] = int(item['price'])

				itemlist.append(item)
			except Exception, e:
				import traceback
				print html.tostring(item_xml)
				print traceback.format_exc()
				raise
				#continue

		# Note this may hit some items already hit above
		for item in itemlist:
			update(item, category=cat)

def diff(new, old):
	diff = []
	for key in set(new.keys() + old.keys()):
		if key == 'diff':
			continue
		elif key == 'url':
			continue
		if new.get(key) != old.get(key):
			if key == 'code':
				raise Exception("Can't update the code")
			diff += [(key, new.get(key), old.get(key))]
	return diff

def format_diff(diffarr):
	lines = []
	for row in diffarr:
		lines += [row[0] + u':' + unicode(row[1]).replace(u'\\', u'\\\\').replace(u',', u'\\,').replace(u';', u'\\;') + u"," + unicode(row[2]).replace(u'\\', u'\\\\').replace(u',', u'\\,').replace(u';', u'\\;')]
	return ';'.join(lines)

def update(new, product_id = None, old = None, category = None, needs_refresh=False):
	if product_id is None:
		curs.execute('select id, name, code, url, image, stock, status, price, discount, release_date from products where code=%(code)s', new)
		data = curs.fetchall()
		if len(data):
			d, = data
			product_id = d[0]
			old = {
				'description': unicode(d[1], 'utf8') if d[1] is not None else None,
				'code': d[2],
				'url': d[3],
				'image': d[4],
				'stock': d[5],
				'status': d[6],
				'price': d[7],
				'discount': d[8],
				'release_date': d[9],
			}
	if old is None:
		if update_raise:
			raise Exception("Unexpected update")
		curs.execute('''insert into products (name, url, code, image, stock, status, price, discount, release_date, last_site_update) values (%(description)s, %(url)s, %(code)s, %(image)s, %(stock)s, %(status)s, %(price)s, %(discount)s, %(release_date)s, now()) returning id''', new)
		(product_id,), = curs.fetchall()
		old = new.copy()
		mydiff = [('exists',True,'')]
	else:
		mydiff = diff(new, old)

	print "UPDATE", new['code'], mydiff
	if category != None:
		curs.execute('''insert into product_categories (product_id, category_id) select %s, c.id from categories c where c.code = %s and not exists (select 1 from product_categories pc where pc.product_id = %s and pc.category_id = c.id)''', (product_id, category, product_id))
		if curs.rowcount > 0:
			print "Category", category
			mydiff.append(('category',category,''))

	if not (mydiff or needs_refresh):
		print "No difference on %(url)s" % new
		return
	
	diffstr = format_diff(mydiff)
	print "Diff", diffstr

	updates = "name = %(description)s, image = %(image)s, stock = %(stock)s, status = %(status)s, price = %(price)s, discount = %(discount)s, release_date = %(release_date)s, url = %(url)s"

	if needs_refresh:
		updates += ', last_site_update = now()'
	
	if update_raise:
		raise Exception("Unexpected update")

	data = new.copy()
	data['id'] = product_id
	
	curs.execute('''update products set ''' + updates + ''' where id=%(id)s''', data)
	
	if len(mydiff) == 1 and mydiff[0][0] == 'discount' or len(mydiff) == 0:
		# Discount sometimes changes without product change.
		pass
	else:
		curs.execute('''insert into product_updates (product_id, diff) values(%s, %s)''', [product_id, diffstr])

if __name__ == '__main__':
	use_cache = True
	find_updates(cached=use_cache)
	update_raise = True
	find_updates(cached=True)
	update_raise = False
	curs.execute("select code, var, count(*) from categories join product_categories on category_id = categories.id group by 1, 2")
	cats = [ (r[0], r[1]) for r in curs.fetchall() ]
	modn = int(time.time() / 3600 + 1) % (len(cats)*10 + 1)
	if modn == len(cats)*10:
		find_categories()
	else:
		cat, cat_var = cats[modn % len(cats)]
		find_updates(cat=cat, cat_var=cat_var, cached=use_cache, perpage=1000)
	dsn.commit()
