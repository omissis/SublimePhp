import sublime
import glob
import json
import os
import re
import hashlib

from pprint import pprint
from inspect import getmembers

# global functions

def is_php_file(view):
    return view.file_name().endswith('.php')

# namespace SourceCode

# manages the queries for fqdns inside sublime.View objects
class ViewFqdnRepository:
    def __init__(self, view):
        self._view = view

    def find_by_namespace(self, namespace):
        fqdns = []
        regions = self._view.find_all('(use\s)?\s*' + namespace.replace('\\', '\\\\'), 0)

        for region in regions:
            fqdns.append(self._view.substr(self._view.line(region)))

        return fqdns

# manages the queries for fqdns inside filesystem objects such as lists of files
class FilesystemFqdnRepository:
    _namespace_regex = 'namespace\s+([A-z][A-z0-9\\\\]*)?'
    _interface_regex = 'interface\s+([A-z][A-z0-9\\\\]*)?'
    _class_regex = 'class\s+([A-z][A-z0-9\\\\]*)?'
    _namespace_separator = '\\'
    _current_namespace = ''
    _is_comment_line = False
    _last_errors = []

    # finds all fqdns within the given list of files' contents
    def find_by_filenames(self, filenames):
        fqdns = set()
        fqdn = None

        self._last_errors = []

        for filename in filenames:
            try:
                with open(filename, 'r') as php_file:
                    for line in php_file:
                        if '/*' in line:
                            self._is_comment_line = True
                        if '*/' in line:
                            self._is_comment_line = False
                        if '//' in line:
                            continue
                        if self._is_comment_line:
                            continue
                        if '$namespace' in line or '$class' in line or '$interface' in line:
                            continue
                        if 'namespace ' in line or 'namespace\t' in line:
                            self._current_namespace = self._extract_namespace(line)
                        if 'class ' in line or 'class\t' in line:
                            current_class = self._extract_class(line)
                            fqdn = self._format_fqdn(current_class)
                        if 'interface ' in line or 'interface\t' in line:
                            current_interface = self._extract_interface(line)
                            fqdn = self._format_fqdn(current_interface)
                        if (bool(fqdn)):
                            fqdns.add(fqdn)
            except UnicodeDecodeError as ude:
                self._last_errors.append("Cannot parse namespace.\n File:" + filename + "\n\n")
            except TypeError as te:
                self._last_errors.append("Cannot parse namespace.\n File: " + filename + "\nLine: \n\n" + line + "\n\n")

        return fqdns

    def get_last_errors(self):
        return self._last_errors

    def _format_fqdn(self, construct_name):
        return self._current_namespace + self._namespace_separator + construct_name

    def _extract_namespace(self, line):
        ns = re.search(self._namespace_regex, line)

        if (not bool(ns)):
            message = "Cannot find namespace in this line. This is probably a bug, please send a report. Line: \n\n" + line + "\n\n"
            raise Exception(message)

        if (None == ns.group(1)):
            return ''

        return ns.group(1)

    def _extract_class(self, line):
        ns = re.search(self._class_regex, line)

        if (not bool(ns)):
            message = "Cannot find class in this line. This is probably a bug, please send a report. Line: \n\n" + line + "\n\n"
            raise Exception(message)

        return ns.group(1)

    def _extract_interface(self, line):
        ns = re.search(self._interface_regex, line)

        if (not bool(ns)):
            message = "Cannot find interface in this line. This is probably a bug, please send a report. Line: \n\n" + line + "\n\n"
            raise Exception(message)

        return ns.group(1)


# namspace SourceCode.Index

# builds and holds an index of fqdns in a given codebase
class FqdnIndex(object):
    _index = {}

    def __init__(self, fqdns):
        self._index = fqdns

    @staticmethod
    def get_path_for_current_project(base_path):
        m = hashlib.md5()

        m.update(','.join(sublime.active_window().folders()).encode('utf-8'))

        return base_path + os.sep + m.hexdigest() + '.namespaces.index.json'


    @classmethod
    def create_from_dict(klass, fqdns):
        return klass(fqdns)

    @classmethod
    def create_from_set(klass, fqdns):
        index = {}

        for fqdn in fqdns:
            parts = fqdn.split('\\');

            for part in parts:
                if part == '':
                    continue

                if part not in index:
                    index[part] = {}

                if fqdn not in index[part]:
                    index[part][fqdn] = None

        return klass(index)

    def get(self, symbol):
        if symbol in self._index:
            return list(self._index[symbol].keys())

        return None

    def all(self):
        return self._index

# manages the dump and load of the namespaces index to and from the fs
class IndexManager:
    def __init__(self, storage_path):
        self._storage_path = storage_path

    def dump(self, index):
        with open(self._storage_path, 'w+') as fp:
            json.dump(index.all(), fp)

    def load(self):
        if not os.path.isfile(self._storage_path):
            return None

        index_file = open(self._storage_path, 'r+')
        index_json_str = index_file.read()
        index_dict = json.loads(index_json_str)

        return FqdnIndex.create_from_dict(index_dict)


# namespace Filesystem

# manages the searches for files in the filesystem
class FilesRepository:
    def __init__(self, folders, folders_to_exclude, file_extensions_to_include):
        self._folders = folders
        self._folders_to_exclude = folders_to_exclude
        self._file_extensions_to_include = file_extensions_to_include

    def find_php_files(self):
        results = []

        for folder in self._folders:
            for dirpath, dirnames, files in os.walk(folder):
                for i, dirname in enumerate(dirnames):
                    if self._should_skip_folder(dirname):
                        continue
                for j, filename in enumerate(files):
                    if self._should_skip_file(filename):
                        continue
                    results.append(dirpath + os.sep + filename)

        return results

    def _should_skip_folder(self, foldername):
        for _folder in self._folders_to_exclude:
            if foldername.find(_folder):
                return True

        return False

    def _should_skip_file(self, filename):
        for _file in self._file_extensions_to_include:
            if filename.endswith(_file):
                return False

        return True


# namespace View.Region

# manages the searches of sublime.Region objects inside sublime.View objects
class ViewRegionRepository:
    _use_namespace_regex = '^\s*(use\s+)?([A-z\\\\][A-z0-9\\\\]+)?\s*(\s+?as\s+[A-z][A-z0-9]+)?\s*([,;])'

    def __init__(self, view):
        self.view = view

    # finds the appropriate region for inserting the given namespace
    def find_region_for_namespace(self, namespace):
        region = None
        regions = self.view.find_all(self._use_namespace_regex, 0)

        # find the first usage of "class" so to make sure the insertion region
        # doesn't fall after it due to, for example, some comments
        class_region = self.view.find("class ", 0)

        if len(regions) > 0:
            for r in regions:
                # Extract the pure namespace from the use statement
                ns = re.search(self._use_namespace_regex, self.view.substr(self.view.line(r)))

                # If no matches are found, continue
                if (not bool(ns)):
                    continue

                # Save the region as the current if the current is alphabetically bigger than the previous
                # and if it's not after the class declaration (remember also Traits use the "use" keyword).
                if (namespace > ns.group(2) and ns.group(4) != "," and r.end() < class_region.begin()):
                    region = r
                    continue

                break

        if region is None:
            region = self.view.find("namespace (.*);\n", 0)

        if region is None:
            region = self.view.find('<\?php', 0)

        if region is None:
            raise RuntimeError('Cannot find the opening php tag nor a namespace declaration. Is this a php file?')

        return region


# namespace Command

# holds all the information needed to insert a new use statement for a namespace in the right place
class InsertNamespaceCommand:
    def __init__(self, view, edit, region, namespace):
        self._view = view
        self._edit = edit
        self._region = region
        self._namespace = namespace

    def execute(self):
        indentation = self._calculate_indentation();
        carriage_return = self._calculate_carriage_return();

        full_namespace = indentation + "use " + self._namespace + ";" + carriage_return

        self._view.insert(self._edit, self._region.end() + 1, full_namespace)

    def _calculate_indentation(self):
        previous_region = self._view.substr(self._view.line(self._region))

        indentation = re.search('^\s*', previous_region)

        return indentation.group(0)

    def _calculate_carriage_return(self):
        namespace_region = self._view.line(self._view.find('namespace ', 0));
        class_region = self._view.line(self._view.find('class ', 0));
        intermediate_region = sublime.Region(namespace_region.end(), class_region.begin())

        if ("\n\n" == self._view.substr(intermediate_region)):
            return "\n\n"

        return "\n"
