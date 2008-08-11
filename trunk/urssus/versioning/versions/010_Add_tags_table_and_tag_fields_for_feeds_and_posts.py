from sqlalchemy import *
from elixir import *
from datetime import datetime
from migrate import *
from migrate.changeset import schema
metadata.bind='sqlite:///sample.db'
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
  tags           = ManyToMany('Tag')

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
  tags        = ManyToMany('Tag')


class Tag(Entity):
  using_options (tablename='tags',metadata=meta)
  name        = Field(Text,unique=True)
  feeds       = ManyToMany('Feed', inverse='tags')
  posts       = ManyToMany('Post', inverse='tags')

setup_all()

def upgrade():
  Tag.table.create()

  # And as usual, I can't get migrate to do what I really want, so...

  from urssus import database
  from sqlite3 import dbapi2 as sqlite

  con = sqlite.connect(database.dbfile)
  cur=con.cursor()
  cur.execute("""
  CREATE TABLE tags_feeds__feeds_tags (
        feeds_id INTEGER NOT NULL,
        tags_id INTEGER NOT NULL,
        PRIMARY KEY (feeds_id, tags_id),
         CONSTRAINT tags_feeds_fk FOREIGN KEY(tags_id) REFERENCES tags (id),
         CONSTRAINT feeds_tags_fk FOREIGN KEY(feeds_id) REFERENCES feeds (id)
  )""")
  cur.execute("""
  CREATE TABLE tags_posts__posts_tags (
        posts_id INTEGER NOT NULL,
        tags_id INTEGER NOT NULL,
        PRIMARY KEY (posts_id, tags_id),
         CONSTRAINT posts_tags_fk FOREIGN KEY(posts_id) REFERENCES posts (id),
         CONSTRAINT tags_posts_fk FOREIGN KEY(tags_id) REFERENCES tags (id)
  );
  """)
  con.commit()

