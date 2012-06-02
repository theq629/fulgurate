PREFIX?=/usr
BINPREFIX?=$(PREFIX)/bin
LIBPREFIX?=$(PREFIX)/lib/fulgurate
MANPREFIX?=$(PREFIX)/man
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

install: man
	mkdir -p $(LIBPREFIX)
	cp -f *.py $(PROGS) $(LIBPREFIX)
	chmod ug+x $(addprefix $(LIBPREFIX)/, $(PROGS))
	mkdir -p $(MANPREFIX)
	cp -f $(MANPAGES) $(MANPREFIX)
	mkdir -p $(BINPREFIX)
	for bin in $(PROGS); do ln -s $(LIBPREFIX)/$$bin $(BINPREFIX)/$$bin; done

clean:
	rm -rf *.pyc $(MANTEMPNAME).py $(MANTEMPNAME).txt $(MANPAGES)
