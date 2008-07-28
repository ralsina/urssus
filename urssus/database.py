import migrate.versioning.api as migrate
improt config

dbUrl="sqlite:///%s/urssus.sqlite"%config.cfdir
repo=os.path.join(os.path.abspath(os.path.dirname(__file__)), 'db_versioning')

def startVersioning():
  '''Puts the DB under migrate versioning control'''
  migrate.version_control (dbUrl, repo, version=1 )
  

def checkUpdate():
  '''See if the DB needs updating'''
