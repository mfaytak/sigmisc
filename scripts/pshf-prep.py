import audiolabel
import os, sys, subprocess
import re, glob
import numpy as np
import shutil
import argparse

'''
Script to prep data for Pitch-Scaled Harmonic Filter (PSHF). Produces f0 estimates for acoustic data.
Also finds files in any number of subdirectories (i.e., acquisition subdirectories in an experiment 
directory) and moves TextGrid and audio files (along with f0 estimates) into a single directory with 
a flat structure. This directory should then be moved into the unzipped PSHF directory. Finally, a shell
script is produced as an output which can be run in the PSHF directory to quickly process all moved files,
and the input and output dirs are created as well.

The PSHF can be downloaded from http://personal.ee.surrey.ac.uk/Personal/P.Jackson/PSHF/download.html. I 
did not create the PSHF, which is described in detail in:

    PJB Jackson, CH Shadle. "Pitch-scaled estimation of simultaneous voiced and turbulence-noise components in speech". 
      IEEE Transactions on Speech and Audio Processing, 9 (7): 713-726, Oct 2001. 
      
Usage: python pshf-prep.py [expdir] [--speaker -s male|female|child]
     expdir: directory containing subdirs which contain acquisition .WAV files.
     speaker: voice information for pitch estimation.
'''

def read_stimfile(stimfile):
    with open(stimfile, "r") as stfile:
        stim = stfile.read().rstrip('\n')
    return stim

# read in command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("expdir", 
                    help="Experiment directory containing \
                    acquisitions in flat structure"
                    )
parser.add_argument("speaker",
					help="Voice information for pitch estimation"
					)
args = parser.parse_args()

# check for appropriate arguments
try:
    expdir = args.expdir
except IndexError:
    print("\tDirectory provided doesn't exist")
    ArgumentParser.print_usage
    ArgumentParser.print_help
    sys.exit(2)

try:
    if not (args.speaker == 'male' or
            args.speaker == 'female' or
            args.speaker == 'child'): raise
    args.speaker != None
except:
    raise Exception('Speaker label must be male, female, or child')

tempifc = "__temp.ifc"
ifc_args = ['ifcformant',
           '--speaker=' + args.speaker,
           '-e', 'gain -n -3 sinc -t 10 60 contrast',
           '-p %0.5f',
           '--print-header',
           '--output=' + tempifc]

# make output dir (over-writes if it already exists)
pshf_dir = str(expdir + '_pshf_in')
try:
    os.mkdir(pshf_dir)
except FileExistsError:
    shutil.rmtree(pshf_dir)
    os.mkdir(pshf_dir)

pshf_out = str(expdir + '_pshf_out')
try:
    os.mkdir(pshf_out)
except FileExistsError:
    shutil.rmtree(pshf_out)
    os.mkdir(pshf_out)
    
script = str(expdir + '_pshf.cmd')

# regular expression to locate .wav files
glob_regexp = os.path.join(expdir,"*","*.ch1.wav")

skip_set = ["bolus", "practice", "bite", 
			"BAAE", "AAE", "BUW", "UW", "BIY", "IY", "EU", "FUH", "BUH", "AHR"]

# loop through available .raw files
for wav in glob.glob(glob_regexp):
    parent = os.path.dirname(wav)
    # skip landmark/practice trials
    stimfile = os.path.join(parent,"stim.txt")
    stim = read_stimfile(stimfile)
    if stim == "bolus" or stim == "practice" or stim == "bite":
        continue

    # define other files of interest
    acq = os.path.split(parent)[1]
    f0_file = os.path.join(parent, str(acq + '.f0'))
    tg = os.path.join(parent,str(acq + ".ch1.TextGrid"))

    # open the .f0 output file and...
    with open(f0_file, 'w') as out:

        # run IFCFormant on raw file
        proc = subprocess.Popen(ifc_args + [wav])
        proc.wait()
        if proc.returncode != 0:
            for line in proc.stderr:
                sys.stderr.write(line + '\n')
            raise Exception("ifcformant exited with status: {0}".format(proc.returncode))
        ifc = audiolabel.LabelManager(from_file=tempifc, from_type='table', t1_col='sec')
    
        # write all f0 samples in f0 'tier' to .f0 file
        for lab in ifc.tier('f0')[:]:
            #print(lab.text)
            if float(lab.text) == 0.:
                out.write('0\n')
            else:
                out.write(lab.text+'\n')
            # for testing, can also write t1 of sample window
            #out.write(str(lab.t1) + '\t' + lab.text + '\n')

    # copy files over
    shutil.copy(f0_file,pshf_dir)
    shutil.copy(wav,pshf_dir)
    shutil.copy(tg,pshf_out) # note: TGs are copied to the OUT directory, to use with outputs.
    
    # write the PSHF run command for this acq to the .cmd file
    with open(script,'a') as out:
        out.write(" ".join([
                    ".\pshf.exe", "-d 6",
                    "\\".join([pshf_dir, os.path.split(f0_file)[1]]), 
                    "\\".join([pshf_dir, os.path.split(wav)[1]]), 
                    '\\'.join([pshf_out, acq])
                    ])
                 )
        out.write('\n')