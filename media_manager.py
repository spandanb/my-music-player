from __future__ import print_function
"""
Interface for finding all the files and whatnot.
"""

import json
import os
import pdb
from id3parser import ID3Parser 
import pickle as pickle    

class MediaManager(object):
    """
    Manager for interfacing with media
    """
    def __init__(self, configfile='./config.json'):
        with open(configfile) as cfile:
            self.config = json.load(cfile)
        
        self.id3_parser = ID3Parser()
        self.archive_fpath = os.path.abspath(os.path.join(self.config['data_dir'], 'MYMEDIA.pickle'))

    def crawl(self, rootpath):
        """
        Crawls starting at `rootpath` and returns a list of all mp3 files
        """
        os.chdir(rootpath)
        music = []
        for dirpath, subdirs, files in os.walk('.'):
            for child in files:
                if child[-3:] == 'mp3':
                    abspath = os.path.join(self.config['root'], dirpath, child) 
                    metadata = self.id3_parser.get_human_readable(abspath)
                    music.append({'filename': child, 'filepath': abspath, 'metadata': metadata})
        return music

    def get_media(self):
        """
        Returns a list of all music files
        Caches the crawled data
        """

        #Check if pickled version exists
        if os.path.exists(self.archive_fpath):
            with open(self.archive_fpath, 'rb') as f:
                return pickle.load(f)
        
        #else crawl 
        music = self.crawl(self.config['root'])
        with open(self.archive_fpath, 'wb') as f:
            pickle.dump(music, f, pickle.HIGHEST_PROTOCOL)
        return music    


if __name__ == "__main__":
    mmanager = MediaManager()
    #id3 = ID3Parser()
    #print(id3.get_human_readable(mmanager.config['sample_file']))
