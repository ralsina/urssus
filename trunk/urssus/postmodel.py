from globals import *
from dbtables import *
from PyQt4 import QtGui, QtCore
import operator

# Roles used in the items
sorting=QtCore.Qt.UserRole
display=QtCore.Qt.DisplayRole
post_id=QtCore.Qt.UserRole+1

class PostModel(QtGui.QStandardItemModel):
  def __init__(self, parent, feed=None, textFilter=None, statusFilter=None):
    QtGui.QStandardItemModel.__init__(self, parent)
    self.feed_id=feed.id
    self.textFilter=textFilter
    self.statusFilter=statusFilter
    self.setSortRole(sorting)
    self._clear()
    column,order = config.getValue('ui','postSorting',[2,QtCore.Qt.DescendingOrder])
    self.sort(column,order) # Date, descending
    self.initData(feed)

  def _clear(self):
    self.clear()
    self.post_data=[]
    self.post_ids=[]
    self.setColumnCount(4)
    self.setHeaderData(0, QtCore.Qt.Horizontal, QtCore.QVariant(""))
    self.setHeaderData(1, QtCore.Qt.Horizontal, QtCore.QVariant("Title"))
    self.setHeaderData(2, QtCore.Qt.Horizontal, QtCore.QVariant("Date"))
    self.setHeaderData(3, QtCore.Qt.Horizontal, QtCore.QVariant("Feed"))
    self.postItems={}
    
  def initData(self, update=False):
    '''Sets data from the feedDB. If update==True, data is just added, not 
    replaced.
    '''
    feed=Feed.get_by(id=self.feed_id)
    if not feed or not update:
      self._clear()
    
    if feed.xmlUrl: # A regular feed
      self.posts=Post.query.filter(Post.feed==feed).filter(Post.deleted==False)
    else: # A folder
      self.posts=feed.allPostsQuery().filter(Post.deleted==False)
    # Filter by text according to the contents of self.textFilter
    if self.textFilter:
      self.posts=self.posts.filter(sql.or_(Post.title.like('%%%s%%'%self.textFilter), 
                                           Post.content.like('%%%s%%'%self.textFilter)))
    if self.statusFilter:
      self.posts=self.posts.filter(self.statusFilter==True)
  
    maxposts=config.getValue('options', 'maxPostsDisplayed', 1000)
    posts=self.posts.order_by(sql.desc('date')).limit(maxposts)
    for post in posts:
      # Keep references to posts instead of posts, to 
      # avoid stale data. nextPost/etc are about
      # iterating what's shown, not the result
      # of self.posts.all()
      
      if post.id in self.post_ids: #Existing post, update
        # FIXME: implement update fully
        self.post_data[self.post_ids.index(post.id)][5]=post.unread
        self.post_data[self.post_ids.index(post.id)][4]=post.important
        self.updateItem(post)
      else:
        # New post, add
        self.post_data.append([post.id, unicode(post).lower(), post.date,
                               unicode(post.feed).lower(), post.important, post.unread])
        item0=QtGui.QStandardItem()
        item0.setData(QtCore.QVariant(post.important), sorting)

        item1=QtGui.QStandardItem()
        item1.setToolTip('%s - Posted at %s'%(unicode(post), unicode(post.date)))
        item1.setData(QtCore.QVariant(unicode(post)), display)
        item1.setData(QtCore.QVariant(unicode(post).lower()), sorting)
        item1.setData(QtCore.QVariant(post.id), post_id)
        
        item2=QtGui.QStandardItem()
        item2.setToolTip('%s - Posted at %s'%(unicode(post), unicode(post.date)))
        item2.setData(QtCore.QVariant(unicode(utc2local(post.date))), display)
        d=utc2local(post.date)
        # AOL Fanhouse posts items with a time differential of milliseconds, so they sorted
        # differently on python and Qt. If someone makesit to microseconds, this solution
        # is borked
        qd=QtCore.QVariant(QtCore.QDateTime(QtCore.QDate(d.year, d.month, d.day), 
                                            QtCore.QTime(d.hour, d.minute, d.second, d.microsecond/1000)))
        item2.setData(qd, sorting)
        item2.setData(QtCore.QVariant(post.id), post_id)

        item3=QtGui.QStandardItem()
        item3.setData(QtCore.QVariant(unicode(post.feed)), display)
        item3.setData(QtCore.QVariant(unicode(post.feed).lower()), sorting)

        self.postItems[post.id]=[item0, item1, item2, item3]
        self.appendRow([item0, item1, item2, item3])
        self.updateItem(post)
      
    self.reset()
 
    if update: # New data, resort
      self.sort(*self.lastSort)

  def hasPost(self, post):
    return post.id in self.postItems

  def markRead(self):
    '''Marks as read what's shown by the model, as opposite to Feed.markAsRead, which
    marks what's on the feed. UI should call this one, usually'''''
    for d in self.post_data:
      if d[5]:
        if d[5]:
          d[5]=False
          post=Post.get_by(id=d[0])        
          post.unread=False
          post.feed.curUnread=-1
          self.updateItem(post)
    elixir.session.flush()
    self.reset()

  def indexFromPost(self, post=None, id=None):
    if not id and not post:
      return QtCore.QModelIndex()
    if not id:
      id=post.id
    if post and post.id in self.postItems:
      return self.indexFromItem(self.postItems[id][1])
    return QtCore.QModelIndex()
    
  def postFromIndex(self, index):
    if index.column()<>1:
      index=self.index(index.row(), 1, index.parent())      
    item=self.itemFromIndex(index)
    if item:
      id=item.data(post_id).toInt()[0]
      return Post.get_by(id=id)
    return None

  def updateItem(self, post):
    if not post.id in self.postItems: #post is not being displayed
      return
    item0, item1, item2, item3=self.postItems[post.id]
    # FIXME: respect the palette
    if post.important:
      item0.setIcon(QtGui.QIcon(':/star.svg'))
    else:
      item0.setIcon(QtGui.QIcon(':/star2.svg'))
    if post.unread:
      item1.setForeground(QtGui.QColor("darkgreen"))
      item2.setForeground(QtGui.QColor("darkgreen"))
      item3.setForeground(QtGui.QColor("darkgreen"))
    else:
      item1.setForeground(QtGui.QColor("black"))
      item2.setForeground(QtGui.QColor("black"))
      item3.setForeground(QtGui.QColor("black"))
      
    f=item1.font()
    if post.important or post.unread:
      f.setBold(True)
    else:
      f.setBold(False)
    item1.setFont(f)
    item2.setFont(f)
    item3.setFont(f)
    
    # Update our post_data, too. Probably not the best way
    # FIXME: not efficient
    self.post_ids=[id for [id, _, _, _, _, _] in self.post_data]
    idx=self.post_ids.index(post.id)
    self.post_data[idx]=[post.id, unicode(post).lower(), post.date,unicode(post.feed).lower(),post.important,post.unread]

  colkey=[5, 1, 2, 3]

  def sort(self, column, order):
    order = [QtCore.Qt.AscendingOrder,QtCore.Qt.DescendingOrder][order]
    # Thanks pyar!
    self.post_data.sort(key=operator.itemgetter(self.colkey[column]), 
                        reverse=order==QtCore.Qt.DescendingOrder)
    QtGui.QStandardItemModel.sort(self, column, order)
    self.post_ids=[id for [id, _, _, _, _, _] in self.post_data]
    self.lastSort=(column, order)
    config.setValue('ui','postSorting',[column,order])

  def nextPostIndex(self, post):
    '''Takes a Post and returns the index of the following post'''
    if not self.post_ids:
      return QtCore.QModelIndex()
    # First, find it in our list of ids
    if not post: 
      idx=-1
    else: 
      idx=self.post_ids.index(post.id)
    if idx==-1: #current post not here, so return the first
      return self.indexFromItem(self.postItems[self.post_ids[0]][1])
    elif idx==len(self.post_ids)-1: # Last post, no next
      return QtCore.QModelIndex()
    else:
      return self.indexFromItem(self.postItems[self.post_ids[idx+1]][1])

  def nextUnreadPostIndex(self, post):
    if not self.post_ids:
      return QtCore.QModelIndex()
      
    # Create filtered lists
    if post:
      unread_data=[x for x in self.post_data if x[5] or x[0]==post.id]
    else:
      unread_data=[x for x in self.post_data if x[5]]
    unread_ids=[id for [id, _, _, _, _, _] in unread_data]
    
    # And now it's pretty much like nextPostIndex
    # FIXME: merge them
    if not unread_ids:
      return QtCore.QModelIndex()
    # First, find it in our list of ids
    if not post: 
      idx=-1
    else: 
      idx=unread_ids.index(post.id)
    if idx==-1: #current post not here, so return the first
      return self.indexFromItem(self.postItems[unread_ids[0]][1])
    elif idx==len(unread_ids)-1: # Last post, no next
      return QtCore.QModelIndex()
    else:
      return self.indexFromItem(self.postItems[unread_ids[idx+1]][1])

  def previousPostIndex(self, post):
    '''Takes a Post and returns the index of the following post'''
    # First, find it in our list of ids
    if not self.post_ids:
      return QtCore.QModelIndex()
    if not post: 
      idx=-1
    else: 
      idx=self.post_ids.index(post.id)
    if idx==-1: #current post not here, so return the last
      return self.indexFromItem(self.postItems[self.post_ids[-1]][1])
    elif idx==0: # First post, no previous
      return QtCore.QModelIndex()
    else:
      return self.indexFromItem(self.postItems[self.post_ids[idx-1]][1])

  def previousUnreadPostIndex(self, post):
    if not self.post_ids:
      return QtCore.QModelIndex()
      
    # Create filtered lists
    if post:
      unread_data=[x for x in self.post_data if x[5] or x[0]==post.id]
    else:
      unread_data=[x for x in self.post_data if x[5]]
    unread_ids=[id for [id, _, _, _, _, _] in unread_data]
    
    # And now it's pretty much like previousPostIndex
    # FIXME: merge them
    if not unread_ids:
      return QtCore.QModelIndex()
    # First, find it in our list of ids
    if not post: 
      idx=-1
    else: 
      idx=unread_ids.index(post.id)
    if idx==-1: #current post not here, so return the last
      return self.indexFromItem(self.postItems[unread_ids[-1]][1])
    elif idx==0: # First post, no previous
      return QtCore.QModelIndex()
    else:
      return self.indexFromItem(self.postItems[unread_ids[idx-1]][1])
