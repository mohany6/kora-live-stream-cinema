# -*- coding: utf-8 -*-
import re

with open("data/fetched_blogger.html", "r", encoding="utf-8") as f:
    html = f.read()

scripts = re.findall(r'<script([^>]*)>(.*?)</script>', html, re.DOTALL)
s12_attrs, s12_body = scripts[11] # index 11 is script #12

with open("data/script_12.js", "w", encoding="utf-8") as f:
    f.write(s12_body)

print("Saved script 12 (length: {}) to data/script_12.js".format(len(s12_body)))
