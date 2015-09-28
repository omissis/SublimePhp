import sublime, sublime_plugin
import shutil
import os

from .sublime_php_library import *

SETTINGS = sublime.load_settings('SublimePHP.sublime-settings')
STORAGE = SublimePhpMemoryStorage()

class SublimePhpPurgeCacheDirectoryCommand(sublime_plugin.WindowCommand):
    def run(self):
        cache_path = os.path.join(sublime.cache_path(), 'SublimePhp')

        shutil.rmtree(cache_path)

class SublimePhpImportNamespaceCommand(sublime_plugin.TextCommand):
    _fqdns = []

    def run(self, edit):
        if not is_php_file(self.view):
            return

        if None == STORAGE.index:
            self.view.run_command("sublime_php_index_fqdns")

        for sel in self.view.sel():
            word_sel = self.view.word(sel)
            symbol = self.view.substr(word_sel)

            if '' == symbol:
                continue

            self._fqdns = STORAGE.index.get(symbol)

            if None == self._fqdns:
                continue

            if (1 == len(self._fqdns)):
                self.view.run_command("sublime_php_insert_namespace", {"fqdn": self._fqdns.pop()})
                continue

            sublime.active_window().show_quick_panel(self._fqdns, self._on_fqdn_chosen)

            return

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
        file_repository = FilesRepository(
            sublime.active_window().folders(),
            SETTINGS.get('folders_to_exclude'),
            SETTINGS.get('file_extensions_to_include')
        )
        fs_fqdn_repository = FilesystemFqdnRepository()
        filenames = file_repository.find_php_files()

        fqdns = fs_fqdn_repository.find_by_filenames(filenames)
        STORAGE.index = FqdnIndex.create_from_set(fqdns)

        STORAGE.dump_index()
