import contextlib
import cyal.exceptions

class Sound:
    def __init__(self, source, volume, dist=False, cat="miscelaneous"):
        self._source = source
        self.volume=volume
        self.cat=cat
        self.dist = dist
        self.muted = False
        self.force_to_destroy = False
        
    def destroy(self, force=False):
        if self.force_to_destroy and not force: return
        with contextlib.suppress(cyal.exceptions.InvalidAlValueError):
            if self.source is not None: 
                try: self._source.stop()
                except cyal.exceptions.InvalidOperationError: pass
                del self.source
        del self
        
    
    @property
    def source(self):
        return self._source
    
    @source.setter
    def source(self, value):
        self._source = value
    
    @source.deleter
    def source(self):
        del self._source
        self._source = None
        