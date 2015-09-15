import os
import re

from pprint import pprint

def is_php_file(view):
    return view.file_name().endswith('.php')

def namespace_insert(view, edit, namespace):
    if '' == namespace:
        return

    full_namespace = "use " + namespace + ";\n"
    region = _find_namespace_region(view, namespace)

    new_region = view.full_line(region)
    view.insert(edit, region.end() + 1, full_namespace)

    return

def _find_namespace_region(view, namespace):
    region = None
    regions = view.find_all("use (.*);", 0)

    if len(regions) > 0:
        for r in regions:
            # Extract the pure namespace from the use statement
            ns = re.search('^\s*use\s+([A-z\\\\][A-z0-9\\\\]+)?\s*\;', view.substr(view.line(r)))

            if (namespace > ns.group(1)):
                region = r
                continue
            break

    if region is None:
        region = view.find("namespace (.*);\n", 0)

    if region is None:
        region = view.find('<\?php', 0)

    if region is None:
        raise RuntimeError('Cannot find the opening php tag nor a namespace declaration. Is this a php file?')

    return region
