# Build the handover presentation.
#
#   make            -> main.pdf
#   make notes      -> main-notes.pdf, slides with presenter notes beside them
#   make clean      -> remove LaTeX build products (not the PDF)
#
# Requires: a TeX Live install with beamer and beamertheme-metropolis.
# Compiles with pdflatex; metropolis falls back to the default fonts when Fira
# is absent, which is the case here.

.PHONY: all notes clean
all: main.pdf

main.pdf: main.tex
	latexmk -pdf -interaction=nonstopmode main.tex

notes:
	sed 's|^% \\setbeameroption|\\setbeameroption|' main.tex > main-notes.tex
	latexmk -pdf -interaction=nonstopmode main-notes.tex
	rm -f main-notes.tex

clean:
	latexmk -c
	rm -f main-notes.*
