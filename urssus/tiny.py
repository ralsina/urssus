"""Converts long URLs to tiny URLs, with either tinyurl, urltea, or a custom url."""

__author__="Andrew Pennebaker (andrew.pennebaker@gmail.com)"
__date__="22 Jun 2007 - 24 Jun 2007"
__copyright__="Copyright 2007 Andrew Pennebaker"
__license__="GPL"
__version__="0.0.1"
__URL__="http://snippets.dzone.com/posts/show/4195"
__credits__="http://lateral.netmanagers.com.ar/weblog/2007/04/08.html#BB548"

import urllib

def tiny(url):
  try:
    instream=urllib.urlopen("http://tinyurl.com/api-create.php?url="+url)
    tinyurl=instream.read()
    instream.close()

    if len(tinyurl)==0:
      return url

    return tinyurl
  except IOError, e:
    return None
