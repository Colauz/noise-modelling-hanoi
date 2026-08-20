# Build the end-of-internship presentation.
#
#   make                     -> main.pdf
#   make notes               -> main-notes.pdf, presenter notes beside each slide
#   make script              -> script.pdf, the bilingual speaker script
#   make check               -> verify script.pdf names the slides main.tex has
#   make view                -> build, then open the PDF
#   make logos               -> report which institutional marks are present
#   make logos-placeholder   -> regenerate the typographic placeholder marks
#   make clean               -> remove LaTeX build products (not the PDF)
#   make distclean           -> also remove main.pdf
#
# FIGURES. figures/*.pdf are built from models/metrics.json and the published
# CSVs by scripts/12_presentation_figures.py, at the repository root:
#
#     make -C .. slides        # figures, then this deck
#
# The deck does not regenerate them itself: they are pipeline output, and the
# root Makefile is where pipeline output is declared.
#
# Requires a TeX Live install with beamer, beamertheme-metropolis, tikz,
# booktabs, standalone and appendixnumberbeamer.
#
# ENGINE. pdflatex is the default because it is the one that works everywhere.
# main.tex also compiles under lualatex, which picks up system Lato and gives
# noticeably better typography:
#
#     make ENGINE=lualatex
#
# If lualatex fails with "Font ... not loadable: metric data not found", the
# luaotfload cache is stale or the Latin Modern OpenType fonts are missing.
# `luaotfload-tool --update --force` usually fixes it; otherwise stay on pdflatex,
# which produces the same slides.

ENGINE  ?= pdflatex
PYTHON  ?= python3
LATEXMK := latexmk -interaction=nonstopmode -halt-on-error

ifeq ($(ENGINE),lualatex)
  ENGINEFLAG := -lualatex
else
  ENGINEFLAG := -pdf
endif

.PHONY: all notes script check view clean distclean logos logos-placeholder
all: main.pdf script.pdf

main.pdf: main.tex appscreens.tex $(wildcard logos/*.pdf) $(wildcard figures/*.pdf)
	$(LATEXMK) $(ENGINEFLAG) main.tex

# Presenter notes on a second screen. The \setbeameroption line lives commented
# out in main.tex; this uncomments it into a throwaway copy so main.tex itself is
# never edited by the build.
notes:
	sed 's|^% \\setbeameroption|\\setbeameroption|' main.tex > main-notes.tex
	$(LATEXMK) $(ENGINEFLAG) main-notes.tex
	rm -f main-notes.tex

# The speaker script: what to say on each slide, English beside French. It is
# prose and quotes no number the deck does not also carry, so it needs none of
# the figures -- but it names every slide by number and title, and those must be
# the deck's. check_script.py enforces that, and the build refuses rather than
# handing a presenter a script that disagrees with the screen.
script: script.pdf
script.pdf: script.tex main.tex
	$(PYTHON) check_script.py
	$(LATEXMK) $(ENGINEFLAG) script.tex

# Same check on its own, and `check_script.py --fix` to take the deck's titles.
check:
	@$(PYTHON) check_script.py

view: main.pdf
	@xdg-open main.pdf 2>/dev/null || open main.pdf 2>/dev/null || \
	 echo "Open presentation/main.pdf yourself."

# Report which institutional marks are present. The deck compiles either way:
# a missing logo degrades to the institution's name set in type.
logos:
	@for l in cosmos vinuni isima uca; do \
	  if [ -f logos/$$l.pdf ]; then echo "  present  logos/$$l.pdf"; \
	  else echo "  MISSING  logos/$$l.pdf  -> falls back to text"; fi; done
	@echo "See logos/README.md for the expected files."

# Regenerate the PLACEHOLDER marks. These are neutral typographic slugs, not the
# institutions' logos: they exist so the logo band is composed and evenly
# weighted while the real files are being obtained. Drop the real PDFs into
# logos/ under the same names and this target becomes unnecessary.
logos-placeholder:
	cd logos && pdflatex -interaction=nonstopmode placeholders.tex
	cd logos && pdfseparate placeholders.pdf tmp-%d.pdf \
	  && mv tmp-1.pdf cosmos.pdf && mv tmp-2.pdf vinuni.pdf \
	  && mv tmp-3.pdf isima.pdf && mv tmp-4.pdf uca.pdf
	cd logos && rm -f placeholders.aux placeholders.log

clean:
	$(LATEXMK) -c
	$(LATEXMK) -c script.tex
	rm -f main-notes.*

distclean: clean
	rm -f main.pdf script.pdf
