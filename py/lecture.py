#!/usr/bin/env python3

import re
import os
import click
from sys import platform
import shutil
import urllib.parse
import urllib.request
import subprocess
import tempfile

USER_AGENT = "analogic-bot/1.0 (+https://github.com/openicdesign/analogIC)"


def _download_remote_asset(url):
    """
    Download a remote asset into the OS temp directory and return the local path.
    """
    tmp_dir = tempfile.gettempdir()
    os.makedirs(tmp_dir, exist_ok=True)
    parsed = urllib.parse.urlparse(url)
    local_name = urllib.parse.unquote(os.path.basename(parsed.path)) or "downloaded_asset"
    local_path = os.path.join(tmp_dir, local_name)
    if os.path.exists(local_path):
        return local_path
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req) as response, open(local_path, "wb") as outf:
            shutil.copyfileobj(response, outf)
    except Exception as exc:
        raise RuntimeError(f"Unable to download image {url}") from exc
    return local_path


class Image():

    def __init__(self,imgsrc,options):
        self.src = imgsrc
        self.orgsrc = imgsrc
        self.options = options
        self.directory = options["dir"]
        self.skip = False
        self.isUrl = False


        if("/ip/" in self.src and "allowIP" not in self.options):
            self.skip = True

        if(re.search(r"\s*https?://",self.src)):
            self.isUrl = True


        if(not self.skip and ".pdf" in self.src and "latex" not in self.options):
            #- I've changed to svg, hopefully better images
            svg = self.src.replace(".pdf",".svg")
            if(not os.path.exists(os.path.join(self.directory,svg))):
                cmd = f"cd {self.directory}; pdftocairo -svg {self.src} {svg}"
                os.system(cmd)
            self.src = svg

        if self.isUrl and "downloadImage" in self.options:
            try:
                self.src = _download_remote_asset(self.src)
            except RuntimeError as exc:
                print(f"{exc}. Marking image for manual follow-up.")
                self.skip = True
                self.skip_reason = str(exc)
                self.caption = options.get("caption", imgsrc)
                return


        self.filesrc = os.path.basename(self.src)
        self.dirsrc  = os.path.dirname(self.src)


    def copy(self):
        if(self.isUrl and not ("downloadImage" in self.options) ):
            return
            
        if(self.skip):
            return

        if("jekyll" in self.options):
            shutil.copyfile(os.path.join(self.options["dir"],self.src), "docs/assets/media/" + self.filesrc)
        elif("latex" in self.options):
            os.makedirs(self.options["latex"] + "media/",exist_ok=True)
            try:
                shutil.copyfile(os.path.join(self.options["dir"],self.src),  self.options["latex"] + "media/" + self.filesrc)
            except Exception as e:
                print(e)
    def __str__(self):

        if self.skip:
            reason = getattr(self, "skip_reason", "image skipped")
            return f"> WARNING: image '{self.orgsrc}' not included ({reason})\n"

        if("jekyll" in self.options):
            path = self.options["jekyll"] + "assets/media/" + self.filesrc

            return f"![]({path})" + "{: width=\"700\" }\n"
        elif("latex" in self.options):
            path = "media/" + self.filesrc
            return f"![]({path})\n\n"

        return self.src

class Lecture():
    
    def __init__(self,filename,options):
        self.filename = filename
        self.title = ""
        self.options = options
        self.date = None
        self.images = list()

        self.filters = {
            r"^\s*---\s*$" : "",
            r"\[.column\]" : "",
            r"\[\.background.*\]" : "",
            r"\[\.text.*\]" : "",
            r"\[\.table  *\]" : "",
            r"\#\s*\[\s*fit\s*\]" : "# ",
            r"\*\*Q:\*\*" : "",
            r"^[.table.*]$": "",
            r"#(.*) Thanks!" : ""
        }

        self._read()

    def copyAssets(self):
        with open("images.txt","a", encoding="utf-8") as fo:
            for image in self.images:
                if(not image.skip and not image.isUrl):
                    fo.write(image.orgsrc.strip() + "\n")
                    fo.write(image.src.strip() +"\n")
                image.copy()


    def _read(self):

        self.buffer = list()
        first = True
        self.output = False
        self.skipslide = False
        self.removeComment = False

        with open(self.filename, encoding="utf-8") as fi:
            for line in fi:

                if(first and "date:" in line):
                    (k,v) = line.split(" ")
                    self.date = v.strip()

                if(first and re.search(r"^\s*$",line)):
                    first = False
                    self.output = True


                line = self._readPan(line)

                if(line):
                    line = self._filterLine(line)
                    line = self._convertImage(line)


                if(line is not None and self.output):
                    self.buffer.append(line)



    def _readPan(self,line):

        #- Check pan tags
        m = re.search(r"<!--pan_([^:]+):(.*)$",line)
        if(m):
            key = m.groups()[0]
            val = m.groups()[1]


            if(key == "title"):
                self.title = val.replace("-->","")

            elif(key == "skip"):
                self.skipslide = True
                self.output = False

            elif(key == "doc"):
                 # Start statemachine
                # 1. Skip this line, it should be <!--pan_doc:
                # 2. Enable removing -->
                # 3. When -->, assume that's the end of the pan_doc, and go back to normal
                self.removeComment = True
            else:
                print(f"Uknown key {key}")

            return None

        #- Go back to normal mode
        if(self.removeComment and re.search(r"-->",line)):
            self.removeComment = False
            return None

        if(self.skipslide and re.search(r"^\s*---\s*$",line)):
            self.output = True
        return line

    def _convertImage(self,line):
        m = re.search(r"\!\[([^\]]*)\]\(([^\)]+)\)",line)

        if(m):
            imgsrc = m.groups()[1]

            if(not "downloadImage" in self.options):
                if(re.search(r"\s*https://",imgsrc)):
                    return f"![]({imgsrc})"

            i = Image(imgsrc,self.options)
            self.images.append(i)
            line = str(i)
        return line


    def _filterLine(self,line):
        for r,s in self.filters.items():
            line = re.sub(r,s,line)
        return line

    def __str__(self):

        ss = ""

        if("jekyll" in self.options):

            furl = "https://github.com/openicdesign/analogIC/tree/main/" + self.filename
            slides = ""
            if("lectures" in self.filename ):
                slides = "[Slides](" +  self.options["jekyll"] + self.filename.replace("lectures","assets/slides").replace(".md",".pdf") +")"

            ss += f"""---
layout: post
title: {self.title}
math: true
---

> If you find an error in what I've made, then [fork](https://docs.github.com/en/get-started/quickstart/fork-a-repo), fix [{self.filename}]({furl}), [commit](https://git-scm.com/docs/git-commit), [push](https://git-scm.com/docs/git-push) and [create a pull request](https://docs.github.com/en/desktop/contributing-and-collaborating-using-github-desktop/working-with-your-remote-repository-on-github-or-github-enterprise/creating-an-issue-or-pull-request). That way, we use the global brain power most efficiently, and avoid multiple humans spending time on discovering the same error.

{slides}


""" + """



* TOC
{:toc }

"""

        for l in self.buffer:
            ss += l
        return ss

class Presentation(Lecture):

    def __init__(self,filename,options):
        self.filename = filename
        self.title = filename.replace(".md","")
        self.options = options

        self.images = list()

        self.filters = {
            r"\[\.background.*\]" : "",
            r"\[\.text.*\]" : "",
            r"\[\.table  *\]" : "",
            r"\#\s*\[\s*fit\s*\]" : "## ",
            r"^[.table.*]$": "",
            r"\!\[[^\]]+\]" : "![]",
            r"^# ":"## ",
            r"\[.column\]" : "",
            #"^---":"#",

        }

        self._read()

    def _read(self):

        self.buffer = list()
        first = True
        self.output = False
        self.skipslide = False
        self.removeComment = False

        with open(self.filename, encoding="utf-8") as fi:
            for line in fi:

                if(first and re.search(r"^\s*$",line)):
                    first = False
                    self.output = True

                key = ""
                val = ""
                m = re.search(r"<!--pan_([^:]+):(.*)$",line)
                if(m):
                    key = m.groups()[0]
                    val = m.groups()[1]


                if(key == "title"):
                    self.title = val.replace("-->","")

                if(re.search(r"^<!--",line)):
                    self.output = False

                line = self._filterLine(line)
                line = self._convertImage(line)

                if(line is not None and self.output):
                    self.buffer.append(line)

                if(re.search(r"-->",line)):
                    self.output = True

    def __str__(self):

        ss = ""

        ss += f"""---
title: {self.title}
output:
  slidy_presentation:
    footer: "Copyright (c) 2025, ASICedu.com"
    fig_width: 800
---

""" + """




"""
        for l in self.buffer:
            ss += l
        return ss

class Latex(Lecture):

    def __init__(self,filename,options):
        self.filename = filename
        self.title = filename.replace(".md","")
        self.options = options

        self.images = list()

        self.filters = {
             r"^\s*---\s*$" : "",
            r"\[.column\]" : "",
            r"\[\.background.*\]" : "",
            r"\[\.text.*\]" : "",
            r"\[\.table  *\]" : "",
            r"\#\s*\[\s*fit\s*\]" : "# ",
            r"\#\#\s*\[\s*fit\s*\]" : "## ",
            #"^## \*\*Q:\*\*.*$" : "",
            r"^[.table.*]$": "",
            r"^\* TOC":"",
            r"^{:toc }":"",
            r"\*\*Q:\*\*" : "",
            r"#(.*) Thanks!" : ""
            #"^---":"#",
        }

        self._read()



    def __str__(self):

        ss = ""

        ss += f"""

""" + """




"""
        for l in self.buffer:
            ss += l
        return ss

def _pandoc_bin():
    """
    Locate pandoc executable, honoring PANDOC_BIN/PANDOC env vars.
    """
    for var in ("PANDOC_BIN", "PANDOC"):
        candidate = os.environ.get(var)
        if candidate:
            return candidate
    return shutil.which("pandoc")

@click.group()
def cli():
    """
    Convert a lecture to something
    """
    pass

@cli.command()
@click.argument("filename")
@click.option("--root",default="/analogIC/",help="Root of jekyll site")
@click.option("--date",default=None,help="Date to use")
def post(filename,root,date):
    options = dict()
    options["jekyll"] = root
    options["dir"] = os.path.dirname(filename)

    os.makedirs("docs/assets/media/", exist_ok=True)
    os.makedirs("docs/_posts", exist_ok=True)

    #- Post
    l = Lecture(filename,options=options)

    if(date is None and l.date is not None):
        date = l.date
    else:
        raise Exception(f"I need a date, either in the frontmatter, or the option for {filename}")

    l.copyAssets()
    fname = "docs/_posts/" + date +"-"+ l.title.strip().replace(" ","-") + ".markdown"

    with open(fname,"w", encoding="utf-8") as fo:
        fo.write(str(l))
    


@cli.command()
@click.argument("filename")
@click.option("--root",default="pdf/",help="output roote")
def latex(filename,root):
    options = dict()
    options["latex"] = root
    options["downloadImage"] = True
    options["allowIP"] = True
    options["dir"] = os.path.dirname(filename)
    p = Latex(filename,options)
    p.copyAssets()


    fname = root + os.path.sep + p.title.strip().replace(" ","_").lower() + ".md"
    with open(fname,"w", encoding="utf-8") as fo:
        fo.write(str(p))

    flatex = fname.replace(".md",".latex")
    pandoc_bin = _pandoc_bin()
    if pandoc_bin is None:
        raise RuntimeError(
            "Pandoc is required for latex generation; set PANDOC_BIN (e.g. to C:\\path\\to\\pandoc.exe) or add pandoc to PATH."
        )
    cmd = [
        pandoc_bin,
        "--citeproc",
        "--bibliography=pdf/analogic.bib",
        "--csl=pdf/ieee-with-url.csl",
        "-o",
        flatex,
        fname,
    ]
    try:
        subprocess.run(cmd, check=True)
    except FileNotFoundError as exc:
        raise RuntimeError(
            "pandoc is required for latex generation; please install it and ensure it is on PATH."
        ) from exc
    except subprocess.CalledProcessError as exc:
        raise RuntimeError(f"pandoc failed while converting {fname}") from exc




if __name__ == "__main__":
    cli()
