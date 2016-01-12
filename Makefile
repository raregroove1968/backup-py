PACKAGE =	backup-py
PACKAGE_NAME = 	Server Backup Python Script
PACKAGE_TARNAME = backup-py
DESTDIR	=	/var/tmp/backup-py/tmp

usbindir =	$(DESTDIR)/usr/sbin
docdir	=	$(DESTDIR)/usr/share/doc/$(PACKAGE_TARNAME)
exdir	=	$(docdir)/examples
etcdir	=	$(DESTDIR)/etc
crondir	=	$(etcdir)/cron.daily

conf	=	examples/$(PACKAGE_TARNAME).conf
log_cron = 	examples/$(PACKAGE_TARNAME).log.cron
program =	./src/backup.py
docs	=	./README ./COPYING

install = 	/usr/bin/install -c
install_program = $(install)

install:
	$(install) -d $(usbindir) $(etcdir) $(crondir) $(docdir) $(exdir)
	$(install_program) $(program) $(usbindir)
	$(install) -m 600 $(conf) $(etcdir)
	$(install) -m 755 $(log_cron) $(crondir)/$(PACKAGE)
	$(install) ./examples/* $(exdir)
	$(install) $(docs) $(docdir)
