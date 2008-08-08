import os

options(
    setup=Bunch(
        name="uRSSus",
        packages=['urssus', 
          'urssus.ui', 
          'urssus.util',
          'urssus.templates', 
          'urssus.versioning', 
          'urssus.versioning.versions', 
          'urssus.GoogleReader', 
          'urssus.GoogleReader.web', 
          'urssus.GoogleReader.web.resolvUrl', 
          ],
        version="0.2.10",
        author="Roberto Alsina",
        author_email='ralsina@netmanagers.com.ar',  
        package_data = {'urssus.templates': ['*.tmpl', '*.css', '*.js'],
                        'urssus.versioning': ['*.cfg'], 
                       }, 
        entry_points = {'gui_scripts': ['urssus = urssus.main:main'], 
                        'console_scripts': ['urssus_upgrade_db = urssus.database:main', 
                                            'urssus_client = urssus.client:main', 
                                            ], 
                        }, 
        install_requires = ['SQLAlchemy==0.4.6', 
                            'Elixir==0.5.2', 
                            'processing', 
                            'sqlalchemy-migrate', 
                            'simplejson'],
        extras_require = {'Twitter':  ["twitter"] }, 
        description = 'A multiplatform GUI news agregator.', 
        license = 'GPLv2', 
        keywords = 'atom rss pyqt', 
        url = 'http://urssus.googlecode.com', 
        long_description = '''
uRSSus is a multi-platform RSS/Atom news aggregtor, with a PyQt4 GUI. 
The code is hosted at http://urssus.googlecode.com and the license is GPL v2.0.

Hope you enjoy it, please use googlecode's issues_ page for bug reports, or mail me at
ralsina at netmanagers dot com dot ar.
        
.. _issues: http://code.google.com/p/urssus/issues/list
'''
    )
)

@task
@needs(['compile_resource','compile_ui','generate_setup', 'minilib', 'setuptools.command.sdist'])
def sdist():
  """Overrides sdist to make sure that our setup.py is generated."""
  pass

#@task
#@needs(['compile_resource','compile_ui', 'setuptools.command.install'])
#def install():
#  """Generate UI and icon resourcebefore installing."""
#  pass

  
uidir=os.path.join('urssus', 'ui')

@task
def compile_ui():
  '''Compile the .ui files using pyuic4'''
  for f in os.listdir(uidir):
    if f.endswith('.ui'):
      print "Compiling ", f
      os.system ('pyuic4 %s -o %s'%(os.path.join(uidir, f), os.path.join(uidir, 'Ui_%s.py'%f[:-3])))
      
@task
def compile_resource():
  '''Compile the icons/images resource file'''
  os.system ('pyrcc4 %s -o %s'%(os.path.join('urssus','images', 'icons.qrc'), os.path.join(uidir, 'icons_rc.py')))
