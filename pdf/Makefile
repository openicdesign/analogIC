
VERSION_DATE=Built on $(shell date)
VERSION_HASH=${shell git log -1 --pretty=format:"%H"}
FILE=analogic

TEXS = ${shell ls -1 *.latex}

PYTHON := $(shell if [ -x ../venv/bin/python ]; then printf "../venv/bin/python"; \
	elif command -v python3 >/dev/null 2>&1; then command -v python3; \
	elif command -v python >/dev/null 2>&1; then command -v python; \
	else printf "python3"; fi)

#- Ensure TEXINPUTS works on both Unix (:) and Windows (;)
ifeq ($(OS),Windows_NT)
  TEXINPUTS_DELIM := ;
else
  TEXINPUTS_DELIM := :
endif
export TEXINPUTS := .$(TEXINPUTS_DELIM)kaobook$(TEXINPUTS_DELIM)

kaobook:
	git clone https://github.com/fmarotta/kaobook.git

fix:
	${foreach f, ${TEXS}, "${PYTHON}" fix_svg.py ${f};}

hash:
	printf '%s %s %s\n%s %s %s\n' '\noindent' "${VERSION_DATE}" '\\\\' '\noindent' 'from' "${VERSION_HASH}" > version.tex

#- Choose right pandoc file based on pandoc version
PANDOC_BIN ?= pandoc
PANDOC_VERSION := $(shell "$(PANDOC_BIN)" --version | head -n 1 | cut -d " " -f 2 | cut -d "." -f "1,2")
PANDOC_TMPL := $(firstword $(wildcard pandoc_${PANDOC_VERSION}.tex pandoc_3.4.tex pandoc_3.1.tex))
pandoc.tex:
	cp ${PANDOC_TMPL} pandoc.tex


one: fix hash kaobook pandoc.tex
	export
	chmod -R 755  media
	pdflatex ${FILE}
	#TEXINPUTS=".:kaobook:" makeindex ${FILE}.nlo
	#-pdflatex -interaction nonstopmode --shell-escape ${FILE}.latex
	-bibtex ${FILE}
	pdflatex ${FILE}
	pdflatex ${FILE}
	#TEXINPUTS=".:kaobook:" pdflatex ${FILE}.tex
	#-pdflatex -interaction nonstopmode --shell-escape ${FILE}.latex

compress:
	gs -sDEVICE=pdfwrite -dCompatibilityLevel=1.4 -dPDFSETTINGS=/ebook \
	-dNOPAUSE -dQUIET -dBATCH -sOutputFile=${FILE}_compress.pdf ${FILE}.pdf

ebook:
	cat ${FILE}.tex |perl -pe "s/fiximg/fiximg_png/ig" > ${FILE}_epub.latex
	pandoc --gladtex -o ${FILE}.epub ${FILE}_epub.latex

clean:
	-rm *.latex
	-rm *_fiximg.tex
	-rm *.md
	-rm *.epub
	-rm -rf media
	-rm *.bbl
	-rm *.aux
	-rm *.toc
	-rm *.log
	-rm *.blg
	-rm *.dvi
	-rm *.fff
	-rm *.lof
	-rm *.lot
	-rm *.ttt
	-rm *.xml
	-rm *.pdf
	-rm *.bcf
	-rm *fiximg*.tex
