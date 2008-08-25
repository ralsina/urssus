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

import elixir,datetime

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

class Feed(elixir.Entity):
  elixir.using_options (tablename='feeds', inheritance='multi')
  htmlUrl        = elixir.Field(elixir.Text)
  xmlUrl         = elixir.Field(elixir.Text)
  title          = elixir.Field(elixir.Text)
  text           = elixir.Field(elixir.Text, default='')
  description    = elixir.Field(elixir.Text)
  children       = elixir.OneToMany('Feed', inverse='parent', order_by='position', cascade="delete")
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

class MetaFeed(Feed):
  elixir.using_options (tablename='metafeeds', inheritance='multi')
  condition   = elixir.Field(elixir.Text)

class MetaFolder(Feed):
  elixir.using_options (tablename='metafolders', inheritance='multi')
  condition   = elixir.Field(elixir.Text)

elixir.setup_all()
metadata=elixir.metadata
