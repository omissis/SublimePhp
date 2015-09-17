import sublime, sublime_plugin
import os
import re

from pprint import pprint
from inspect import getmembers

# global functions

def is_php_file(view):
    return view.file_name().endswith('.php')

# namespace View.Region

class ViewRegionRepository:
    def __init__(self, view):
        self.view = view
        self._use_namespace_regex = '^\s*use\s+([A-z\\\\][A-z0-9\\\\]+)?\s*(\s+?as\s+[A-z][A-z0-9]+)?\;'

    def find_by_namespace(self, namespace):
        region = None
        regions = self.view.find_all("use (.*);", 0)

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
                if (namespace > ns.group(1) and r.end() < class_region.begin()):
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
