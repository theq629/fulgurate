PYTHON?=python2
A2X?=a2x

PROGS=$(addprefix fulgurate-, run import show-schedule)
MANPAGES=fulgurate.1 $(addsuffix .1, $(PROGS))
MANTEMPNAME=temp

all: man

%.1: %
	( echo $< | tr 'a-z' 'A-Z' | sed -e 's|$$|(1)|g'; echo $< | sed -e 's|.|=|g;s|$$|===|g'; cp $< $(MANTEMPNAME).py; $(PYTHON) -c "import $(MANTEMPNAME); print $(MANTEMPNAME).__doc__"; echo -e "SEE ALSO\n--------\n'fulgurate(1)'" ) > $(MANTEMPNAME).txt
	$(A2X) -f manpage -L $(MANTEMPNAME).txt

fulgurate.1: fulgurate-man README
	./$< > $(MANTEMPNAME).txt
	$(A2X) -f manpage -L $(MANTEMPNAME).txt

man: $(MANPAGES)

clean:
	rm -rf *.pyc $(MANTEMPNAME).py $(MANTEMPNAME).txt $(MANPAGES)
