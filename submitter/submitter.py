#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
from glob import glob
from os.path import basename, abspath
from shutil import copyfile
import time
import os
import configparser
from string import Template
import logging
import logzero
import numpy as np
from logzero import logger

'''
Outline of program:
    You would love to give a command line option that 

    You give a
        - Folder containing all submittable scripts.
        - maximum number of jobs the program will be allowed to submit. 
        - ???

'''
class Error(Exception):
    """Base class for exceptions in this module."""
    pass

class InputError(Error):
    """Exception raised for errors in the input.

    Attributes:
        message -- explanation of the error
    """
    def __init__(self, message):
        self.message = message
    def __str__(self):
        return repr(self.message)

def _get_qstat():
    return subprocess.check_output(["qstat"])
    
def _parse_qstat_state(qstat_out, job_id):
    """Parse "state" column from `qstat` output for given job_id
    Returns state for the *first* job matching job_id. Returns 'u' if
    `qstat` output is empty or job_id is not found.
    """
    if qstat_out.strip() == '':
        return 'u'
    lines = qstat_out.split('\n')
    # skip past header
    while not lines.pop(0).startswith('---'):
        pass
    for line in lines:
        if line:
            job, prior, name, user, state = line.strip().split()[0:5]
            if int(job) == int(job_id):
                return state
    return 'u'


def _parse_qsub_job_id(qsub_out):
    """Parse job id from qsub output string.
    Assume format:
        "Your job <job_id> ("<job_name>") has been submitted"
    """
    return int(qsub_out.split()[2])


def _build_qsub_command(qsubOptions):
    """Submit shell command to SGE queue via `qsub`"""
    qsub_template = Template('qsub -cwd -o ${outFile} -e ${errFile} -q ${queue} -N ${jobName} -l h_rss=${maxram}G,h_vmem=${maxram}G ${script}')
    return qsub_template.safe_substitute(qsubOptions)

def _parse_all_job_ids(qstat_out):
    JobIDs = []
    if qstat_out.strip() == '':
        return []
    lines = qstat_out.split('\n')
    # skip past header
    while not lines.pop(0).startswith('---'):
        pass
    for line in lines:
        if line:
            job, prior, name, user, state = line.strip().split()[0:5]
            JobIDs.append(int(job))

    return JobIDs

def parseQsubOptions(config,section):
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                DebugPrint("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1

def setupLogging(options):

    # Set a custom formatter
    log_format = '%(color)s[%(levelname)s %(asctime)s %(module)s:%(lineno)d]%(end_color)s %(message)s'
    formatter = logzero.LogFormatter(fmt=log_format)
    logzero.setup_default_logger(formatter=formatter)

    # Set a minimum log level
    logzero.loglevel(logging.INFO)

    # Set a logfile (all future log messages are also saved there)
    logzero.logfile(os.path.abspath(options.folder)+"/submitter.log",formatter=formatter)

def main(options):
    """
    :returns: TODO

    """
    setupLogging(options)
    
    if int(os.uname()[1].split(".")[0][5:]) not in range(400,408):
        try:
            raise Exception("Run on heppc400-407")
        except Exception as e:
            logger.exception(e)
            raise

    

    from pkg_resources import resource_filename
    foo_config = resource_filename('submitter', 'config/config.ini')
    print foo_config

    config = configparser.ConfigParser()
    if options.configFile == "N/A":
        files_read =config.read([foo_config, 
            os.path.expanduser('~/.submitterrc')])
        for fname in files_read:
            print "Reading config from", fname
        print config.keys()
        print config.get("qsubOptions",'queue')
    else:
        files_read =config.read([foo_config, 
            os.path.expanduser('~/.submitterrc'),
            os.path.abspath(options.configFile)])
        for fname in files_read:
            print "Reading config from", fname
        print config.keys()
        print config.get("qsubOptions",'queue')
    qsubOptions = parseQsubOptions(config,"qsubOptions")
    if options.maxram != "N/A":
        try:
            qsubOptions["maxram"] = float(options.maxram)
        except ValueError as e:
            raise InputError("-m/--maxRam is not a float.")

    if options.queue != "N/A":
        try:
            qsubOptions["queue"] = str(options.queue)
        except ValueError as e:
            raise InputError("-q/--queue is not a str.")

    print qsubOptions
    # for i in range(100):
    #     if i ==1:
    #         continue
    #     copyfile("scripts/1.sh","scripts/%i.sh"%i)
    jobRunning = 0
    submittedJobIds = set()
    currentJobIds = set()
    idScriptMap = {}
    
    try:
        os.mkdir("{0}/batchLogs/".format(options.folder))
    except OSError as e:
        logger.info("Batch log folder exists.")
        # logger.exception(e)

    for script in np.sort(glob(options.folder+"/*")):
        print os.path.basename(script)

        print os.path.join(options.folder, script)
        if not os.path.isfile(os.path.abspath(script)):
            continue
        if os.path.basename(script) == "submitter.log":
            continue
        print script
        qsubOptions["script"] = os.path.abspath(script)
        qsubOptions["jobName"] = "sub_"+os.path.basename(script).split(".")[0]
        qsubOptions["outFile"] = "{0}/batchLogs/{1}.out".format(options.folder,os.path.basename(script))
        qsubOptions["errFile"] = "{0}/batchLogs/{1}.err".format(options.folder,os.path.basename(script))
        command = _build_qsub_command(qsubOptions)
        print command
        output = subprocess.check_output(command.split(" "))
        print "Submitted ",script
        time.sleep(0.5)
        submittedJobIds.add(_parse_qsub_job_id(output))
        currentJobIds.add(_parse_qsub_job_id(output))
        idScriptMap[_parse_qsub_job_id(output)] = script 
        while len(currentJobIds)>= options.jobMax:
            holderList = list(currentJobIds)
            for id in holderList:
                output =_parse_all_job_ids(_get_qstat())
                # print "Checking job ",id
                # print "Current running jobs = ",output
                if id not in output:
                    currentJobIds.remove(id)
                    logger.info("Script "+idScriptMap[id]+" completed.")
                    # print "id ",id," completed"
            time.sleep(5)
    while len(currentJobIds):
        holderList = list(currentJobIds)
        for id in holderList:
            output =_parse_all_job_ids(_get_qstat())
            # print "Checking job ",id
            # print "Current running jobs = ",output
            if id not in output:
                currentJobIds.remove(id)
                logger.info("Script "+idScriptMap[id]+" completed.")
        time.sleep(5)

def parseCommandLine(parser):
    parser.add_option("-I", "--input_folder", dest="folder",
            help="Top level folder for scripts.",default=".", metavar="OUTPUTFOLDER")
    parser.add_option("-N", "--jobMax", dest="jobMax",
            help="Maximum number of jobs this program can submit.",type="int",default=10, metavar="JOBMAX")
    parser.add_option("-q", "--queue", dest="queue",
            help="Queue to sub to.",type="str",default="N/A", metavar="QUEUE")
    parser.add_option("-c", "--configFile", dest="configFile",
            help="Config file.",type="str",default="N/A", metavar="CONFIGFILE")
    parser.add_option("-m", "--maxRam", dest="maxram",
            help="Maximum RAM the job can use.",type="str",default="N/A", metavar="MAXRAM")
    return parser
        
if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parseCommandLine(parser)
    (options, args) = parser.parse_args()
    main(options)
