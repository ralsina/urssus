from urssus import database

def upgrade():
  '''Ugly but I can't figure out a way to do it with migrate'''
  from sqlite3 import dbapi2 as sqlite

  con = sqlite.connect(database.dbfile)
  cur=con.cursor()
  cur.execute('ALTER TABLE feeds ADD COLUMN row_type VARCHAR(40)') 
    
def downgrade():
  '''Can't do it in sqlite'''
