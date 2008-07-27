import os

options(
    setup=Bunch(
        name="uRSSus",
        packages=['urssus', 'urssus.ui', 'urssus.templates'],
        version="0.0.1",
        author="Roberto Alsina", 
        package_data = {'urssus.templates': ['*.tmpl']}, 
        entry_points = {
                        'gui_scripts': ['urssus = urssus.urssus:main']
        }
    )
)

@task
@needs(['compile_resource','compile_ui','generate_setup', 'minilib', 'setuptools.command.sdist'])
def sdist():
  """Overrides sdist to make sure that our setup.py is generated."""
  pass
  
  
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
