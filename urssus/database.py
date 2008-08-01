import os, sys
import migrate.versioning.api as migrate
import config, sqlalchemy
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
  setLogger(name='urssus', level=DEBUG)

dbfile=os.path.join(config.cfdir, 'urssus.sqlite')
dbUrl="sqlite:///%s"%dbfile
repo=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'versioning')

def initDB():
  '''Creates the DB if it doesn't exists, 
     Puts the DB under migrate versioning control if needed,
     upgrades to latest schema if needed'''
  # See if the DB exists, or create
  info ("Initializing DB")
  if not os.path.exists(dbfile):
    info ("Starting on schema version 0")
    migrate.version_control (dbUrl, repo, version=0 )
  try:
    curVer=migrate.db_version(dbUrl, repo)
    info ("Currently on schema version %d", curVer)
  except sqlalchemy.exceptions.NoSuchTableError:
    info ("Starting on schema version 1")
    # Start at version 1 because this was created by a pre-migrate urssus
    migrate.version_control (dbUrl, repo, version=1 )
  migrate.upgrade(dbUrl, repo)
 
def main():
  initDB()

if __name__ == "__main__":
  main()
