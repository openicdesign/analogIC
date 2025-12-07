#!/usr/bin/env python3

import re
import sys
import os
import shutil
import subprocess
fname = sys.argv[1]


def _magick():
    """
    Locate ImageMagick executable. Prefer IMAGEMAGICK_BIN env, then magick, then convert.
    """
    candidates = []
    env_bin = os.environ.get("IMAGEMAGICK_BIN")
    if env_bin:
        candidates.append(env_bin)
    candidates.append("magick")
    # Look for default Windows installation if not on PATH
    search_roots = [
        os.environ.get("PROGRAMFILES"),
        os.environ.get("PROGRAMFILES(X86)"),
        os.environ.get("IMAGEMAGICK_HOME"),
        r"C:\Software",
    ]
    for base in search_roots:
        if not base or not os.path.isdir(base):
            continue
        for entry in os.listdir(base):
            if entry.lower().startswith("imagemagick"):
                candidates.append(os.path.join(base, entry, "magick.exe"))
    candidates.append("convert")
    for cmd in candidates:
        if os.path.basename(cmd) == cmd:
            exe = shutil.which(cmd)
        else:
            exe = cmd if os.path.exists(cmd) else None
        if exe:
            return exe
    return None

MAGICK_BIN = _magick()

def imgConvert(ftype,fotype,path,required=True):
    fopath = "media/"+ os.path.basename(path).replace(ftype,fotype)
    if os.path.exists(fopath):
        return fopath
    if MAGICK_BIN is None:
        raise RuntimeError(
            "ImageMagick (magick/convert) not found; install it or set IMAGEMAGICK_BIN."
        )
    cmd = [MAGICK_BIN, "-density", "100", path, fopath]
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        if required:
            raise RuntimeError(f"Image conversion failed for {path}") from exc
        print(f"Warning: unable to convert {path} -> {fopath}, using original file")
        return path
    return fopath


def toPng(ftype,path):
    required = ftype.lower() != ".pdf"
    return imgConvert(ftype,".png",path,required=required)

def toPdf(ftype,path):
    return imgConvert(ftype,".pdf",path)

def getPath(line):

    m = re.findall(r"{([^{}]+)}",line)
    path = m[0]

    return path

tmplt = r"""
{
\centering
\includegraphics[width=\myfigwidth]{#path#}

}
"""

#tmplt = r"""
#\pandocbounded{\includegraphics[width=\myfigwidth]{#path#}}
#"""

foname = fname.replace(".latex","_fiximg.tex")
foname_png = fname.replace(".latex","_fiximg_png.tex")
with open(fname) as fi:
    with open(foname,"w") as fo:
        with open(foname_png,"w") as fo_png:
            for line in fi:

                #- Fix titles for kao
                #if(re.search(r"^\s*\\chapter",line)):
                #    nline = """\setchapterstyle{kao}
#\setchapterpreamble[u]{\margintoc}
#""" + line
 #                   fo.write(nline)
 #                   fo_png.write(line)
 #                   continue

                #- Pandoc sometimes uses includesvg instead of includegraphics
                line = line.replace("includesvg","includegraphics")
                if(re.search(r"includegraphics(\[[^\]]+\])?{",line)):
                    path = getPath(line)
                    fopath = path
                    fopath_png = path
                    if(path.endswith(".svg")):
                        fopath = toPdf(".svg",path)
                        fopath_png = toPng(".svg",path)
                        pass
                    elif(path.endswith(".gif")):
                        fopath = toPng(".gif",path)
                        fopath_png = fopath
                        pass
                    elif(path.endswith(".pdf")):
                        fopath_png = toPng(".pdf",path)
                        pass
                    fo.write(tmplt.replace("#path#",fopath))
                    fo_png.write(tmplt.replace("#path#",fopath_png))
                else:
                    fo.write(line)
                    fo_png.write(line)
