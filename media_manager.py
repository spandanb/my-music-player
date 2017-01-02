from __future__ import print_function
from __future__ import division
"""
Interface for finding all the files and whatnot.
"""

import json
import os
import pdb
import struct

class ParserException(Exception):
    pass
    

class HumanReadable(object):
    
    @classmethod
    def human_readable(cls, num, si=True):
        """
        Gives 
        """
        if si:
            K, M, G = 1024, 1048576, 1073741824
        else:
            K, M, G = 1000, 1000000, 1000000000

        if num < K:
            return '{}B'.format(num)
        elif num < M:
            return '{:.2f}KB'.format(num/K)
        elif num < G:
            return '{:.2f}MB'.format(num/M)
        else:
            return '{:.2f}GB'.format(num/G)

        return num

class ID3Parser(object):
    """
    Parses text information frames, since these are the most
    important.
    """
    def __init__(self):
        pass

    def header_flags(self, flagbyte):
        """
        Get the individual flags set in the header
        """
        unsync     = bool((flagbyte >> 7) & 0b1)
        extheader  = bool((flagbyte >> 6) & 0b1)
        expindic   = bool((flagbyte >> 5) & 0b1)
        footerpres = bool((flagbyte >> 4) & 0b1)

        return unsync, extheader, expindic, footerpres


    def get_size(self, byte_arr):
        """
        Decode the size value
        """
        return sum([b & 0x7F for b in byte_arr])
    

    def get_metadata(self, filepath):
        """
        Get the metadata of the file at `filepath`
        Returns a dict of ID3 frames IDs -> values

        References: 
        http://id3.org/id3v2.4.0-structure
        http://id3.org/id3v2.3.0#ID3v2_frame_overview
        """
        with open(filepath, "rb") as f:
            #ID3 Header
            #'ID3'
            if struct.unpack('3s', f.read(3))[0].decode('utf-8') != 'ID3':
                raise ParserException("Cannot parse non ID3v2 Tags") 

            #The major and minor version
            major_version, minor_version = struct.unpack('BB', f.read(2))
            version = "2.{}.{}".format(major_version, minor_version)

            #TODO: Different parsers based on version, e.g. 2.3 frame size = encoded value, 2.4 frame size = 4 * encoded value
            if major_version != 3:
                raise ParserException("Cannot parse version {}".format(version))

            #The flags
            flagbyte, = struct.unpack('B', f.read(1))
            #Extract the flags
            _, extheader, _, footerpres = self.header_flags(flagbyte)
  
            #Parse the extended header
            if extheader: 
                raise ParserException("Extended header parsing not implemented")

            #Tag size: Total number of bytes, includes padding, 
            #excludes header (but not extended header)
            tag_size = self.get_size(struct.unpack('BBBB', f.read(4)))

            bytes_read = 0
            fields = {}

            #Frames
            while bytes_read < tag_size: 

                #frame ID
                frame_id, = struct.unpack('4s', f.read(4))
                frame_id = frame_id.decode('utf-8')
                
                #frame size: excludes frame header (10B)
                frame_size = self.get_size(struct.unpack('BBBB', f.read(4)))
    
                #frame flags
                flag1, flag2 = struct.unpack('BB', f.read(2))
    
                frame_value, = struct.unpack('{}s'.format(frame_size), f.read(frame_size))
                bytes_read += 10 + frame_size

                #only parse text fields
                if frame_id[0] != 'T':
                    continue

                #FIXME: [1:] because there is a preceding \x00 byte
                frame_value = frame_value.decode('utf-8')[1:]
                fields[frame_id] = frame_value

            return fields


    def get_human_readable(self, filepath):
        """
        fields is a dict of ID3 frame identifiers -> values
        Returns a dict with the fields: name, artist, album, genre, time
        """
        #strip extension and path
        media_name = lambda fpath: os.path.splitext(os.path.basename(fpath))
        fields = self.get_metadata(filepath)

        human_readable = {}

        #The name
        name = []
        if 'TIT1' in fields: 
            name.append(fields['TIT1'])
        if 'TIT2' in fields: 
            name.append(fields['TIT2'])
        if 'TIT3' in fields: 
            name.append(fields['TIT3'])
        if not name: 
            name.append(media_name(filepath))
        human_readable['name'] = ' '.join(name)

        #The artist
        artist = []
        if 'TPE1' in fields:
            artist.append(fields['TPE1'])
        if 'TPE2' in fields and fields['TPE2'] not in artist:
            artist.append(fields['TPE2'])
        if 'TPE3' in fields and fields['TPE3'] not in artist:
            artist.append(fields['TPE3'])
        if 'TPE4' in fields and fields['TPE4'] not in artist:
            artist.append(fields['TPE4'])
        human_readable['artist'] = ' '.join(artist)

        #Album
        human_readable['album'] = fields.get('TALB', '')

        #Genre
        human_readable['genre'] = fields.get('TCON', '')

        #Time
        #TODO: fix this
        human_readable['time'] = '0'

        return human_readable
    

class MediaManager(object):
    """
    Manager for interfacing with media
    """
    def __init__(self, configfile='./config.json'):
        with open(configfile) as cfile:
            self.config = json.load(cfile)
        

    def get_media(self):
        """
        Returns a list of all music files
        TODO: 
         1) Keep track of directory
         2) Extract ID3 info
        """
        os.chdir(self.config['root'])
        music = []
        for dirpath, subdirs, files in os.walk('.'):
            for child in files:
                if child[-3:] == 'mp3':
                    music.append(child)
        return music

if __name__ == "__main__":
    mmanager = MediaManager()
    id3 = ID3Parser()
    print(id3.get_human_readable(mmanager.config['sample_file']))
    #mmanager.get_media()
