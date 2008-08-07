from sqlalchemy import *
from elixir import *
from datetime import datetime
from migrate import *
from migrate.changeset import schema

meta = MetaData(migrate_engine)
class Feed(Entity):
  using_options (tablename='feeds', metadata=meta, inheritance='multi')
  htmlUrl        = Field(Text)
  xmlUrl         = Field(Text)
  title          = Field(Text)
  text           = Field(Text, default='')
  description    = Field(Text)
  children       = OneToMany('Feed', inverse='parent')
  parent         = ManyToOne('Feed')
  posts          = OneToMany('Post', order_by="-date", inverse='feed')
  lastUpdated    = Field(DateTime, default=datetime(1970,1,1))
  loadFull       = Field(Boolean, default=False)
  archiveType    = Field(Integer, default=0) 
  limitCount     = Field(Integer, default=1000)
  limitDays      = Field(Integer, default=60)
  notify         = Field(Boolean, default=False)
  markRead       = Field(Boolean, default=False)
  icon           = Field(Binary, deferred=True)
  updateInterval = Field(Integer, default=-1)
  position       = Field(Integer, default=0)
  subtitle       = Field(Text, default=0)
  etag           = Field(Text, default='')
  lastModified   = Field(DateTime, default=datetime(1970,1,1),colname="last-modified")
  
class Post(Entity):
  using_options (tablename='posts', metadata=meta)
  feed        = ManyToOne('Feed', inverse='posts')
  title       = Field(Text)
  post_id     = Field(Text)
  content     = Field(Text)
  date        = Field(DateTime)
  unread      = Field(Boolean, default=True)
  important   = Field(Boolean, default=False)
  author      = Field(Text)
  link        = Field(Text)
  deleted     = Field(Boolean, default=False)

setup_all()

def upgrade():
  # This doesn't work for some reason :-(
  # Feed.table.update().where(Feed.lastModified==None).values(lastModified=datetime.datetime(1970,1,1)).execute()

  # And this doesn'twork, either
  # for feed in Feed.query():
  #   if not feed.lastModified:
  #     feed.lastModified=datetime.datetime(1970,1,1)

  from urssus import database
  from sqlite3 import dbapi2 as sqlite
  
  con = sqlite.connect(database.dbfile)
  cur=con.cursor()
  cur.execute("""UPDATE feeds SET "last-modified"='1970-01-01 00:00:00.0' WHERE "last-modified" IS NULL """)
  con.commit()
