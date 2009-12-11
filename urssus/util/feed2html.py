#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""feed2html.py

It takes anything that feedparser can handle, and turn them into HTML (or
other text formats using templates)

Required: Python 2.3 <http://python.org/>
Required: feedparser <http://feedparser.org/>
License: Python Software Foundation License

"""
############################################################################
# Configuration section - you can set up the basic configuration here, however
# you should be able to override them from command line arguments.
############################################################################

infile  = '-'
outfile = '-'

############################################################################
# End of configuration section
############################################################################

__author__      = 'Scott Yang <http://scott.yang.id.au/>'
__copyright__   = 'Copyright (c) 2005 Scott Yang'
__date__        = '2005-05-02'
__license__     = 'Python'
__url__         = 'http://scott.yang.id.au/project/feed2html'
__version__     = '1.0'

import sys
try:
    # module "feedparser" can be downloaded from Mark Pilgrim's website:
    # http://diveintomark.org/projects/feed_parser/
    import feedparser
except ImportError:
    print >>sys.stderr, """\
Error: Cannot import Python module "feedparser".  Please download and install 
this module from the following website:

    http://feedparser.org/
"""
    sys.exit(1)

import getopt
import os
import re
import time

class Template:
    """Generic template library. Initially implemented in bloglines2html.py"""
    
    re_parse = re.compile(r'<tpl:(\S+)\b(.*?)(?:/>|>(.*?)</tpl:\1>)', 
        re.U | re.S)
    re_parse_attr = re.compile(r'([a-z]+)\s*=\s*"([^"]*)"', re.U|re.I)

    # Default Date/Time format
    datetime_format = '%Y-%m-%d %H:%M:%S'

    def __init__(self):
        self.var = {}

    def format_datetime(self, data, format):
        return time.strftime(format, data)

    def get_charset(self):
        return 'utf-8'

    def parse(self, text):
        return self.re_parse.sub(self.process_tag, text)

    def parse_attr(self, text):
        return dict(self.re_parse_attr.findall(text.strip()))

    def process_tag(self, match):
        tag  = match.group(1)
        attr = self.parse_attr(match.group(2))
        data = match.group(3) or u''

        try:
            handler = getattr(self, 'tag_%s' % tag)
        except AttributeError:
            return ''
        else:
            result = handler(attr, data)
            if result is None:
                result = ''
            elif (isinstance(result, tuple) or 
                    isinstance(result, time.struct_time)) and len(result) == 9:
                result = self.format_datetime(result, 
                    attr.get('format', self.datetime_format))

            if 'filter' in attr:
                result = do_filters(result, attr['filter'])
 
            if isinstance(result, unicode):
                result = result.encode(self.get_charset())
            else:
                result = str(result)

            return result

    def tag_charset(self, attr, data):
        return self.get_charset()

    def tag_feed2html_author(self, attr, data):
        return __author__

    def tag_feed2html_copyright(self, attr, data):
        return __copyright__

    def tag_feed2html_version(self, attr, data):
        return __version__

    def tag_feed2html_url(self, attr, data):
        return __url__

    def tag_var(self, attr, data):
        # Handle <tpl:var name="foo" />
        val = self.var.get(attr.get('name'), attr.get('default', ''))
        if isinstance(val, unicode):
            val = val.encode(self.get_charset())
        return val


class RSSTemplate(Template):
    """Template with tag handlers for feed data."""

    re_range = re.compile(r'([\-\d]+)?(:([\-\d]+)?(:([\-\d]+)?)?)?')
    
    def __init__(self, feed):
        Template.__init__(self)
        self.feed = feed
        self.content = None
        self.contributors = None
        self.enclosures = None
        self.entries = None

    def get_charset(self):
        return self.feed.encoding

    def get_loop(self, obj, objattr, attr, data):
        def range_value(val):
            if val is None:
                return val
            else:
                return int(val)

        if obj:
            items = obj.get(objattr)
            if items:
                result = []
                if 'select' in attr:
                    match = self.re_range.match(attr['select'])
                    if match:
                        # Only a single item is selected.
                        match = [range_value(x) 
                            for x in list(match.group(1, 3, 5))]
                        items = items[slice(*match)]
                        
                for item in items:
                    setattr(self, objattr, item)
                    result.append(self.parse(data))

                setattr(self, objattr, None)
                return ''.join(result)

        return ''

    def get_value(self, obj, attr, data):
        if (obj is not None) and ('value' in attr):
            key = attr['value']
            detail = attr.get('detail')
            value = None

            # Check whether it is requesting a datetime field.
            if (key+'_parsed') in obj:
                return obj.get(key+'_parsed')

            # Check whether it is trying to get details.
            if detail:
                obj2 = attr.get('%s_detail' % key)
                if obj2:
                    value = obj2.get(detail)
            else:
                value = obj.get(key)

            if isinstance(value, basestring):
                return value

        return ''

    def tag_content(self, attr, data):
        return self.get_value(self.content, attr, data)

    def tag_contents(self, attr, data):
        return self.get_loop(self.entries, 'content', attr, data)

    def tag_contributor(self, attr, data):
        return self.get_value(self.contributors, attr, data)

    def tag_contributors(self, attr, data):
        return self.get_loop(self.entries, 'contributors', attr, data)

    def tag_enclosure(self, attr, data):
        return self.get_value(self.enclosures, attr, data)

    def tag_enclosures(self, attr, data):
        return self.get_loop(self.entries, 'enclosures', attr, data)

    def tag_entries(self, attr, data):
        return self.get_loop(self.feed, 'entries', attr, data)

    def tag_entry(self, attr, data):
        return self.get_value(self.entries, attr, data)

    def tag_feed(self, attr, data):
        return self.get_value(self.feed.feed, attr, data)

    def tag_if_not(self, attr, data):
        # Handle <tpl:if_not_tag tag="foo"> ... </tpl:if_not_tag>
        try:
            handler = getattr(self, 'tag_%s' % attr['tag'])
        except (AttributeError, KeyError):
            pass
        else:
            val = handler(attr, data)
            match = attr.get('match')

            if ((not match) and (not val)) or (match and (val != match)):
                return self.parse(data)

        return self.parse(data)

    def tag_if(self, attr, data):
        # Handle <tpl:if_tag tag="foo"> ... </tpl:if_tag>
        try:
            handler = getattr(self, 'tag_%s' % attr['tag'])
        except (AttributeError, KeyError):
            pass
        else:
            val = handler(attr, data)
            match = attr.get('match')

            if ((not match) and val) or (match and (val == match)):
                return self.parse(data)

        return ''

    def tag_now(self, attr, data):
        # Handle <tpl:now format="..." />
        return time.localtime()


def do_filters(data, filters):
    for f in filters.split(','):
        f = f.strip()

        # Try to find the filter using the global name space.
        try:
            f = globals()['filter_%s' % f]
        except KeyError:
            pass
        else:
            data = f(data)

    return data


def filter_basename(data):
    """Return the basename of the filename."""
    idx = data.rfind('/')
    if idx < 0:
        idx = data.rfind('\\')
        if idx < 0:
            return data

    return data[idx+1:]


def filter_reducespace(data):
    return re.sub(r'[\t\r\n\s]+', ' ', data).strip()


def filter_xml(data):
    """Escape the XML entities."""
    data = data.replace('&', '&amp;')
    data = data.replace('<', '&lt;')
    data = data.replace('>', '&gt;')
    return data


def filter_xmlq(data):
    """Escape the XML entities + quote, useful for XML attributes."""
    data = filter_xml(data)
    data = data.replace('"', '&quot;')
    return data


cmdline_help = """\
Usage:
    %s [options]

Options:
    -D var=val  Define variable equals to value.
    -h          Display this help message.
    -i input    Feed input. It can be an URL, a local file name, or '-' for 
                standard input. (Default standard input)
    -o output   HTML output. It can be a local file name, or '-' for standard 
                output. (Default standard output)
    -t tplfile  Template file name. If omitted, default template will be used.
"""

def main(argv):
    global infile, outfile

    try:
        opts, args = getopt.getopt(argv, 'D:hi:o:t:')
    except getopt.GetoptError, ex:
        print >>sys.stderr, 'Error: %s' % ex
        print >>sys.stderr, cmdline_help % os.path.basename(sys.argv[0])
        sys.exit(1)

    tplfile = None
    variables = {}

    for o, a in opts:
        if o == '-D':
            match = re.match('([^=]+)=(.*)', a)
            if match:
                variables[match.group(1)] = match.group(2)
        elif o == '-h':
            print cmdline_help % os.path.basename(sys.argv[0])
            sys.exit(0)
        elif o == '-i':
            infile = a
        elif o == '-o':
            outfile = a
        elif o == '-t':
            tplfile = a

    run_template(infile, outfile, tplfile, variables)


def main_cgi():
    import cgi
    import cgitb; cgitb.enable()

    print 'Content-Type: text/html'
    print

    form = cgi.FieldStorage()
    in_url = form['i'].value
    if not re.match('^https?://', in_url):
        raise Exception, 'Feed "%s" does not appear to be a HTTP URL.'

    try:
        tplfile = form['t'].value
    except KeyError:
        tplfile = None
    else:
        dirname = os.path.dirname(sys.argv[0])
        tplfile = os.path.normpath(os.path.join(dirname, tplfile))
        if not tplfile.startswith(dirname) or (not os.path.exists(tplfile)):
            tplfile = None

    run_template(in_url, tplfile=tplfile)


def run_template(i='-', o='-', tplfile=None, variables=None):
    # Parse the feed data and supply that to RSSTemplate object
    template = RSSTemplate(feedparser.parse(i))
    if variables:
        template.var.update(variables)

    # Initialise the template text
    if tplfile is None:
        tpltext = DEFAULT_TEMPLATE
    else:
        tpltext = open(tplfile, 'rb').read()

    result = template.parse(tpltext)
    return result


DEFAULT_TEMPLATE = """\
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
  <head>
    <meta http-equiv="Content-Type" content="text/html; charset=<tpl:charset filter="xmlq"/>" />
    <title><tpl:feed value="title" filter="xml" /></title>
  </head>
  <body>
    <div id="container">
      <h1><a href="<tpl:feed value="link" filter="xmlq"/>"><tpl:feed value="title" filter="xml"/></a></h1>
      <div id="content">
        <tpl:entries>
        <div class="entry">
          <h3><a href="<tpl:entry value="link" filter="xmlq"/>"><tpl:entry value="title" filter="xml" /></a></h3>
          <div class="entrybody"><tpl:entry value="summary" /></div>
          <p class="posted">Posted by <tpl:entry value="author" filter="xml" /> on <tpl:entry value="modified" /></p>
        </div>
        </tpl:entries>
      </div>
      <div id="footer">Generated on <tpl:now /> by <a href="<tpl:feed2html_url filter="xmlq"/>">Feed2HTML <tpl:feed2html_version /></a></div>
    </div>
  </body>
</html>
"""

if __name__ == '__main__':
    # Check whether we are fired from the command line or from CGI
    if os.environ.get('GATEWAY_INTERFACE'):
        main_cgi()
    else:
        main(sys.argv[1:])


# Revision history
# 
# 1.0: 2005-05-03 - Borrowed most of the code from bloglines2html.py and made
#   it work.
