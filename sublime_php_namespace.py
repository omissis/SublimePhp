import sublime, sublime_plugin
import os

from .sublime_php_library import *

from pprint import pprint
from inspect import getmembers

class SublimePhpConfig():
    file_extensions_to_include = ['.php']
    file_extensions_to_exclude = ['.', '..', '.git']
    cache_path = os.path.join(sublime.cache_path(), 'SublimePhp')

class SublimePhpImportNamespaceCommand(sublime_plugin.TextCommand):
    _fqdns = []

    def run(self, edit):
        if not os.path.exists(SublimePhpConfig.cache_path):
            os.makedirs(SublimePhpConfig.cache_path)

        if not is_php_file(self.view):
            return

        index_manager = IndexManager(get_index_path(SublimePhpConfig.cache_path))
        index = index_manager.load()

        if None == index:
            self.view.run_command("sublime_php_index_fqdns")
            index = index_manager.load()

        for sel in self.view.sel():
            word_sel = self.view.word(sel)
            symbol = self.view.substr(word_sel)

            if '' == symbol:
                continue

            self._fqdns = index.get(symbol)

            if None == self._fqdns:
                continue

            if (1 == len(self._fqdns)):
                self.view.run_command("sublime_php_insert_namespace", {"fqdn": self._fqdns.pop()})
                continue

            sublime.active_window().show_quick_panel(self._fqdns, self._on_fqdn_chosen)

    def _on_fqdn_chosen(self, chosen_fqdn_key):
        if (-1 == chosen_fqdn_key):
            return

        fqdn = self._fqdns[chosen_fqdn_key]

        self.view.run_command("sublime_php_insert_namespace", {"fqdn": fqdn})

class SublimePhpInsertNamespaceCommand(sublime_plugin.TextCommand):
    def run(self, edit, **args):
        fqdn = args.get('fqdn')

        if None == fqdn:
            return

        view_fqdn_repository = ViewFqdnRepository(self.view)
        region_repository = ViewRegionRepository(self.view)
        region = region_repository.find_region_for_namespace(fqdn)

        view_fqdns = view_fqdn_repository.find_by_namespace(fqdn)

        if len(view_fqdns) > 0:
            return

        command = InsertNamespaceCommand(self.view, edit, region, fqdn)
        command.execute()

class SublimePhpIndexFqdnsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        file_repository = FilesRepository(sublime.active_window().folders())
        fs_fqdn_repository = FilesystemFqdnRepository()
        filenames = file_repository.find_by_extensions(SublimePhpConfig.file_extensions_to_include)
        fqdns = fs_fqdn_repository.find_by_filenames(filenames)
        index = FqdnIndex.create_from_set(fqdns)

        index_manager = IndexManager(get_index_path(SublimePhpConfig.cache_path))
        index_manager.dump(index)

        return index
