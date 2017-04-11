NAME=tendrl-commons
VERSION := $(shell PYTHONPATH=. python -c \
             'import tendrl.commons; print tendrl.commons.__version__' \
             | sed 's/\.dev[0-9]*//')
RELEASE=1
COMMIT := $(shell git rev-parse HEAD)
SHORTCOMMIT := $(shell echo $(COMMIT) | cut -c1-7)
GIT_RELEASE := $(shell git describe --tags --match 'v*' \
                 | sed 's/^v//' \
                 | sed 's/^[^-]*-//' \
                 | sed 's/-.*//')

all: srpm

clean:
	rm -rf dist/
	rm -f $(NAME)-$(VERSION).tar.gz
	rm -rf $(NAME)-$(VERSION)-$(RELEASE).el7.src.rpm

dist:
	python setup.py sdist \
	  && mv dist/$(NAME)-$(VERSION).tar.gz .

srpm: dist
	fedpkg --dist epel7 srpm

rpm: dist
	mock -r epel-7-x86_64 rebuild $(NAME)-$(VERSION)-$(RELEASE).el7.src.rpm --resultdir=. --define "dist .el7"

gitversion:
	# Set version and release to the latest values from Git
	$(eval VERSION := $(VERSION).dev$(GIT_RELEASE))
	$(eval RELEASE := $(GIT_RELEASE).$(SHORTCOMMIT))
	sed -i tendrl/commons/__init__.py \
	  -e "s/^__version__ = .*/__version__ = '$(VERSION)'/"
	sed -i tendrl-commons.spec \
	  -e "s/^Version: .*/Version: $(VERSION)/"
	sed -i tendrl-commons.spec \
	  -e "s/^Release: .*/Release: $(RELEASE)/"

snapshot: gitversion srpm


.PHONY: dist rpm srpm gitversion snapshot
