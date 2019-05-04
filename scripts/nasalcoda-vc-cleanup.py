
import os, sys, glob, re
import shutil
import argparse
import audiolabel
import parselmouth
import subprocess
from numpy import linspace
from statistics import mean

'''
Extract stimuli for presentation: final VC in target words.
Usage: python nasalcoda-vc-cleanup.py [expdir] [words] [segments] [speaker]
  expdir: directory containing all ultrasound acquisitions for a subject
  words: list of target words, plaintext
  segments: list of target segments, plaintext (including suprasegmentals) 
  speaker: characteristics of the voice for formant extraction: must be:
    male, female, or child
TODO: add vowel argument?
'''

def read_stimfile(stimfile):
	with open(stimfile, "r") as stfile:
		stim = stfile.read().rstrip('\n')
	return stim

def interval_mean(tslice):
	'''Calculate mean of single characteristic (i.e. f0) from an audiolabel tslice of a LabelManager object.'''
	return mean([float(lab.text) for lab in tslice])

# read in command line arguments
parser = argparse.ArgumentParser()
parser.add_argument("expdir", 
					help="Experiment directory containing \
					target acq dirs in flat structure"
					)
parser.add_argument("words",
					help="Plaintext list of target words to be extracted"
					)
parser.add_argument("segments",
					help="Plaintext list of target segments to be extracted"
					)
parser.add_argument("speaker",
					help="Required settings to help with formant extraction"
					)
# TODO make stimulus output optional
args = parser.parse_args()

# check for appropriate arguments
try:
	expdir = args.expdir
except IndexError:
	print("\tDirectory provided doesn't exist")
	ArgumentParser.print_usage
	ArgumentParser.print_help
	sys.exit(2)

with open('stim-extraction-dict.txt', 'r') as mydict:
	wrds = [line.strip().split()[0].lower() for line in mydict.readlines()]
with open('stim-extraction-segments.txt','r') as mysegm:
	segs = [line.strip().split()[0] for line in mysegm.readlines()]
word_regexp = re.compile("^({})$".format('|'.join(wrds)))
seg_regexp = re.compile("^({})$".format('|'.join(segs)))

tempifc = "__temp.ifc"
ifc_args = ['ifcformant',
		   '--speaker=' + args.speaker,
		   '-e', 'gain -n -3 sinc -t 10 60 contrast',
		   '-p %0.5f',
		   '--print-header',
		   '--output=' + tempifc]

with open(args.words, 'r') as mydict:
	wrds = [line.strip().split()[0].lower() for line in mydict.readlines()]
with open(args.segments,'r') as mysegm:
	segs = [line.strip().split()[0] for line in mysegm.readlines()]
word_regexp = re.compile("^({})$".format('|'.join(wrds)))
seg_regexp = re.compile("^({})$".format('|'.join(segs)))

# regular expression to locate .wav files
glob_regexp = os.path.join(expdir,"*","*","*.ch1.wav")

# output the header to the formants file
subj = re.sub("[^0-9]", "", expdir)
acoustic_file = os.path.join(expdir, str(subj + "_formants.txt"))
with open(acoustic_file,'w') as out:
	out.write("\t".join(["subj","acq","stim","vowel","nasal","midF1","endF1","midF2","endF2","midF3","endF3"]) + "\n")

for wave_file in glob.glob(glob_regexp):
	parent = os.path.dirname(wave_file)
	condition = os.path.dirname(parent)
	# skip landmark/practice trials
	stimfile = os.path.join(parent,"stim.txt") # this is lower-case
	stim = read_stimfile(stimfile).upper() # makes it upper-case

	if stim.lower() not in wrds:
		continue
	
	# define other files of interest
	acq = os.path.split(parent)[1]
	tg_handle = os.path.join(parent,str(acq + ".ch1.TextGrid"))
	tg = audiolabel.LabelManager(from_file=tg_handle,from_type='praat')

	sound = parselmouth.Sound(wave_file)
	matches = tg.tier('words').search(word_regexp)
	if len(matches) > 1:
		print("Multiple tokens of {} in {}, skipping!".format(stim, acq))
		continue
	
	match = matches[0] # take first item (only item) from the match list
	
	labels = tg.tier('phones').tslice(t1=match.t1,t2=match.t2)
	# remove intervals surrounding word, which are included in tslice
	phones = labels[1:-1]
	# get last two intervals and check
	vc = phones[-2:]
	if vc[0].text not in ['i1','i2','i3','i4','i5']:
		print("{} {}: Final interval is not [i]; skipping!".format(acq, stim))
		continue
	if vc[1].text not in ['n','ng']:
		print("{} {}: Final interval is not a nasal; skipping!".format(acq, stim))
		continue

	print("Now working on {} {}".format(stim,acq))
	start = vc[0].t1
	vowel_end = vc[0].t2
	end = vc[1].t2
	
	# extract the content of the two intervals and scale intensity
	sub = sound.extract_part(from_time = start, to_time = end)
	sub.scale_intensity(70.)
	
	# save the sound file as a stimulus file
	out_handle = "_".join([subj,stim,acq]) + ".wav"
	out_path = os.path.join(condition, out_handle)
	sub.save(out_path, "WAV")
	
	# get IFC object from start to VOWEL's end
	proc = subprocess.Popen(ifc_args + [out_path])
	proc.wait()
	if proc.returncode != 0:
		for line in proc.stderr:
			sys.stderr.write(line + '\n')
		raise Exception("ifcformant exited with status: {0}".format(proc.returncode))
	ifc = audiolabel.LabelManager(from_file=tempifc, from_type='table', t1_col='sec')

	# get thirds of the elapsed time in the vowel
	thirds = linspace(start, vowel_end, 4)
	thirds = [t - start for t in thirds] # set so starts at zero
	
	# get all IFC samples between the timepoints thirds[1] and thirds[2] = middle third
	mid_third_f1 = ifc.tier('f1').tslice(t1=thirds[1], t2=thirds[2])
	midF1 = interval_mean(mid_third_f1)
	mid_third_f2 = ifc.tier('f2').tslice(t1=thirds[1], t2=thirds[2])
	midF2 = interval_mean(mid_third_f2)
	mid_third_f3 = ifc.tier('f3').tslice(t1=thirds[1], t2=thirds[2])
	midF3 = interval_mean(mid_third_f3)
	# get all IFC samples between the timepoints thirds[2] and thirds[3] = last third
	end_third_f1 = ifc.tier('f1').tslice(t1=thirds[2], t2=thirds[3])
	endF1 = interval_mean(end_third_f1)
	end_third_f2 = ifc.tier('f2').tslice(t1=thirds[2], t2=thirds[3])
	endF2 = interval_mean(end_third_f2)
	end_third_f3 = ifc.tier('f3').tslice(t1=thirds[2], t2=thirds[3])
	endF3 = interval_mean(end_third_f3)

	# output the data in tabular format
	formant_vals= '\t'.join([str(round(m,4)) for m in [midF1,endF1,midF2,endF2,midF3,endF3]])
	out_row = '\t'.join([subj, acq, stim, vc[0].text, vc[1].text, formant_vals])
	with open(acoustic_file, 'a') as out:
		out.write(out_row + '\n')
