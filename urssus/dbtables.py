# -*- coding: utf-8 -*-

# uRSSus, a multiplatform GUI news agregator
# Copyright (C) 2008 Roberto Alsina
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# version 2 as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301, USA.

# DB Classes
from __future__ import with_statement
import sqlalchemy as sql
import elixir
import database
import os, sys, time
from globals import *
import urlparse
from norm import normalizar

# Not sure about this
from PyQt4 import QtCore, QtGui

# Mark Pilgrim's Feed Parser
from util import feedparser as fp
fp.USER_AGENT = 'uRSSus/%s +http://urssus.googlecode.com/'%VERSION
# Configuration
import config

from feedupdater import updateOne, updateOneNice

# Some feeds put html in titles, which can't be shown in QStandardItems
from util.html2text import html2text as h2t


import urllib
class MyUrlOpener(urllib.FancyURLopener):
  '''A url opener that fails on 404s, copied from 
  http://mail.python.org/pipermail/python-bugs-list/2006-February/032155.html'''
  
  def http_error_default(*args, **kwargs):
    return urllib.URLopener.http_error_default(*args, **kwargs)
    
urllib._urlopener=MyUrlOpener()

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
  tags        = elixir.Field(elixir.Text, default='')
  
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
  children       = elixir.OneToMany('Feed', inverse='parent', order_by='text', cascade="delete")
  parent         = elixir.ManyToOne('Feed')
  posts          = elixir.OneToMany('Post', order_by="-date", inverse='feed', cascade="delete,delete-orphan")
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
  updating       = False
  # Added in schema version 6
  subtitle       = elixir.Field(elixir.Text, default='')
  # Added in schema version 7
  etag           = elixir.Field(elixir.Text, default='')
  # Added in schema version 7
  lastModified   = elixir.Field(elixir.DateTime, colname="last-modified", default=datetime.datetime(1970,1,1))
  tags        = elixir.Field(elixir.Text, default='')


  def __repr__(self):
    return self.text

  def getChildren(self, order_by='-text'):
    # Always should use this accesor, so metafolders work transparently
    if order_by[0]=='-': 
      mul=-1
      order_by=order_by[1:]
    else: mul=1
    
    if order_by=='text':
      _cmp=lambda x, y: mul* cmp(normalizar(x.text.lower()), normalizar(y.text.lower()))
    elif order_by=='unreadCount':
      _cmp=lambda x, y: mul* cmp(x.unreadCount(), y.unreadCount())
    
    self.children.sort(cmp=_cmp)
    return self.children
    
  def removeChild(self, feed):
    self.children.remove(feed)
    
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
      try:
        Post.table.update().where(Post.unread==True).where(Post.feed==self).values(unread=False).execute()
        elixir.session.commit()
      except:
        elixir.session.rollback()
    else: # A folder
      for feed in self.allFeeds():
        feed.markAsRead()
    # Put in queue for status update
    feedStatusQueue.put([1, self.id])
    

  def expire(self, expunge=False):
    '''Delete all posts that are too old'''
    # meaning of archiveType:
    # 0 = use default, 1 = keepall, 2 = use limitCount
    # 3 = use limitDays, 4 = no archiving
    now=datetime.datetime.now()
    if self.archiveType==0: # Default archive config
      days=config.getValue('options', 'defaultExpiration', 7)
      cutoff=now-datetime.timedelta(7, 0, 0)
      try:
        Post.table.update().where(sql.and_(Post.important==False,  
                                         Post.feed==self, 
                                         Post.date<cutoff)).\
                            values(deleted=True).execute()
        elixir.session.commit()
      except:
        elixir.session.rollback()
    elif self.archiveType==1: #keepall
      # Tested ;-)
      return
    elif self.archiveType==2: #limitCount
      # FIXME: implement quicker!
      # Doesn't seem to work
      try:
        for post in self.posts[self.limitCount:]:
          if post.important: continue # Don't delete important stuff
          post.deleted=True
        elixir.session.commit()
      except:
        elixir.session.rollback()
        
    elif self.archiveType==3: #limitDays
      # Tested
      cutoff=now-datetime.timedelta(self.limitDays, 0, 0)
      try:
        Post.table.update().where(sql.and_(Post.important==False, 
                                          Post.date<cutoff)).\
                            values(deleted=True).execute()
        elixir.session.commit()
      except:
        elixir.session.rollback()
    elif self.archiveType==4: #no archiving
      try:
        Post.table.update().where(sql.and_(Post.important==False, 
                                          Post.feed==self)).\
                            values(deleted=True).execute()
        elixir.session.commit()
      except:
        elixir.session.rollback()
        
    if expunge:
      # Delete all posts with deleted==True, which are not fresh 
      # (are not in the last RSS/Atom we got)
      try:
        Post.table.delete().where(sql.and_(Post.deleted==True,
                                           Post.fresh==False,
                                           Post.feed==self)).execute()
        elixir.session.commit()
      except:
        elixir.session.rollback()
      
    # Force recount
    self.curUnread=-1
    self.unreadCount()

  def allFeeds(self):
    '''Returns a list of all "real" feeds that have this one as ancestor'''
    if not self.getChildren():
      return [self]
    feeds=[]
    for child in self.getChildren():
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
    debug("allposts for feed: %s"%self)
    
    # Get posts for all children
    posts=[]
    for child in self.getChildren():
      posts.extend(child.posts)
    return posts
    
  def previousSibling(self, order_by='-text'):
    if not self.parent: return None
    sibs=self.parent.getChildren(order_by=order_by)
    ind=sibs.index(self)
    if ind==0: return None
    else:
      return sibs[ind-1]

  def nextSibling(self, order_by='-text'):
    if not self.parent: return None
    sibs=self.parent.getChildren(order_by=order_by)
    ind=sibs.index(self)+1
    if ind >= len(sibs):
      return None
    return sibs[ind]

  def lastChild(self, order_by='-text'):
    '''Goes to the last possible child of this feed (the last child of the last child ....)'''
    if not self.getChildren(order_by=order_by):
      return self
    else:
      return self.getChildren()[-1].lastChild(order_by=order_by)

  def previousFeed(self, order_by='-text'):
    # Search for a sibling above this one, then dig
    sib=self.previousSibling(order_by=order_by)
    if sib:
      return sib.lastChild(order_by=order_by)
    else:
      # Go to parent
      if self.parent:
        return self.parent
    # We are probably at the root
    return None

  def nextFeed(self, order_by='-text'):
    # First see if we have children
    if len(self.getChildren(order_by=order_by)):
      return self.getChildren(order_by=order_by)[0]
    # Then search for a sibling below this one
    sib=self.nextSibling(order_by=order_by)
    if sib:
      return sib
    else:
      # Go to next uncle/greatuncle/whatever
      parent=self.parent
      while parent:
        nextSib=parent.nextSibling(order_by=order_by)
        if nextSib: return nextSib.nextFeed(order_by=order_by)
        parent=parent.parent
    return None

  def previousUnreadFeed(self, order_by='-text'):
    # If there are no unread articles, there is no point
    if root_feed.unreadCount()==0:
      return
      
    # First see if there is any sibling with unread items above this one
    if not self.parent: # At root feed
      return self.lastChild(order_by=order_by).previousUnreadFeed(order_by=order_by)
    sibs=self.parent.getChildren(order_by=order_by)
    sibs=sibs[:sibs.index(self)]
    sibs.reverse()
    for sib in sibs:
      if sib.unreadCount():
        if sib.xmlUrl:
          return sib
        else:
          return sib.lastChild(order_by=order_by).previousUnreadFeed(order_by=order_by)
    # Then see if our parent is the answer
    if self.parent and self.parent.unreadCount():
      if self.parent.xmlUrl:
        return self.parent
      else:
        return self.parent.lastChild(order_by=order_by).previousUnreadFeed(order_by=order_by)
    elif self.parent:
      # Not him, pass the ball to uncle/gramps/whatever
      return self.parent.previousUnreadFeed(order_by=order_by)
    # Maybe should go to the *last* feed with unread articles, but it's
    # a corner case
    return None

  def nextUnreadFeed(self, order_by='-text'):
    # If there are no unread articles, there is no point
    if root_feed.unreadCount()==0:
      return
    # First see if we have children with unread articles
    if len(self.getChildren(order_by=order_by)):
      for child in self.getChildren(order_by=order_by):
        if child.unreadCount():
          if child.xmlUrl:
            return child
          else: # Skip folders
            return child.nextUnreadFeed(order_by=order_by)
            
    if not self.parent: 
      # We are the root feed, and have no children unread: there's no unread
      return None

    # Then search for a sibling with unread items below this one
    
    sib=self.nextSibling(order_by=order_by)
    while sib:
      if sib.unreadCount():
        if sib.xmlUrl:
          return sib
        else:
          return sib.nextUnreadFeed(order_by=order_by)
      sib=sib.nextSibling(order_by=order_by)

    # Go to next uncle/greatuncle/whatever
    parent=self.parent
    while parent:
      nextSib=parent.nextSibling(order_by=order_by)
      # Parent is surely a folder
      if nextSib: return nextSib.nextUnreadFeed(order_by=order_by)
      parent=parent.parent
    # There is nothing below, so go to the top and try again
    return root_feed.nextUnreadFeed(order_by=order_by)

  def unreadCount(self):
    if self.getChildren():
      self.curUnread=sum([ f.unreadCount() for f in self.getChildren()])
    else:
      if self.curUnread==-1:
        debug ("Forcing recount in %s", self.title)
        self.curUnread=Post.query.filter(Post.feed==self).filter(Post.deleted==False).filter(Post.unread==True).count()
      else:
        debug ("Got cached recount")
    return self.curUnread
      
  def updateFeedData(self, parsedFeed):
    # Fills blanks in feed data from parsedFeed
      
    d=parsedFeed
    
    if not self.htmlUrl:
      if 'link' in d['feed']:
        self.htmlUrl=d['feed']['link']
      else:
        # This happens, for instance, on deleted blogger blogs (everyone's clever)
        self.htmlUrl=None
        
    if 'title_detail' in d['feed']: 
      self.title=detailToTitle(d['feed']['title_detail'])
    elif 'title' in d['feed']:
      self.title=d['feed']['title']
    else:
      # This happens, for instance, on deleted blogger blogs (everyone's clever)
      self.title=''
      
    if not self.text:
      self.text=self.title

    if 'subtitle_detail' in d['feed']: 
      self.subtitle=detailToTitle(d['feed']['subtitle_detail'])
    elif 'subtitle' in d['feed']:
      self.subtitle=d['feed']['subtitle']
    else:
      self.subtitle=''

    if 'info' in d['feed']:
      self.description=d['feed']['info']
    elif 'description' in d['feed']:
      self.description=d['feed']['description']

    if not self.icon and self.htmlUrl:
      try:
        iconUrl=urlparse.urljoin(self.htmlUrl,'/favicon.ico')
        self.icon=urllib.urlopen(iconUrl).read().encode('base64')
      except:
        pass #I am not going to care about errors here :-D
        
  def update(self, forced=False):
    u=self.unreadCount()
    try:
      self.real_update(forced)
    except: # FIXME: reraise
      pass
    # Add feed and parents to the update queue
    if self.unreadCount()<>u:
      p=self
      while p:
        feedStatusQueue.put([1, p.id])
        p=p.parent
    
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
    try:
      self.lastUpdated=datetime.datetime.now()
      elixir.session.commit()
    except:
      elixir.session.rollback()
    
    if d.status==304: # No need to fetch
      return
    if d.status==301: # Permanent redirect
      self.xmlUrl=d.href
    if d.status==410: # Feed deleted. FIXME: tell the user and stop trying!
      return
      
    self.updating=True
    # Notify feed is updating
#    feedStatusQueue.put([0, self.id])
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

        try:
          # FIXME: if I use date to check here, I get duplicates on posts where I use
          # artificial date because it's not in the feed's entry.
          # If I don't I don't re-get updated posts.
          p = Post.get_by(feed=self, post_id=post[idkey])
          if p:
            if p.content<>content:
              p.content=content
            if p.title<>title:
              p.title=title          
          else:
            # This is because of google news: the same news gets reposted over and over 
            # with different post_id :-(
            p = Post.get_by(feed=self, title=title)
            if p:
              if p.post_id<>post[idkey]:
                p.post_id=post[idkey]
              if p.content<>content:
                p.content=content
              if p.title<>title:
                p.title=title          
            else:
              p=Post(feed=self, date=date, title=title, 
                     post_id=post[idkey], content=content, 
                     author=author, link=link)
              if self.markRead:
                p.unread=False
              # Tag support
              if 'tags' in post:
                p.tags=','.join([t.term for t in post['tags']])
              posts.append(p)
          elixir.session.commit()
        except:
          traceback.print_exc(1)
          elixir.session.rollback()
      except KeyError:
        debug( post )
    try:
      self.updateFeedData(d)
      if 'modified' in d:
        self.lastModified=datetime.datetime(*d['modified'][:6])
      if 'etag' in d:
        self.etag=d['etag']
      elixir.session.commit()
    except:
      elixir.session.rollback()
  
    try:
      # Silly way to release the posts objects
      # we don't need anymore
      post_ids=[post.id for post in posts]
  
      if len(post_ids):
        # Mark feed UI for updating
        self.curUnread=-1
        # Fix freshness
        Post.table.update().where(sql.except_(Post.table.select(Post.feed==self), 
                                              Post.table.select(Post.id.in_(post_ids)))).\
                                              values(fresh=False).execute()
      elixir.session.commit()
    except:
      elixir.session.rollback()

  def getQuery(self):
    if self.xmlUrl:
      return Post.query.filter(Post.feed==self)
    else:
      return self.allPostsQuery()

  def getIcon(self):
    icon=None
    try:
      sicon=str(self.icon)
      if sicon and sicon<>'None':
        if sicon.startswith(':/'): # A resource name
          icon=QtGui.QIcon(sicon)
        else:    
          iconData=sicon.decode('base64') # An encoded binary
          pmap=QtGui.QPixmap()
          pmap.loadFromData(iconData)
          icon=QtGui.QIcon(pmap)
      elif self.xmlUrl:
        # No icon specified, but have xmlUrl:
          icon=QtGui.QIcon(':/urssus.svg')
      else:
        # A folder
          icon=QtGui.QIcon(':/folder.svg')
    except:
      pass # Te icon is not critical!
    return icon


class MetaFeed(Feed):
  elixir.using_options (tablename='metafeeds', inheritance='multi')
  condition   = elixir.Field(elixir.Text)
  _stamp = None

  def __repr__(self):
    return unicode(self.text or self.condition)
  
  def allPostsQuery(self):
    return Post.query.filter(eval(self.condition))

  def unreadCount(self):
    if self.curUnread==-1:
      info ("Forcing recount in %s"%self.text)
      self.curUnread=Post.query.filter(eval(self.condition)).filter(Post.deleted==False).filter(Post.unread==True).count()
    return self.curUnread

class MetaFolder(Feed):
  elixir.using_options (tablename='metafolders', inheritance='multi')
  condition   = elixir.Field(elixir.Text)
  
  def getChildren(self):
    return eval(self.condition)

  def removeChild(self, feed):
    '''Makes no sense in this context'''
    return

root_feed=None
starred_feed=None
unread_feed=None

def initDB():
  global root_feed, starred_feed, unread_feed, tags_feed
  elixir.metadata.bind = database.dbUrl
  # FIXME: show what we are doing on the UI
  if not os.path.exists(os.path.join(config.cfdir, 'urssus.sqlite')):
    elixir.setup_all()
    elixir.create_all()
  else:
    os.system('urssus_upgrade_db')
#  elixir.metadata.bind.echo = True
    elixir.setup_all()
  try:
    # Make sure we have a root feed
    root_feed=Feed.get_by_or_init(parent=None)
    root_feed.text='All Feeds'
    elixir.session.commit()
  except:
    elixir.session.rollback()

  try:
    # Delete old metafolders
    for mf in MetaFolder.query.all():
      mf.delete()
    for mf in MetaFeed.query.all():
      mf.delete()
    elixir.session.commit()
    # Add standard meta feeds
    starred_feed=MetaFeed(parent=None, 
                          condition='Post.important==True',
                          text='Important Articles', icon=':/star.svg')
    unread_feed=MetaFeed(parent=None, 
                           condition='Post.unread==True',
                           text='Unread Articles')                             
    elixir.session.commit()
  except:
    elixir.session.rollback()
