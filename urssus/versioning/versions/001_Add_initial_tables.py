from sqlalchemy import *
import migrate
from elixir import *
from datetime import datetime

meta = MetaData(migrate.migrate_engine)

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

class Feed(Entity):
  using_options (tablename='feeds', metadata=meta)
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

setup_all()

def upgrade():
  Feed.table.create()
  Post.table.create()

def downgrade():
  Post.table.drop()
  Feed.table.drop()
