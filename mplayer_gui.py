#!/usr/bin/env python
"""

"""
from __future__ import unicode_literals

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.interface import CommandLineInterface
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout.containers import VSplit, HSplit, Window, FloatContainer, Float
from prompt_toolkit.layout.controls import BufferControl, FillControl, TokenListControl
from prompt_toolkit.layout.dimension import LayoutDimension as D
from prompt_toolkit.shortcuts import create_eventloop
from prompt_toolkit.token import Token
from prompt_toolkit.filters.base import Filter
from prompt_toolkit.cache import memoized
from prompt_toolkit.contrib.completers import WordCompleter
from prompt_toolkit.layout.menus import CompletionsMenu

from media_manager import MediaManager

def dbg(*msg):
    """
    helper method that writes prints to file
    """
    with open('dbg.foo', 'a') as dfile:
        dfile.write(str(msg) + '\n')
        
###################################################
#Filters for the different modes
###################################################
#See: https://github.com/jonathanslenders/python-prompt-toolkit/blob/master/prompt_toolkit/filters/cli.py
#TODO: @memoized #causes an assertion error
class CommandMode(Filter):
    def __call__(self, cli):
        return cli.mode == 'command'

    def __repr__(self):
        return 'CommandMode()'


class PlaylistMode(Filter):
    def __call__(self, cli):
        return cli.mode == 'playlist'

    def __repr__(self):
        return 'PlaylistMode()'
    
    
class InteractMode(Filter):
    def __call__(self, cli):
        return cli.mode == 'interact'

    def __repr__(self):
        return 'InteractMode()'



    

class MediaFiles(object):
    """
    Adaptor for interfacing with music files 
    """
    def __init__(self, dummy=False):
        if dummy:
            self.media_list = ["Song {}".format(i) for i in range(100)]
        else:
            self.media_manager = MediaManager()
            self.media_list = [ media['metadata']['name'] for media in self.media_manager.get_media()]
        self.document = Document(
            ''.join(["{}\n".format(m) for m in self.media_list]))
               
    def as_document(self):
        return self.document
        

class BufferManager(object):
    """
    Manages buffers
    """
    def  __init__(self):
        self.media_files = MediaFiles()
        self.buffers = {
            DEFAULT_BUFFER: Buffer(is_multiline=True,
                                   completer=self.get_completer(),
                                    complete_while_typing=True),

            'LIBRARY': Buffer(is_multiline=True,
                              read_only=True,
                              initial_document=self.media_files.as_document()),
            
            'COMMAND': Buffer(),
        }
        self.buffer_list = [DEFAULT_BUFFER, 'LIBRARY', 'COMMAND']
    
    def next(self, curr):
        """
        Given name of current buffer, returns name of the next buffer
        """
        return self.buffer_list[(self.buffer_list.index(curr) + 1) %
            len(self.buffer_list)]
    
    def prev(self, curr):
        """
        Returns next buffer
        """
        return self.buffer_list[(self.buffer_list.index(curr) - 1) %
            len(self.buffer_list)]
    
    def get_completer(self):
        if not hasattr(self, 'completer'):
            self.completer = WordCompleter(self.media_files.media_list, ignore_case=True)
        return self.completer
    
class MusicPlayer(object):
    def __init__(self):
        self.buffers = BufferManager()
        self.registry = load_key_bindings()
        self.create_key_bindings()
        self.create_application()
        self.run_application()        
        

    def get_layout(self):
        """
        Create the layout
        """
        
        autosuggestion = Float(xcursor=True,
                               ycursor=True,
                               content=CompletionsMenu(
                                    max_height=5,
                                    scroll_offset=1                                    
                                ))
    
        inner = VSplit([
            # One window that holds the BufferControl with the default buffer
            # (playlist buffer) on the left.
            #See: https://github.com/jonathanslenders/python-prompt-toolkit/blob/master/prompt_toolkit/shortcuts.py#L334    
            FloatContainer(content=Window(content=BufferControl(buffer_name=DEFAULT_BUFFER)),
                           floats=[autosuggestion]),
        
            # A vertical line in the middle. We explicitely specify the width
            Window(width=D.exact(1),
                   content=FillControl('|', token=Token.Line)),
        
            Window(content=BufferControl(buffer_name='LIBRARY')),
        ])
    
    
        #This is the main UI Block
        return HSplit([
            # The titlebar.
            Window(height=D.exact(1),
                   content=TokenListControl(lambda cli: [(Token.Title, 'Music Player')], align_center=True)),    
        
            # Horizontal separator.
            Window(height=D.exact(1),
                   content=FillControl('-', token=Token.Line)),
        
            # The 'body'- defined above.
            inner,
            
            # Separator
            Window(height=D.exact(1),
                   content=FillControl('-', token=Token.Line)),
            
            # Command Prompt
            Window(content=BufferControl(buffer_name='COMMAND')),
        ])
    
    def create_key_bindings(self):
        """
        To handle multiple modes, put filter on key bindings
        See: https://github.com/jonathanslenders/python-prompt-toolkit/blob/master/prompt_toolkit/key_binding/bindings/vi.py (LINE 370)
        
        List of named keys: https://github.com/jonathanslenders/python-prompt-toolkit/blob/master/prompt_toolkit/keys.py
        """
        
        command_mode = CommandMode()
        playlist_mode = PlaylistMode()
        interact_mode = InteractMode()
        
        handle = self.registry.add_binding
        
        #UNIVERSALS BINDINGS
        @handle(Keys.ControlC, eager=True)
        @handle(Keys.ControlQ, eager=True)
        def _exit(event):
            """
            Pressing Ctrl-Q or Ctrl-C will exit the user interface.        
            """
            event.cli.set_return_value(None)
        
        @handle(Keys.Escape, eager=True)
        def _enter_command_mode(event):
            """
            Escape always takes us to Command Mode
            """
            event.cli.mode = 'command'
            
        
        #COMMAND-MODE BINDINGS    
        @handle(Keys.Right, filter=command_mode)    
        def _move_clockwise(event):
            #NOTE: current_buffer may be undefined
            cli = event.cli
            cli.focus(self.buffers.next(cli.current_buffer_name))
            
        @handle(Keys.Left, filter=command_mode)    
        def _move_counter_clockwise(event):
            cli = event.cli
            cli.focus(self.buffers.prev(cli.current_buffer_name))    

        @handle('i', filter=command_mode)    
        def _enter_interact_mode(event):
            cli = event.cli
            event.cli.mode = 'interact'
            
        @handle('p', filter=command_mode)    
        def _enter_playlist_mode(event):
            cli = event.cli
            event.cli.mode = 'playlist'
        
        @handle(Keys.Any, filter=command_mode)    
        def _ignore_all_else(event):
            """
            Other than the bindings defined above, ignore
            everything else
            """
            pass
        
        
        #INTERACT-MODE BINDINGS
        
        
        #PLAYLIST-MODE BINDINGS    
        @handle(Keys.Enter, filter=playlist_mode)    
        def _add_to_playlist(event):
            cli = event.cli
            #Add this to Playlist Buffer
            if cli.current_buffer_name == 'LIBRARY':                                
                #https://github.com/jonathanslenders/python-prompt-toolkit/blob/master/prompt_toolkit/buffer.py#L536
                #get the current doc
                document = cli.current_buffer.document 
                a = document.cursor_position + document.get_start_of_line_position()
                b = document.cursor_position + document.get_end_of_line_position()
                #string representing the current line
                musicfile = document.text[a:b] 
                self.buffers.buffers[DEFAULT_BUFFER].text +=  musicfile + '\n'
                
                
        
        

    def create_application(self):
        """
        Creates the application instance
        """
        self.application = Application(
            layout=self.get_layout(),
            buffers=self.buffers.buffers,
            key_bindings_registry=self.registry,
            mouse_support=True,
            use_alternate_screen=True)

    def run_application(self):
        "Runs the application"
        eventloop = create_eventloop()
    
        try:
            cli = CommandLineInterface(application=self.application, eventloop=eventloop)
            #Check if there is a better way to do this
            cli.mode = 'command' 
            cli.run()        
        finally:
            eventloop.close()



if __name__ == '__main__':
    mplayer = MusicPlayer()
    
