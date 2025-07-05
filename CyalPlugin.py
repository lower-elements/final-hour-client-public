import glob
from pathlib import Path
import shutil

from nuitka.plugins.PluginBase import NuitkaPluginBase


def get_libraries(module):
    """Returns a  list of the libraries needed by cyal"""
    cyal_dir = module.getCompileTimeDirectory()
    return list(glob.glob(f'{cyal_dir}/*.dll'))

class cyalPlugin(NuitkaPluginBase):
    plugin_name = "cyal"
    plugin_desc = "provides cyal support"
    
    def __init__(self):
        self.copied_cyal = False    

    def considerExtraDlls(self, dist_dir, module):
        libs = get_libraries(module)
        name = module.getFullName()
        # to avoid copying files twice
        if self.copied_cyal == False and name == "cyal":
            for lib in libs:
                shutil.copy(lib, str(Path(dist_dir)))
                self.info(f'copied {lib}')
            self.copied_cyal = True
        return ()

