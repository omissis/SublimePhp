import sublime, sublime_plugin
import os

from .sublime_php_library import *

from pprint import pprint
from inspect import getmembers

SETTINGS = sublime.load_settings('SublimePHP.sublime-settings')

class SublimePhpImportNamespaceCommand(sublime_plugin.TextCommand):
    _fqdns = []
    _index = {}
    _cache_path = None
    _index_manager = None

    def run(self, edit):
        if not is_php_file(self.view):
            return

        self._cache_path = os.path.join(sublime.cache_path(), 'SublimePhp')

        if not os.path.exists(self._cache_path):
            os.makedirs(self._cache_path)

        self._index_manager = IndexManager(FqdnIndex.get_path_for_current_project(self._cache_path))
        self._index = self._index_manager.load()

        if None == self._index:
            self.view.run_command("sublime_php_index_fqdns")
            self._index = self._index_manager.load()

        for sel in self.view.sel():
            word_sel = self.view.word(sel)
            symbol = self.view.substr(word_sel)

            if '' == symbol:
                continue

            self._fqdns = self._index.get(symbol)

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
        cache_path = os.path.join(sublime.cache_path(), 'SublimePhp')
        file_repository = FilesRepository(
            sublime.active_window().folders(),
            SETTINGS.get('folders_to_exclude'),
            SETTINGS.get('file_extensions_to_include')
        )
        fs_fqdn_repository = FilesystemFqdnRepository()
        filenames = file_repository.find_php_files()

        fqdns = fs_fqdn_repository.find_by_filenames(filenames)
        index = FqdnIndex.create_from_set(fqdns)
        pprint(FqdnIndex.get_path_for_current_project(cache_path))

        index_manager = IndexManager(FqdnIndex.get_path_for_current_project(cache_path))
        index_manager.dump(index)
