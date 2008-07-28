import os
import migrate.versioning.api as migrate
import config, sqlalchemy

dbfile=os.path.join(config.cfdir, 'urssus.sqlite')
dbUrl="sqlite:///%s"%dbfile
repo=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'versioning')

def initDB():
  '''Creates the DB if it doesn't exists, 
     Puts the DB under migrate versioning control if needed,
     upgrades to latest schema if needed'''
  # See if the DB exists, or create
  if not os.path.exists(dbfile):
    open(dbfile, 'w').close()
    migrate.version_control (dbUrl, repo, version=0 )
  try:
    curVer=migrate.db_version(dbUrl, repo)
  except sqlalchemy.exceptions.NoSuchTableError:
    # Start at version 1 because this was created by a pre-migrate urssus
    migrate.version_control (dbUrl, repo, version=1 )
  migrate.upgrade(dbUrl, repo)
  
  

def checkUpdate():
  '''See if the DB needs updating'''

def main():
  initDB()

if __name__ == "__main__":
  main()
