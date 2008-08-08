'''An attempt at a setup.py that can be used with py2exe on windows. It's
not even close to working, though'''

from py2exe.build_exe import py2exe
from distutils.core import setup


setup(windows=['urssus.py'],
      options={
                "py2exe":{
                        "includes": ["elixir","sip"],                        
                }
        }
)
