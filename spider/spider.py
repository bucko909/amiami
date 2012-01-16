#!/usr/bin/python

import urllib2
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
	if cached and os.path.exists(CACHE + cache_name(url)):
		print "Use cache"
		return open(CACHE + cache_name(url), 'r')
	else:
		print "Fetch page"
		if not login.done:
			print "Logging in"
			urllib2.urlopen(prepare_req("http://www.amiami.jp/shop/?set=english"))
			login.done = True
		x = urllib2.urlopen(prepare_req(url))
		if cached or True:
			f = open(CACHE + cache_name(url), 'w')
			f.write(x.read())
			f.close()
			return open(CACHE + cache_name(url), 'r')
		else:
			return x

def find_categories():
	content = get_page("http://www.amiami.jp/shop/?set=english")
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

def find_updates(no_seq=False, seq_only=False, cat=None, cat_var='CategoryNickname', cached=False, full=False, perpage=1000, reseq=False):
	print "Finding updates on category", cat
	print "Cache:", cached
	print "Sequence only:", seq_only
	print "No seq:", no_seq
	print "Full:", full
	print "Per page:", perpage

	if reseq and ((not full) or no_seq or seq_only or cat):
		raise Exception("Can only reseq with full, no cat, seq")

	n = perpage

	if cat is not None:
		catpart = 'vgvar_1_name=%s&vgvar_1_value=%s&vgvar_1_operator=LIKE&' % (cat_var, cat)
	else:
		catpart = ''

	#'http://www.amiami.jp/shop?set=english&vgForm=SearchProducts&vgvar_1_name=e_originaltitle&vgvar_1_value=Touhou%20Project&vgvar_1_operator=LIKE&sort_1_name=sortkey&sort_1_direction=ASC&results_per_page=20&next=Next&previous=Previous&template=default/product/e_search_results.html'
	url1 = '''http://www.amiami.jp/shop/?vgform=SearchProducts&%svgvar_4_name=e_translated&vgvar_4_value=1&vgvar_4_operator=LIKE&sort_1_name=UpdateDate&Sort_1_direction=DESC&next=next&previous=previous&max_results=0&results_per_page=%i&template=default/product/e_search_results.html''' % (catpart, n)
	#url1 = '''http://www.amiami.jp/shop/?vgform=SearchProducts&vgvar_1_name=CategoryNickname&vgvar_1_value=_00459&vgvar_1_operator=LIKE&vgvar_4_name=e_translated&vgvar_4_value=1&vgvar_4_operator=LIKE&sort_1_name=UpdateDate&Sort_1_direction=DESC&next=next&previous=previous&max_results=0&results_per_page=40&template=default/product/e_search_results.html'''
	#http://www.amiami.jp/shop/?vgform=SearchProducts&vgvar_1_name=CategoryNickname&vgvar_1_value=_00459&vgvar_1_operator=LIKE&vgvar_2_name=e_translated&vgvar_2_value=1&vgvar_2_operator=LIKE&vgvar_3_name=e_Maker&vgvar_3_value=Good%20Smile%20Company&vgvar_3_operator=LIKE&sort_1_name=UpdateDate&Sort_1_direction=DESC&next=next&previous=previous&max_results=0&results_per_page=40&template=default/product/e_search_results.html
	#http://www.amiami.jp/shop/?vgform=SearchProducts&vgvar_1_name=CategoryNickname&vgvar_1_value=_00459&vgvar_1_operator=LIKE&vgvar_2_name=e_translated&vgvar_2_value=1&vgvar_2_operator=LIKE&vgvar_3_name=e_seriestitle&vgvar_3_value=figma&vgvar_3_operator=LIKE&sort_1_name=UpdateDate&Sort_1_direction=DESC&next=next&previous=previous&max_results=0&results_per_page=40&template=default/product/e_search_results.html
	#http://www.amiami.jp/shop/?vgform=SearchProducts&vgvar_1_name=CategoryNickname&vgvar_1_value=_00459&vgvar_1_operator=LIKE&vgvar_2_name=e_translated&vgvar_2_value=1&vgvar_2_operator=LIKE&vgvar_3_name=e_originaltitle&vgvar_3_value=ToHeart&vgvar_3_operator=LIKE&sort_1_name=UpdateDate&Sort_1_direction=DESC&next=next&previous=previous&max_results=0&results_per_page=40&template=default/product/e_search_results.html
	#url1 = '''http://www.amiami.jp/shop/?vgform=SearchProducts&vgvar_1_name=SaleItem&vgvar_1_value=1&vgvar_1_operator=LIKE&vgvar_2_name=CategoryNickname&vgvar_2_value=_00459&vgvar_2_operator=LIKE&vgvar_4_name=e_translated&vgvar_4_value=1&vgvar_4_operator=LIKE&sort_1_name=DiscountRate&Sort_1_direction=DESC&next=next&previous=previous&max_results=0&results_per_page=1000&template=default/product/e_search_results.html'''
	#url = 'http://www.amiami.jp/shop/?vgform=SearchProducts&page_number=7&search_id=1319360820563&template=default/product/e_search_results.html
	content = get_page(url1, cached=cached).read()
	pages = sorted(list(set(re.findall("(http://www.amiami.jp/shop/\\?vgform=SearchProducts&page_number=\\d+&search_id=\\d+&template=default/product/e_search_results.html)", content))), key = lambda x : int(re.search('(\\d+)', x).group(1)))
	seq = -1

	if not pages:
		pages = [url1]
	if full:
		maxpage = len(pages)
	else:
		k = int(math.log(len(pages),2))+1
		modn = int(time.time() / 3600 + 1) % 2**k
		maxpage = 2**max([ x for x in range(k+1) if modn % 2**x == 0 ])

	print "Will fetch", maxpage, "pages"

	page_no = 0
	matchset = []
	seq_done = no_seq
	seq_itemlist = list()
	while page_no < maxpage and page_no < len(pages):
		page_url = pages[page_no]
		page_no += 1
		if page_no == 1:
			# We already have page 1
			page_content = unicode(content, 'utf-8', 'replace')
		else:
			page_content = unicode(get_page(page_url, cached=cached).read(), 'utf-8', 'replace')

		xml = html.fromstring(page_content)
		itemlist = list()
		for item_xml in xml.xpath('//table//table//table'):
			try:
				item = {}
				itemlink, = list(set(item_xml.xpath('tr/td/a/@href')))
				item['url'] = str(itemlink)
				maybetype = item_xml.xpath('tr/td/img/@src')
				no_image = False
				if len(maybetype):
					if maybetype[0] == 'http://www.amiami.jp/images/product/thumbnail/noimage.gif':
						no_image = True
						if len(maybetype) == 2:
							status_url = str(maybetype[1])
						else:
							status_url = None
					else:
						status_url = str(maybetype[0])
				else:
					status_url = None
				if status_url == 'http://www.amiami.jp/images/en/e_nav-reorder.gif':
					item['status'] = 'reorder'
				elif status_url == 'http://www.amiami.jp/images/en/e_nav-preorder.gif':
					item['status'] = 'preorder'
				else:
					item['status'] = None
				if not no_image:
					imgurl, = list(set(item_xml.xpath('tr/td/a/img/@src')))
					item['image'] = imgurl.replace('\n','').replace('thumbnail','qvga')
				else:
					item['image'] = None
				descr = item_xml.xpath('tr/td/a/text()')
				if len(descr) == 0:
					item['description'] = None
				else:
					item['description'] = unicode(descr[0])
				price, = [ i for i in item_xml.xpath('tr/td//text()') if 'Sale Price' in i ]
				if price == '\n\nSale Price':
					price, off = item_xml.xpath('tr/td/span/b/text()')
					item['discount'] = int(off)
					item['price'] = int(re.sub('[^0-9]', '', price))
				else:
					item['discount'] = 0
					item['price'] = int(re.sub('[^0-9]', '', price))
				stock, = [ i for i in item_xml.xpath('tr/td//text()') if 'Stock:' in i ]
				stock, = re.search('Stock:\n\n\t(.+)\n\n', stock).groups()
				item['stock'] = str(stock)

				itemlist.append(item)
				#(descr, itemlink, imgurl, stock, typ, price, off, seq))
			except Exception, e:
				import traceback
				traceback.print_exc()
				continue

		if reseq:
			seq_itemlist.extend(itemlist)
			if page_no == maxpage:
				seq_itemlist.reverse()
				for item in seq_itemlist:
					update(item, seq='increment')
		elif (not seq_done) and (not no_seq):
			seq_done = page_no # We unset it later if we fail
			seq_itemlist.extend(itemlist)
			if cat is None:
				curs.execute('select id, name, url, image, stock, status, price, discount, updateseq from products order by updateseq desc limit %s', (n * page_no + 100,))
			else:
				curs.execute('select p.id, p.name, p.url, image, stock, status, price, discount, updateseq from products p join product_categories pc on pc.product_id = p.id join categories c on c.id = pc.category_id where c.code = %s order by updateseq desc limit %s', (cat, n * page_no + 100))
			matchset = [ (d[0], {
					'description': unicode(d[1], 'utf8') if d[1] is not None else None,
					'url': d[2],
					'image': d[3],
					'stock': d[4],
					'status': d[5],
					'price': d[6],
					'discount': d[7],
				}, d[8]) for d in curs.fetchall() ]
			matchset.reverse()

			# Need to find the items which have changed.
			revitems = list(reversed(seq_itemlist))
			itemi = -1
			dbi = None
			expectedupdates = list()
			hits = 0
			updates = 0
			for item in revitems:
				itemi += 1
				if dbi is None:
					match = [ i for (i, data) in zip(xrange(n),matchset) if data[1]['url'] == item['url'] ]
					if len(match) == 0:
						# Over 1000 updates?!
						print "Item not in match set:", matchset[0], len(revitems), len(matchset)
						if page_no == maxpage:
							maxpage += 1
						seq_done = False
						dsn.rollback()
						break
					dbi = match[0]
				skipcount = 0
				while skipcount < 5000 and dbi < len(matchset) and matchset[dbi][1]['url'] != item['url']:
					expectedupdates.append(matchset[dbi][1])
					skipcount += 1
					dbi += 1
				#if dbi < len(matchset) and matchset[dbi][1]['url'] != item['url'] and hits > 100:
				#	# If we got here, we have 20 items in our list, in a row, which are missing.
				#	print ":(", item, hits
				#	raise Exception("A fountain of tears")
				if skipcount > 100 and page_no < 5:
					print "Skipped too many; assuming we can sync at a lower point."
					if page_no == maxpage:
						maxpage += 1
					seq_done = False
					dsn.rollback()
					break
				if skipcount > 100:
					print "Skipped too many and dug too deep; just going to assume everything's an update."
					dbi = len(matchset)
					# Just start syncing
				if False:
					pass
				elif dbi < len(matchset) and item != matchset[dbi][1]:
					# This entry wasn't meant to have changed, but stock changes don't count in ordering.
					update(item, matchset[dbi][0], matchset[dbi][1], category=cat, seq='ignore')
					dbi += 1
					hits += 1
				elif dbi >= len(matchset):
					expectedupdates = [ u for u in expectedupdates if u['url'] != item['url'] ]
					updates += 1
					if cat is None:
						update(item, seq='increment', needs_refresh=True)
					else:
						#raise Exception("New product; can't sync to a sequence number")
						# Should be OK just to stick it at the end of the list; we'll put it in sequence later
						update(item, category=cat, seq='ignore', needs_refresh=True)
				else:
					dbi += 1
					hits += 1
			if seq_done:
				print "Matched", hits, "entries."
				print "Updated", updates, "entries."
				if len(expectedupdates):
					#raise Exception("Missed updates: " + str(expectedupdates))
					print "Missed updates: " + str(expectedupdates)
				if seq_only:
					break
			else:
				print "Could not sync items by page %i" % page_no
				
		if (seq_done is not False) and seq_done < page_no or no_seq:
			# Note this may hit some items already hit above
			for item in itemlist:
				update(item, category=cat, seq='ignore')

def diff(new, old):
	diff = []
	for key in set(new.keys() + old.keys()):
		if key == 'diff':
			continue
		if new.get(key) != old.get(key):
			if key == 'url':
				raise Exception("Can't update the URL")
			diff += [(key, new.get(key), old.get(key))]
	return diff

def format_diff(diffarr):
	lines = []
	for row in diffarr:
		lines += [row[0] + u':' + unicode(row[1]).replace(u'\\', u'\\\\').replace(u',', u'\\,').replace(u';', u'\\;') + u"," + unicode(row[2]).replace(u'\\', u'\\\\').replace(u',', u'\\,').replace(u';', u'\\;')]
	return ';'.join(lines)

def update(new, product_id = None, old = None, category = None, seq = None, needs_refresh=False):
	if product_id is None:
		curs.execute('select id, name, url, image, stock, status, price, discount from products where url=%(url)s', new)
		data = curs.fetchall()
		if len(data):
			d, = data
			product_id = d[0]
			old = {
				'description': unicode(d[1], 'utf8') if d[1] is not None else None,
				'url': d[2],
				'image': d[3],
				'stock': d[4],
				'status': d[5],
				'price': d[6],
				'discount': d[7],
			}
	if old is None:
		if update_raise:
			raise Exception("Unexpected update")
		curs.execute('''insert into products (name, url, image, stock, status, price, discount, updateseq, last_site_update) values (%(description)s, %(url)s, %(image)s, %(stock)s, %(status)s, %(price)s, %(discount)s, -100000, now()) returning id''', new)
		(product_id,), = curs.fetchall()
		old = new.copy()
		mydiff = [('exists',True,'')]
	else:
		mydiff = diff(new, old)

	print "UPDATE ", new['url']
	if category != None:
		curs.execute('''insert into product_categories (product_id, category_id) select %s, c.id from categories c where c.code = %s and not exists (select 1 from product_categories pc where pc.product_id = %s and pc.category_id = c.id)''', (product_id, category, product_id))
		if curs.rowcount > 0:
			print "Category", category
			mydiff.append(('category',category,''))

	if not (mydiff or needs_refresh or seq == 'increment'):
		print "No difference on %(url)s" % new
		return
	
	diffstr = format_diff(mydiff)
	print "Diff", diffstr

	updates = "name = %(description)s, image = %(image)s, stock = %(stock)s, status = %(status)s, price = %(price)s, discount = %(discount)s"

	if seq == 'increment':
		print "Incr seq"
		updates += ", updateseq = nextval('product_update_seq')"
	elif seq == 'ignore':
		# Just leave the sequence alone.
		pass
	else:
		raise Exception("Should not be here")

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
	find_updates(cached=False)
	update_raise = True
	find_updates(cached=True)
	update_raise = False
	dsn.commit()
	curs.execute("select code, var, count(*) from categories join product_categories on category_id = categories.id group by 1, 2")
	cats = [ (r[0], r[1]) for r in curs.fetchall() ]
	modn = int(time.time() / 3600 + 1) % (len(cats)*10 + 1)
	if modn == len(cats)*10:
		find_categories()
	else:
		cat, cat_var = cats[modn % len(cats)]
		# Should be seq_only
		find_updates(no_seq=True, cat=cat, cat_var=cat_var, cached=False, full=True, perpage=1000)
	dsn.commit()
