#!/usr/bin/env python3

import os

def generate_listing(directory, supported_types, ignore_list):
    html = "<h1>Directory Listing</h1>\n<ul>\n"
    for item in sorted(os.listdir(directory)):
        if item in ignore_list:  # Ignore items in the ignore list
            continue
        item_path = os.path.join(directory, item)
        if os.path.isfile(item_path) and any(item.endswith(ext) for ext in supported_types):  # Check supported file types
            html += f"<li><a href='{item}'>{item}</a></li>\n"
        elif os.path.isdir(item_path):
            html += f"<li><a href='{item}/'>{item}/</a></li>\n"
    html += "</ul>"

    with open(os.path.join(directory, "index.html"), "w") as f:
        f.write(html)

if __name__ == "__main__":
    supported_types = [".html"]
    ignore_list = ["index.html"]
    generate_listing("examples", supported_types, ignore_list)