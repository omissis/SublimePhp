import sublime, sublime_plugin
import os

from .sublime_php_library import *

from pprint import pprint
from inspect import getmembers

class SublimePhpImportNamespaceCommand(sublime_plugin.TextCommand):
    _cache_path = os.path.join(sublime.cache_path(), 'SublimePhp')

    def run(self, edit):
        if not is_php_file(self.view):
            return

        sels = self.view.sel()

        for sel in sels:
            word_sel = self.view.word(sel)
            namespace = self.view.substr(word_sel)

            if '' == namespace:
                continue

            region_repository = ViewRegionRepository(self.view)
            region = region_repository.find_by_namespace(namespace)

            command = InsertNamespaceCommand(self.view, edit, region, namespace)
            command.execute()
