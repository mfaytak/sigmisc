import audiolabel
import os, sys, subprocess
import re, glob
import numpy as np
import shutil
import argparse
import parselmouth

'''
Script to prep data for Pitch-Scaled Harmonic Filter (PSHF). Produces f0 estimates for acoustic data.
Also finds files in any number of subdirectories (i.e., acquisition subdirectories in an experiment 
directory) and moves TextGrid and audio files (along with f0 estimates) into a series of directories
sorted by type. Finally, a shell script is produced as an output which can be run on the containing
directory to quickly process all the files.

This script is tailored to extract data from the acoustics of my Suzhou ultrasound corpus.

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
target_list = ['IZ', 'BIZX', 'SIZ', 'XIZ', 
                'SIY', 'XIY',
               'YZ', 'XYZ', 'XEU', 
               'SEI', 'SAAE', 'XAE', 
                'SUW', 'XUEQ', 'SOOW',
               'SIEX', 'XIEX', 'SZ', 'SZW']

iz_list = ['IZ', 'BIZX', 'SIZ', 'XIZ']

target_segments = ['IZ1', 'YZ1', 'S', 'SH', 'ZZ1', 'ZW1']

for seg in target_segments:
    seg_in_folder = os.path.join(pshf_dir, str(seg + '_in'))
    try:
        os.mkdir(seg_in_folder)
    except FileExistsError:
        shutil.rmtree(seg_in_folder)
        os.mkdir(seg_in_folder)
    seg_out_folder = os.path.join(pshf_dir, str(seg + '_out'))
    try:
        os.mkdir(seg_out_folder)
    except FileExistsError:
        shutil.rmtree(seg_out_folder)
        os.mkdir(seg_out_folder)  


# loop through available .raw files
for wave_file in glob.glob(glob_regexp):
    parent = os.path.dirname(wave_file)
    # skip landmark/practice trials
    stimfile = os.path.join(parent,"stim.txt")
    stim = read_stimfile(stimfile)

    # TODO: this block might allow you to simplify below loops
    if stim in skip_set:
        continue

    # define other files of interest
    acq = os.path.split(parent)[1]
    tg_handle = os.path.join(parent,str(acq + ".ch1.TextGrid"))
    tg = audiolabel.LabelManager(from_file=tg_handle,from_type='praat')

    # remove irrelevant labels
    for f in tg.tier('phone'):
        # blank silent intervals
        if f.text == "sp" or f.text == "sil":
            f.text = ""
            continue

        # remove any segments not in a word in the target list
        pron = tg.tier('word').label_at(f.center).text
        if pron not in target_list:
            f.text = ""
        else:
            # ...get phone label, disambiguating IY, IH based on word
            if f.text == "IY1":
                if pron in iz_list: # change if IZ
                    f.text = "IZ1"
                elif pron == "YZ" or pron == "XYZ":
                    f.text = "YZ1"
                elif pron == "SIEX" or pron == "XIEX":
                    f.text = ""
            elif f.text == "IH1":
                if pron == "SZ":
                    f.text = "ZZ1"
                elif pron == "SZW":
                    f.text = "ZW1"
                elif pron == "EU" or pron == "XEU" or pron == "NYEU":
                    f.text = "YY1"
                    
        if f.text not in target_segments:
            f.text == ""
            continue
        
        print(acq, '\t', stim, '\t', 'Retained a {}'.format(f.text))

    # trim files with parselmouth
    name = os.path.splitext((os.path.basename(wave_file)))[0]
    sound = parselmouth.Sound(wave_file)
    # TODO stop-band filter sound? [sound], 0, 4000, 100
    matches = tg.tier('phone').search("[^()]")
    for match in matches:
        i += 1
        if match.text not in target_segments:
            continue
            
        # extract section of wav file and save
        sub = sound.extract_part(from_time = match.t1, to_time = match.t2)    
        # TODO change save location to pshf_in
        sub_handle = os.path.join(parent, str(acq + "_" + str(i) + ".wav"))
        sub.save(sub_handle, 'WAV')
        
        sub_acq = os.path.splitext(os.path.split(sub_handle)[1])[0]
        
        f0_file = os.path.join(parent, str(sub_acq + '.f0'))
        # open the .f0 output file and...
        with open(f0_file, 'w') as out:
            # run IFCFormant on split files
            proc = subprocess.Popen(ifc_args + [sub_handle])
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
        
        # define dirs
        seg_in_folder = os.path.join(pshf_dir, str(match.text + '_in'))
        seg_out_folder = os.path.join(pshf_dir, str(match.text + '_out'))
        
        # copy files over
        shutil.copy(f0_file, seg_in_folder)
        shutil.copy(sub_handle, seg_in_folder)
        shutil.copy(tg_handle, seg_out_folder) # note: TGs are copied to the OUT directory, to use with outputs.
        print("Sending {} to {}".format(match.text, seg_in_folder))
        
        # write the PSHF run command for this acq to the .cmd file
        with open(script,'a') as out:
            out.write(" ".join([
                        ".\pshf_3.13_win32\pshf.exe", "-d 2", 
                        "\\".join([seg_in_folder, os.path.split(f0_file)[1]]), 
                        "\\".join([seg_in_folder, os.path.split(sub_handle)[1]]), 
                        '\\'.join([seg_out_folder, sub_acq])
                        ])
                     )
            out.write('\n')
