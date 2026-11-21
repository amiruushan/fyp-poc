#!/bin/sh
set -eu
paper_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
paper_build_dir=$(mktemp -d)
trap 'rm -rf "$paper_build_dir"' EXIT
cp "$paper_dir/manuscript.tex" "$paper_build_dir/"
cp -R "$paper_dir/figures" "$paper_build_dir/"
cp "$paper_dir/template/"* "$paper_build_dir/"
cd "$paper_build_dir"
pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex > first-pass.log 2>&1 || { cat first-pass.log; exit 1; }
pdflatex -interaction=nonstopmode -halt-on-error manuscript.tex > second-pass.log 2>&1 || { cat second-pass.log; exit 1; }
cp manuscript.pdf "$paper_dir/manuscript.pdf"
printf 'Built %s\n' "$paper_dir/manuscript.pdf"
