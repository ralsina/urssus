# DB Classes
from __future__ import with_statement
import sqlalchemy as sql
import elixir as elixir
import migrate as migrate
import database
import os, sys, time
from globals import *
from urllib import urlopen
import urlparse


# Mark Pilgrim's Feed Parser
import feedparser as fp
fp.USER_AGENT = 'uRSSus/%s +http://urssus.googlecode.com/'%VERSION
# Configuration
import config

# Logging
if sys.platform=='win32':
  # easylog and Processing on windows == broken
  def dumb(*a, **kw):
    pass
  critical=dumb
  error=dumb
  warning=dumb
  debug=dumb
  info=dumb 
  setLogger=dumb 
  DEBUG=dumb
else:
  from easylog import critical, error, warning, debug, info, setLogger, DEBUG
#  setLogger(name='urssus', level=DEBUG)

from feedupdater import updateOne

# Some feeds put html in titles, which can't be shown in QStandardItems
from html2text import html2text as h2t

def detailToTitle(td):
  '''Converts something like feedparser's title_detail into a 
  nice text or html string.'''
  # Title may be in plain title, but a title_detail is preferred
  if td.type=='text/html':
    title=h2t(td.value).strip().replace('\n', ' ')
  else:
    title=td.value.strip()    
  return title

def detailToAuthor(ad):
  '''Converts something like feedparser's author_detail into a 
  nice string describing the author'''

  if 'name' in ad:
    author=ad['name']
    if 'href' in ad:
      author='<a href="%s">%s</a>'%(ad['href'], author)
  if 'email' in ad:
    email ='<a href="mailto:%s">%s</a>'%(ad['email'], ad['email'])
  else:
    email = ''

  if email and author:
    return '%s - %s'%(author, email)
  elif email:
    return email
  return author

# Patch from http://elixir.ematia.de/trac/wiki/Recipes/GetByOrAddPattern
def get_by_or_init(cls, if_new_set={}, **params):
  """Call get_by; if no object is returned, initialize an
  object with the same parameters.  If a new object was
  created, set any initial values."""
  
  result = cls.get_by(**params)
  if not result:
    result = cls(**params)
    result.set(**if_new_set)
  return result

elixir.Entity.get_by_or_init = classmethod(get_by_or_init)

elixir.metadata.bind = database.dbUrl
#elixir.metadata.bind.echo = True

class Post(elixir.Entity):
  elixir.using_options (tablename='posts')
  feed        = elixir.ManyToOne('Feed')
  title       = elixir.Field(elixir.Text)
  post_id     = elixir.Field(elixir.Text)
  content     = elixir.Field(elixir.Text)
  date        = elixir.Field(elixir.DateTime)
  unread      = elixir.Field(elixir.Boolean, default=True)
  important   = elixir.Field(elixir.Boolean, default=False)
  author      = elixir.Field(elixir.Text)
  link        = elixir.Field(elixir.Text)
  deleted     = elixir.Field(elixir.Boolean, default=False)
  # Added in schema version 5
  fresh       = elixir.Field(elixir.Boolean, default=True)

  decoTitle    = ''

  def __repr__(self):
    if not self.decoTitle:
      self.decoTitle=h2t(self.title).strip().replace('\n', ' ')
    return self.decoTitle
    
  def titleLink(self):
    if self.link:
      return '<a href="%s">%s</a>'%(self.link, unicode(self))
    return self.title

class Feed(elixir.Entity):
  elixir.using_options (tablename='feeds', inheritance='multi')
  htmlUrl        = elixir.Field(elixir.Text)
  xmlUrl         = elixir.Field(elixir.Text)
  title          = elixir.Field(elixir.Text)
  text           = elixir.Field(elixir.Text, default='')
  description    = elixir.Field(elixir.Text)
  children       = elixir.OneToMany('Feed', inverse='parent', order_by='position')
  parent         = elixir.ManyToOne('Feed')
  posts          = elixir.OneToMany('Post', order_by="-date", inverse='feed')
  lastUpdated    = elixir.Field(elixir.DateTime, default=datetime.datetime(1970,1,1))
  loadFull       = elixir.Field(elixir.Boolean, default=False)
  # meaning of archiveType:
  # 0 = use default, 1 = keepall, 2 = use limitCount
  # 3 = use limitDays, 4 = no archiving
  archiveType    = elixir.Field(elixir.Integer, default=0) 
  limitCount     = elixir.Field(elixir.Integer, default=1000)
  limitDays      = elixir.Field(elixir.Integer, default=60)

  notify         = elixir.Field(elixir.Boolean, default=False)
  markRead       = elixir.Field(elixir.Boolean, default=False)
  icon           = elixir.Field(elixir.Binary, deferred=True)
  # updateInterval -1 means use the app default, any other value, it's in minutes
  updateInterval = elixir.Field(elixir.Integer, default=-1)
  # Added in schema version 3
  position       = elixir.Field(elixir.Integer, default=0)
  # Added in schema version 4
  is_open        = elixir.Field(elixir.Integer, default=0)
  curUnread      = -1
  # Added in schema version 6
  subtitle       = elixir.Field(elixir.Text, default='')
  # Added in schema version 7
  etag           = elixir.Field(elixir.Text, default='')
  # Added in schema version 7
  lastModified   = elixir.Field(elixir.DateTime, colname="last-modified", default=datetime.datetime(1970,1,1))
  
  def __repr__(self):
    return self.text

  def titleLink(self):
    if self.title:
      title=self.title
    else:
      title=self.text
    if self.htmlUrl:
      return '<a href="%s">%s</a>'%(self.htmlUrl, title)
    return title

  def markAsRead(self):
    if self.xmlUrl: # regular feed
      Post.table.update().where(Post.unread==True).where(Post.feed==self).values(unread=False).execute()
    else: # A folder
      for feed in self.allFeeds():
        feed.markAsRead()
    elixir.session.flush()
    # Put in queue for status update [parents too]
    self.curUnread=-1
    self.unreadCount()
    feedStatusQueue.put([2, self.id, True])
    

  def expire(self, expunge=False):
    '''Delete all posts that are too old'''
    # meaning of archiveType:
    # 0 = use default, 1 = keepall, 2 = use limitCount
    # 3 = use limitDays, 4 = no archiving
    now=datetime.datetime.now()
    if self.archiveType==0: # Default archive config
      days=config.getValue('options', 'defaultExpiration', 7)
      cutoff=now-datetime.timedelta(7, 0, 0)
      Post.table.update().where(sql.and_(Post.important==False,  
                                         Post.feed==self, 
                                         Post.date<cutoff)).\
                          values(deleted=True).execute()
      elixir.session.flush()
    elif self.archiveType==1: #keepall
      # Tested ;-)
      return
    elif self.archiveType==2: #limitCount
      # FIXME: implement quicker!
      # Doesn't seem to work
      for post in self.posts[self.limitCount:]:
        if post.important: continue # Don't delete important stuff
        post.deleted=True
      elixir.session.flush()
    elif self.archiveType==3: #limitDays
      # Tested
      cutoff=now-datetime.timedelta(self.limitDays, 0, 0)
      Post.table.update().where(sql.and_(Post.important==False, 
                                         Post.date<cutoff)).\
                          values(deleted=True).execute()
      elixir.session.flush()
    elif self.archiveType==4: #no archiving
      # Tested
      Post.table.update().where(sql.and_(Post.important==False, 
                                         Post.feed==self)).\
                          values(deleted=True).execute()
      elixir.session.flush()
        
    if expunge:
      # Delete all posts with deleted==True, which are not fresh 
      # (are not in the last RSS/Atom we got)
      Post.table.delete().where(sql.and_(Post.deleted==True,Post.fresh==False,Post.feed==self)).execute()

      elixir.session.flush()
      
    # Force recount
    self.curUnread=-1
    self.unreadCount()

  def allFeeds(self):
    '''Returns a list of all "real" feeds that have this one as ancestor'''
    if not self.children:
      return [self]
    feeds=[]
    for child in self.children:
      feeds.extend(child.allFeeds())
    return feeds

  def allPostsQuery(self):
    '''Returns a query that should give you all the posts contained in this folder's children
    down to any level. Required for aggregate feeds, I'm afraid'''
    af=[feed.id for feed in self.allFeeds()]
    return Post.query.filter(Post.table._columns.get('feed_id').in_(af))

  def allPosts(self):
    '''This is used if you want all posts in this feed as well as in its childrens.
    Obviously meant to be used with folders, not regular feeds ;-)
    '''
    if self.xmlUrl: #I'm not a folder
      return []
    info("allposts for feed: %s", self)
    
    # Get posts for all children
    posts=[]
    for child in self.children:
      posts.extend(child.posts)
    return posts
    
  def previousSibling(self):
    if not self.parent: return None
    sibs=self.parent.children
    ind=sibs.index(self)
    if ind==0: return None
    else:
      return sibs[ind-1]

  def nextSibling(self):
    if not self.parent: return None
    sibs=self.parent.children
    ind=sibs.index(self)+1
    if ind >= len(sibs):
      return None
    return sibs[ind]

  def lastChild(self):
    '''Goes to the last possible child of this feed (the last child of the last child ....)'''
    if not self.children:
      return self
    else:
      return self.children[-1].lastChild()

  def previousFeed(self):
    # Search for a sibling above this one, then dig
    sib=self.previousSibling()
    if sib:
      return sib.lastChild()
    else:
      # Go to parent
      if self.parent:
        return self.parent
    # We are probably at the root
    return None

  def nextFeed(self):
    # First see if we have children
    if len(self.children):
      return self.children[0]
    # Then search for a sibling below this one
    sib=self.nextSibling()
    if sib:
      return sib
    else:
      # Go to next uncle/greatuncle/whatever
      parent=self.parent
      while parent:
        nextSib=parent.nextSibling()
        if nextSib: return nextSib.nextFeed()
        parent=parent.parent
    return None

  def previousUnreadFeed(self):
    # If there are no unread articles, there is no point
    if Post.query.filter(Post.unread==True).count()==0:
      return None
      
    # First see if there is any sibling with unread items above this one
    if not self.parent: # At root feed
      return self.lastChild().previousUnreadFeed()
    sibs=self.parent.children
    sibs=sibs[:sibs.index(self)]
    sibs.reverse()
    for sib in sibs:
      if sib.unreadCount():
        if sib.xmlUrl:
          return sib
        else:
          return sib.lastChild().previousUnreadFeed()
    # Then see if our parent is the answer
    if self.parent and self.parent.unreadCount():
      if self.parent.xmlUrl:
        return self.parent
      else:
        return self.parent.lastChild().previousUnreadFeed()
    elif self.parent:
      # Not him, pass the ball to uncle/gramps/whatever
      return self.parent.previousUnreadFeed()
    # Maybe should go to the *last* feed with unread articles, but it's
    # a corner case
    return None

  def nextUnreadFeed(self):
    # If there are no unread articles, there is no point
    if Post.query.filter(Post.unread==True).count()==0:
      return None
    # First see if we have children with unread articles
    if len(self.children):
      for child in self.children:
        if child.unreadCount():
          if child.xmlUrl:
            return child
          else: # Skip folders
            return child.nextUnreadFeed()
            
    if not self.parent: 
      # We are the root feed, and have no children unread: there's no unread
      return None

    # Then search for a sibling with unread items below this one
    
    sib=self.nextSibling()
    while sib:
      if sib.unreadCount():
        if sib.xmlUrl:
          return sib
        else:
          return sib.nextUnreadFeed()
      sib=sib.nextSibling()

    # Go to next uncle/greatuncle/whatever
    parent=self.parent
    while parent:
      nextSib=parent.nextSibling()
      # Parent is surely a folder
      if nextSib: return nextSib.nextUnreadFeed()
      parent=parent.parent
    # There is nothing below, so go to the top and try again
    return root_feed.nextUnreadFeed()

  def unreadCount(self):
    if self.children:
      self.curUnread=sum([ f.unreadCount() for f in self.children])
    else:
      if self.curUnread==-1:
        info ("Forcing recount in %s", self.title)
        self.curUnread=Post.query.filter(Post.feed==self).filter(Post.deleted==False).filter(Post.unread==True).count()
    return self.curUnread
      
  def updateFeedData(self, parsedFeed):
    # Fills blanks in feed data from parsedFeed
    # assumes this feed has a xmlUrl, fetches any missing data from it
    if not self.xmlUrl: # Nowhere to fetch data from
      return
      
    # See if we have all data:
    if self.htmlUrl and self.title and self.subtitle and self.description:
      return
    
    d=parsedFeed
    
    if not self.htmlUrl:
      if 'link' in d['feed']:
        self.htmlUrl=d['feed']['link']
      else:
        # This happens, for instance, on deleted blogger blogs (everyone's clever)
        self.htmlUrl=None
        
    if not self.title:
      if 'title_detail' in d['feed']: 
        self.title=detailToTitle(d['feed']['title_detail'])
      else:
        self.title=d['feed']['title']
    else:
      # This happens, for instance, on deleted blogger blogs (everyone's clever)
      self.title=''

    if not self.subtitle:
      if 'subtitle_detail' in d['feed']: 
        self.subtitle=detailToTitle(d['feed']['subtitle_detail'])
      elif 'subtitle' in d['feed']:
        self.subtitle=d['feed']['subtitle']
      else:
        self.subtitle=''

    if not self.description:
      if 'info' in d['feed']:
        self.description=d['feed']['info']
      elif 'description' in d['feed']:
        self.description=d['feed']['description']
    if not self.icon and self.htmlUrl:
      try:
        # FIXME: handle 404, 403 whatever errors
        self.icon=urlopen(urlparse.urljoin(self.htmlUrl,'/favicon.ico')).read()
        open('/tmp/icon.ico', 'w').write(self.icon)
      except:
        pass #I am not going to care about errors here :-D
    elixir.session.flush()
    
  def update(self, forced=False):
    feedStatusQueue.put([0, self.id])
    try:
      self.real_update(forced)
    except: # FIXME: reraise
      pass
    feedStatusQueue.put([1, self.id])
    
  def real_update(self, forced=False):
    if not self.xmlUrl: # Not a real feed
      af=self.allFeeds()
      for f in af:
        f.update()

    if self.lastModified:
      mod=self.lastModified
    else:
      mod=datetime.datetime(1970, 1, 1)
      
    if self.title:
      statusQueue.put(u"Updating: "+ self.title)
    d=fp.parse(self.xmlUrl, etag=self.etag, modified=mod.timetuple())
    
    if d.status==304 and not forced: # No need to fetch
      return
    if d.status==301: # Permanent redirect
      self.xmlUrl=d.href
    if d.status==410: # Feed deleted. FIXME: tell the user and stop trying!
      return

    posts=[]
    for post in d['entries']:
      try:
        # Date can be one of several fields
        if 'created_parsed' in post:
          dkey='created_parsed'
        elif 'published_parsed' in post:
          dkey='published_parsed'
        elif 'modified_parsed' in post:
          dkey='modified_parsed'
        else:
          dkey=None
        if dkey and post[dkey]:
          date=datetime.datetime.fromtimestamp(time.mktime(post[dkey]))
        else:
          date=datetime.datetime.now()
        
        # So can the "unique ID for this entry"
        if 'id' in post:
          idkey='id'
        elif 'link' in post:
          idkey='link'
       
        # So can the content
       
        if 'content' in post:
          content='<hr>'.join([ c.value for c in post['content']])
        elif 'summary' in post:
          content=post['summary']
        elif 'value' in post:
          content=post['value']
         
        # Rudimentary NON-html detection
        if not '<' in content:
          content=escape(content).replace('\n\n','<p>')
         
        # Author if available, else None
        author=''
        # First, we may have author_detail, which is the nicer one
        if 'author_detail' in post:
          ad=post['author_detail']
          author=detailToAuthor(ad)
        # Or maybe just an author
        elif 'author' in post:
          author=post['author']
          
        # But we may have a list of contributors
        if 'contributors' in post:
          # Which may have the same detail as the author's
          author+=' - '.join([ detailToAuthor(contrib) for contrib in post[contributors]])
        if not author:
          #FIXME: how about using the feed's author, or something like that
          author=None
          
        # The link should be simple ;-)
        if 'link' in post:
          link=post['link']
        else:
            link=None
            
        # Titles may be in plain title, but a title_detail is preferred
        if 'title_detail' in post:
          title=detailToTitle(post['title_detail'])
        else:
          title=post['title']

          
        # FIXME: if I use date to check here, I get duplicates on posts where I use
        # artificial date because it's not in the feed's entry.
        # If I don't I don't re-get updated posts.
        p = Post.get_by(feed=self, title=title,post_id=post[idkey])
        if not p:
          p=Post(feed=self, date=date, title=title, 
                 post_id=post[idkey], content=content, 
                 author=author, link=link)
          if self.markRead:
            p.unread=False
          posts.append(p)
      except KeyError:
        debug( post )
    self.lastUpdated=datetime.datetime.now()
    self.updateFeedData(d)
    if 'modified' in d:
      self.lastModified=datetime.datetime(*d['modified'][:6])
    if 'etag' in d:
      self.etag=d['etag']

    # Silly way to release the posts objects
    # we don't need anymore
    posts=[post.id for post in posts]

    if posts:
      with elixir.session.begin():
        # Fix freshness
        Post.table.update().where(sql.except_(Post.table.select(Post.id.in_(posts)))).values(fresh=False)
        elixir.session.commit()

      # Mark feed UI for updating
      self.curUnread=-1
      self.unreadCount()
      feedStatusQueue.put([2, self.id])

      # Queue a notification if needed
      if self.notify:
        feedStatusQueue.put([3, self.id, len(posts)])
    
  def getQuery(self):
    if self.xmlUrl:
      return Post.query.filter(Post.feed==self)
    else:
      return self.allPostsQuery()

root_feed=None

def initDB():
  global root_feed
  REQUIRED_SCHEMA=9
  # FIXME: show what we are doing on the UI
  if not os.path.exists(database.dbfile): # Just create it
    os.system('urssus_upgrade_db')
  else: # May need to upgrade
    try:
      curVer=migrate.versioning.api.db_version(database.dbUrl, database.repo)
    except:
      curVer=0
    if curVer < REQUIRED_SCHEMA:
      info ("UPGRADING from %s to %s", curVer, REQUIRED_SCHEMA)
      os.system('urssus_upgrade_db')

  import sqlite3
  def connect():
    conn = sqlite3.connect(database.dbfile)
    conn.isolation_level = "IMMEDIATE"
    return conn
  engine = sql.create_engine(database.dbUrl, creator=connect) 
    
  elixir.metadata.bind = engine
  elixir.setup_all()
  elixir.session.flush()
  root_feed=Feed.get_by_or_init(parent=None)
  root_feed.text='All Feeds'
  elixir.session.flush()
