from urssus.dbtables import *
initDB()
for f in Feed.query.all():
	try:
		if not f.xmlUrl: continue
		print f.xmlUrl
		f.update()
		f.expire(purge=True)
	except:
		pass
