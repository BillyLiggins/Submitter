#!/usr/bin/env python
# -*- coding: utf-8 -*-

import subprocess
from glob import glob
from os.path import basename, abspath
from shutil import copyfile
import time
import os

'''
Outline of program:
    You would love to give a command line option that 

    You give a
        - Folder containing all submittable scripts.
        - maximum number of jobs the program will be allowed to submit. 
        - ???

'''

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


def _build_qsub_command(job_name, outfile, errfile, que, script):
    """Submit shell command to SGE queue via `qsub`"""
    qsub_template = """qsub -o {outfile} -e {errfile} -q {que} -N {job_name} {script}"""
    return qsub_template.format(
            job_name=job_name, outfile=outfile, errfile=errfile,que = que, script= script)

def _build_qsub_command(job_name,  que, script):
    """Submit shell command to SGE queue via `qsub`"""
    qsub_template = """qsub -cwd -q {que} -N {job_name} {script}"""
    return qsub_template.format(
            job_name=job_name,que = que, script= script)

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


command = "qstat -u liggins"

def main(options):
    """
    :returns: TODO

    """
    
    if int(os.uname()[1].split(".")[0][5:]) not in range(400,408):
        print "Run on heppc400-407"
        return
    # for i in range(100):
    #     if i ==1:
    #         continue
    #     copyfile("scripts/1.sh","scripts/%i.sh"%i)
    jobRunning = 0
    submittedJobIds = set()
    currentJobIds = set()
    
    for script in glob(options.folder+"/*"):
        print script
        try:
            os.mkdir("{0}/batchLogs/".format(options.folder))
        except OSError as e:
            print "Batch log folder exists."
        # jobName = "{}".format(script)
        jobName = "job"
        outFile = "{0}/batchLogs/{1}.out".format(options.folder,script)
        errFile = "{0}/batchLogs/{1}.err".format(options.folder,script)
        # command = _build_qsub_command(jobName, outFile,errFile,"snoplusSL6",abspath(script))
        command = _build_qsub_command(jobName,"snoplusSL6",abspath(script))
        output = subprocess.check_output(command.split(" "))
        print "Submitted ",script
        time.sleep(0.5)
        submittedJobIds.add(_parse_qsub_job_id(output))
        currentJobIds.add(_parse_qsub_job_id(output))
        while len(currentJobIds)>= options.jobMax:
            print "Waiting"
            holderList = list(currentJobIds)
            for id in holderList:
                output =_parse_all_job_ids(_get_qstat())
                print "Checking job ",id
                print "Current running jobs = ",output
                if id not in output:
                    currentJobIds.remove(id)
                    print "id ",id," completed"
            time.sleep(5)

        
if __name__ == "__main__":
    from optparse import OptionParser
    parser = OptionParser()
    parser.add_option("-I", "--input_folder", dest="folder",
            help="Top level folder for scripts.",default=".", metavar="OUTPUTFOLDER")
    parser.add_option("-N", "--jobMax", dest="jobMax",
            help="Maximum number of jobs this program can submit.",type="int",default=10, metavar="JOBMAX")
    (options, args) = parser.parse_args()
    main(options)
