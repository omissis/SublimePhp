import sublime, sublime_plugin
import os

from .sublime_php_library import *

from pprint import pprint
from inspect import getmembers

class SublimePhpImportNamespaceCommand(sublime_plugin.TextCommand):
    _cache_path = os.path.join(sublime.cache_path(), 'SublimePhp')

    def run(self, edit):
        if not os.path.exists(self._cache_path):
            os.makedirs(self._cache_path)

        if not is_php_file(self.view):
            return

        index_manager = IndexManager(self._cache_path + os.sep + 'namespaces.index.json')

        index = index_manager.load()

        if None == index:
            file_repository = FilesRepository(sublime.active_window().folders())
            fs_fqdn_repository = FilesystemFqdnRepository()
            filenames = file_repository.find_by_extensions('php')
            fqdns = fs_fqdn_repository.find_by_filenames(filenames)
            index = FqdnIndex.create_from_set(fqdns)
            index_manager.dump(index)

        view_fqdn_repository = ViewFqdnRepository(self.view)

        for sel in self.view.sel():
            word_sel = self.view.word(sel)
            symbol = self.view.substr(word_sel)

            if '' == symbol:
                continue

            fqdn = index.get(symbol)

            if None == fqdn:
                continue

            region_repository = ViewRegionRepository(self.view)
            region = region_repository.find_region_for_namespace(fqdn)

            view_fqdns = view_fqdn_repository.find_by_namespace(fqdn)

            if len(view_fqdns) > 0:
                continue

            command = InsertNamespaceCommand(self.view, edit, region, fqdn)
            command.execute()
