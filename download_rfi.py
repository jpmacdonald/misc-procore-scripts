from operator import itemgetter
from itertools import groupby
import fitz
import requests
import pathlib
import pickle

doc = fitz.open("rfi_master.pdf")
data = {}
with open('rfi_data.pickle', 'rb') as handle:
    data = pickle.load(handle)

links = []

for page in doc:
    words = page.getTextWords()
    for link in page.links():
        rect = link['from']
        uri = link['uri']
        page.addHighlightAnnot(rect)
        mywords = [w for w in words if fitz.Rect(w[:4]) in rect]
        mywords.sort(key=itemgetter(3, 0))
        group = groupby(mywords, key=itemgetter(3))
        for y1, gwords in group:
            filename = " ".join(w[4] for w in gwords)
            links.append((filename, uri))

for item in links:
    filename = item[0]
    url = item[1]
    r = requests.get(url, allow_redirects=True)
    pathlib.Path('temp').mkdir(parents=True, exist_ok=True)
    if data.get(filename) != None:
        open('temp/' + "RFI-" + data[filename] +
             " " + filename, 'wb').write(r.content)
    else:
        open('temp/' + filename, 'wb').write(r.content)

doc.save("new_rfi_master.pdf")



