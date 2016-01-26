#!/usr/bin/python3
#
# backup.py - backup script for server resources.
#
# Copyright 2016 Yasutaka SATO <yasutaka@freesoul.org>
#

__version__ = '1.2.0'

import configparser
import subprocess
import argparse
import os
import sys
from time import mktime, strftime
from datetime import date, datetime
import re

def check_repo_server(cfg):
    try:
        basics = cfg['basic']
        details = cfg['detail']
        remote_archive = cfg.get('detail','remote_archive_format',raw=True) % {"backup_server":basics['backup_server'],"host":basics['host']}
        details['remote_archive'] = remote_archive
        dirs = [
            details['bk_home'],
            details['bk_home'] + '/' + details['bk_repository'],
            details['bk_home'] + '/' + details['bk_dir'], 
            details['bk_home'] + '/' + details['bk_dbdir'], 
            details['bk_home'] + '/' + details['bk_mirror'], 
            details['bk_archive'],
            remote_archive,
        ]
        errors = []
        for d in dirs:
            if not os.path.isdir(d):
                if details.getboolean('create_dir') and not details.getboolean('is_test'):
                    os.makedirs(d)
                else:
                    errors.append(d)
        if len(errors) > 0:
            print ('Error: ',', '.join(errors) ," don't exist")
            sys.exit(1)
    except configparser.Error as e:
        print ("Error: can't parse config at check_repo_server():", e)
        sys.exit(1)
    else:
        return

def set_target_dbs(cfg):
    try:
        targets = {}
        db_list = []
        basics = cfg['basic']
        details = cfg['detail']
        for d in basics['target_dbs'].splitlines():
            d = 'db:' + d
            dbtype = cfg[d]['dbtype']
            dbname = cfg[d]['dbname']
            targets[dbname] = {}
            dbargs = {}
            dbargs['verbose'] = cfg[dbtype]['verbose'] if not details.getboolean('is_quiet') else ''
            for v in cfg[dbtype]['vars'].split():
                targets[dbname][v] = cfg.get(d,v)
                dbargs[v] = cfg.get(d,v)
            targets[dbname]['dbtype'] = dbtype
            targets[dbname]['dbcmd'] = cfg.get(dbtype,'cmd_format',raw=True) % dbargs
    except configparser.Error as e:
        print ("Error: can't parse config at set_target_dbs():", e)
        sys.exit(1)
    else:
        return targets

def set_target_dirs(cfg):
    try:
        targets = []
        basics = cfg['basic']
        for d in basics['target_dirs'].splitlines():
            targets.append(d)
    except configparser.Error as e:
        print ("Error: can't parse config at set_target_dirs():", e)
        sys.exit(1)
    else:
        return targets

def set_target_mirrors(cfg):
    try:
        targets = {}
        basics = cfg['basic']
        args = ['scheme','host','path']
        for d in basics['target_mirrors'].splitlines():
            targets[d] = {}
            m = re.match(r"(?P<scheme>[^:]+)://(?P<host>[^/]+)(?P<path>/.*$)",d)
            if m is None:
                print ("Not Matched")
                sys.exit(1)
            for a in args:
                targets[d][a] = m.group(a)
    except configparser.Error as e:
        print ("Error: can't parse config at set_target_mirrors():", e)
        sys.exit(1)
    else:
        return targets

def dbs_backup_exe(cfg,targets):
    details = cfg['detail']
    sweeptype = details['sweep_type']
    sweepargs = {}
    sweepargs['verbose'] = cfg[sweeptype]['verbose'] if not details.getboolean('is_quiet') else ''
    sweepargs['sweep_mtime'] = details['sweep_mtime']
    sweepargs['sweep_dir'] = details['bk_home'] + '/' + details['bk_dbdir']
    sweepcmd = cfg.get(sweeptype,'cmd_format',raw=True) % sweepargs
    for db in targets:
        try:
            print ("backup database \"%s\" ..." % db)
            archive_filename = "%s/%s/%s_%s" % (details['bk_home'],details['bk_dbdir'],targets[db]['dbname'],date)
            cmd = "%s > %s && %s %s" \
                  % (targets[db]['dbcmd'],archive_filename,details['gzip_cmd'],archive_filename)
            output_cmd = ""
            output_tmpcmd = ""
            if details.getboolean('is_test'):
                print ("EXEC: ",cmd)
                print ("EXEC: ",sweepcmd)
            else:
                output_cmd = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
                output_sweepcmd = subprocess.check_output(sweepcmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as c:
            print ("Execute Failed:", c)
            sys.exit(c.returncode)
        else:
            if not details.getboolean('is_quiet') and not details.getboolean('is_test'):
                print (output_cmd.decode('utf-8'))
                print (output_sweepcmd.decode('utf-8'))
                lap = mktime(datetime.now().timetuple())
                print ("Lap Time:", lap - begin_date)
            print ("done\n")
    return

def dirs_backup_exe(cfg,targets):
    details = cfg['detail']
    for d in targets:
        try:
            print ("backup %s ..." % d)
            synctype = details['sync_type']
            syncargs = {}
            syncargs['verbose'] = cfg[synctype]['verbose'] if not details.getboolean('is_quiet') else ''
            syncargs['src'] = d
            syncargs['dest'] = details['bk_home'] + '/' + details['bk_dir']
            cmd = cfg.get(synctype,'cmd_format',raw=True) % syncargs
            output_cmd = ""
            if details.getboolean('is_test'):
                print ("EXEC: ",cmd)
            else:
                output_cmd = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as c:
            print ("Execute Failed:", c)
            sys.exit(c.returncode)
        else:
            if not details.getboolean('is_quiet') and not details.getboolean('is_test'):
                print (output_cmd.decode('utf-8'))
                lap = mktime(datetime.now().timetuple())
                print ("Lap Time:", lap - begin_date)
            print ("done\n")
    return

def mirrors_backup_exe(cfg,targets):
    details = cfg['detail']
    for d in targets:
        try:
            print ("backup %s ..." % d)
            synctype = targets[d]['scheme']
            syncargs = {}
            syncargs['verbose'] = cfg[synctype]['verbose'] if not details.getboolean('is_quiet') else ''
            syncargs['host'] = targets[d]['host']
            syncargs['src'] = targets[d]['path']
            syncargs['dest'] = details['bk_home'] + '/' + details['bk_mirror']
            cmd = cfg.get(synctype,'cmd_format',raw=True) % syncargs
            output_cmd = ""
            if details.getboolean('is_test'):
                print ("EXEC: ",cmd)
            else:
                output_cmd = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as c:
            print ("Execute Failed:", c)
            sys.exit(c.returncode)
        else:
            if not details.getboolean('is_quiet') and not details.getboolean('is_test'):
                print (output_cmd.decode('utf-8'))
                lap = mktime(datetime.now().timetuple())
                print ("Lap Time:", lap - begin_date)
            print ("done\n")
    return

def make_archive(cfg,today):
    basics = cfg['basic']
    details = cfg['detail']
    try:
        print ("archive %s ..." % cfg.get('detail','bk_repository'))
        archivetype = details['archive_type']
        archiveargs = {}
        archiveargs['exec_dir'] = details['bk_home'] + '/' + details['bk_repository']
        archiveargs['archive_file'] = '%s/BACKUP_%s_%s.tgz' % (details['bk_archive'],basics['host'],today)
        archiveargs['target_dir'] = details['archive_target']
        archivecmd = cfg.get(archivetype,'cmd_format',raw=True) % archiveargs
        cptype = details['cp_type']
        cpargs = {}
        cpargs['exec_dir'] = details['bk_home']
        cpargs['verbose'] = cfg[cptype]['verbose'] if not details.getboolean('is_quiet') else ''
        cpargs['archive_file'] = archiveargs['archive_file']
        cpargs['target_dir'] = details['remote_archive']
        cpcmd = cfg.get(cptype,'cmd_format',raw=True) % cpargs
        output_archivecmd = ""
        output_cpcmd = ""
        if details.getboolean('is_test'):
            print ("EXEC: ",archivecmd)
            print ("EXEC: ",cpcmd)
        else:
            output_archivecmd = subprocess.check_output(archivecmd, shell=True, stderr=subprocess.STDOUT)
            output_cpcmd = subprocess.check_output(cpcmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as c:
        print ("Execute Failed:", c)
        sys.exit(c.returncode)
    else:
        if not details.getboolean('is_quiet') and not details.getboolean('is_test'):
            print (output_archivecmd.decode('utf-8'))
            print (output_cpcmd.decode('utf-8'))
            lap = mktime(datetime.now().timetuple())
            print ("Lap Time:", lap - begin_date)
        print ("done\n")

    return

def sweep_archive(cfg):
    details = cfg['detail']
    try:
        print ('archive sweep ...')
        sweeptype = details['sweep_type']
        sweepargs = {}
        sweepargs['verbose'] = cfg[sweeptype]['verbose'] if not details.getboolean('is_quiet') else ''
        sweepargs['sweep_mtime'] = details['sweep_mtime']
        sweepargs['sweep_dir'] = details['bk_archive'] + " " + details['remote_archive']
        sweepcmd = cfg.get(sweeptype,'cmd_format',raw=True) % sweepargs
        output_sweepcmd = ""
        if details.getboolean('is_test'):
            print ("EXEC: ",sweepcmd)
        else:
            output_sweepcmd = subprocess.check_output(sweepcmd, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as c:
        print ("Execute Failed:", c)
        sys.exit(c.returncode)
    else:
        if not details.getboolean('is_quiet') and not details.getboolean('is_test'):
            print (output_sweepcmd.decode('utf-8'))
            lap = mktime(datetime.now().timetuple())
            print ("Lap Time:", lap - begin_date)
        print ("done\n")

    return

def nagios_passive_notify(cfg,exet):
    nagios = cfg['nagios']
    details = cfg['detail']
    STATE_OK=0
    STATE_WARNING=1
    STATE_CRITICAL=2
    STATE_UNKNOWN=3
    STATE_DEPENDENT=4
    warning_time  = float(nagios['warning_time'])
    critical_time = float(nagios['critical_time'])
    exec_time = float(exet)
    sargs = {}
    sargs['passive_check_host'] = nagios['passive_check_host']
    sargs['passive_check_remote_host'] = nagios['passive_check_remote_host']
    sargs['passive_check_service'] = nagios['passive_check_service']
    sargs['passive_check_port'] = nagios['passive_check_port']
    sargs['warning_time'] = warning_time
    sargs['critical_time'] = critical_time
    sargs['exec_time'] = exec_time
    if exec_time >= 0.0 and exec_time < warning_time:
        sargs['passive_status'] = STATE_OK
        sargs['passive_msg'] = 'OK: backup exec time ok'
    elif exec_time >= warning_time and exec_time < critical_time:
        sargs['passive_status'] = STATE_WARNING
        sargs['passive_msg'] = 'WARNING: backup exec time warning'
    elif exec_time >= critical_time:
        sargs['passive_status'] = STATE_CRITICAL
        sargs['passive_msg'] = 'CRITICAL: backup exec time critical'
    else:
        sargs['passive_status'] = STATE_UNKNOWN
        sargs['passive_msg'] = 'UNKNOWN: backup exec time unknown error'
    status_string = cfg.get('nagios','passive_echo_format',raw=True) % sargs
    sendcommand = cfg.get('nagios','passive_cmd_format',raw=True) % sargs
    scommand = "echo \"%s\" | %s" % (status_string,sendcommand)
    try:
        print ('send nagios passive command ...')
        if details.getboolean('is_test'):
            print ("EXEC: ",scommand)
        else:
            output_scommand = subprocess.check_output(scommand, shell=True, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as c:
        print ("Execute Failed:", c)
        sys.exit(c.returncode)
    else:
        if not details.getboolean('is_quiet') and not details.getboolean('is_test'):
            print (output_scommand.decode('utf-8'))
        print ("done\n")

    return

##########
# main
##########

#
# parse command arguments
#
parser = argparse.ArgumentParser(description='Backup the Server Resources')
parser.add_argument('-f', action='store', dest='file', default='/etc/backup-py.conf',
                    help='specify an alternative config file')
parser.add_argument('-t', action='store_true', dest='is_test', default=False,
                    help='test run with no changes made')
parser.add_argument('-m', action='store_true', dest='create_dir', default=False,
                    help='create the repository')
parser.add_argument('-V', '--version', action='version', version='%(prog)s '+ __version__,
                    help='version information')

results = parser.parse_args()

#
# load config and set vars
#
if os.access(results.file,os.R_OK):
    try:
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(results.file)
    except config.ParsingError as e:
        print ("Error: %s can't read" % results.file)
        sys.exit(e.returncode)
else:
    print ("Error: %s not found OR can't read" % results.file)
    sys.exit(1)

if results.is_test:
    config.set('detail','is_test','1')

if results.create_dir:
    config.set('detail','create_dir','1')


#
# check and create directories for repository and archive server
#
check_repo_server(config)


#
# BEGIN Backup
#
date = strftime("%Y%m%d")
begin_date = mktime(datetime.now().timetuple())
#print ("BEGIN Backup\n")
#print ("BEGIN Backup\n\tProgram Version: %s\n\tStart Date: %s\n" % __version__, begin_date)
print ("BEGIN Backup  by %s %s\n" % (sys.argv[0], __version__))

#
# database backup
#
if config.has_option('basic','target_dbs'):
    target_dbs = set_target_dbs(config)
    dbs_backup_exe(config,target_dbs)

#
# file and directory backup
#
if config.has_option('basic','target_dirs'):
    target_dirs = set_target_dirs(config)
    dirs_backup_exe(config,target_dirs)


#
# file and directory backup WITHOUT archive (only mirror)
#
if config.has_option('basic','target_mirrors'):
    mirrors = set_target_mirrors(config)
    mirrors_backup_exe(config,mirrors)


#
# make an archive file from repository and copy to archive server
#
make_archive(config,date)

#
# sweep repository and arhcive server
#
sweep_archive(config)

#
# END Backup
#
print ("END Backup\n")

end_date = mktime(datetime.now().timetuple())
etime = end_date - begin_date

print ("Exec Time:",etime,"\n")

if config.getboolean('nagios','is_nagios') and config.getboolean('nagios','is_passive'):
    nagios_passive_notify(config,etime)


sys.exit(0)
