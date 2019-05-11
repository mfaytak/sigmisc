import audiolabel
import os, sys, subprocess
import re, glob
from numpy import linspace
import shutil
import argparse
import parselmouth

'''
Script to filter and collect CoG data on fricative spectra using Parselmouth.
This script is tailored to extract data from the acoustics of my Suzhou ultrasound corpus.

Usage: python pshf-prep.py [expdir] 
	 expdir: directory containing subdirs which contain acquisition .WAV files.
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
args = parser.parse_args()

# check for appropriate arguments
try:
	expdir = args.expdir
except IndexError:
	print("\tDirectory provided doesn't exist")
	ArgumentParser.print_usage
	ArgumentParser.print_help
	sys.exit(2)

subj = str("S" + re.sub("[^0-9]", "", expdir))
glob_regexp = os.path.join(expdir,"*","*.ch1.wav")

acoustic_file = os.path.join("cogs_out", str(subj + "_cogs.txt"))
with open(acoustic_file,'w') as out:
	out.write("\t".join(["subj","acq","stim","pron","phone","coart_class","round_class","cog","cog075k","cog2k","cog3k","cog4k","cog5k"]) + "\n")

skip_set = ["bolus", "practice", "bite", 
			"BAAE", "AAE", "BUW", "UW", "BIY", "IY", "EU", "FUH", "BUH", "AHR"]
target_list = ['IZ', 'BIZX', 'SIZ', 'XIZ', 
				'SIY', 'XIY',
			   'YZ', 'XYZ', 'XEU', 
			   'SEI', 'SAAE', 'XAE', 
				'SUW', 'XUEQ', 'SOOW',
			   'SIEX', 'XIEX', 'SZ', 'SZW']
iz_list = ['IZ', 'BIZX', 'SIZ', 'XIZ']
target_segments = ['IY1',  'IH1', 'S', 'SH']

no_coart_words = ["IZ", "BIZX", "YZ"]
coart_words = ['SIZ', 'XIZ', 'XYZ']
round_words = ['YZ', 'XYZ', 'XEU', 'SUW', 'XUEQ', "SOOW", "SZW"]

for wave_file in glob.glob(glob_regexp):
	#print(wave_file)
	parent = os.path.dirname(wave_file)
	# skip over other acoustics folders
	if parent.endswith("sauce"):
		#print("Skipping sauce")
		continue
	# skip landmark/practice trials
	stimfile = os.path.join(parent,"stim.txt")
	stim = read_stimfile(stimfile)
	#print(stim)

	if stim in skip_set:
		continue

	# define other files of interest
	acq = os.path.split(parent)[1]
	tg_handle = os.path.join(parent,str(acq + ".ch1.TextGrid"))
	tg = audiolabel.LabelManager(from_file=tg_handle,from_type='praat')

	for f in tg.tier('phone'):
		# skip any target segments not in a word in the target list
		if f.text not in target_segments:
			continue

		# adjust labels to disambiguate
		pron = tg.tier('word').label_at(f.center).text
		if pron in target_list:
			if f.text == "IY1":
				if pron in iz_list: # change if IZ
					f.text = "IZ1"
				elif pron == "YZ" or pron == "XYZ":
					f.text = "YZ1"
				elif pron == "SIEX" or pron == "XIEX":
					continue
			elif f.text == "IH1":
				if pron == "SZ":
					f.text = "ZZ1"
				elif pron == "SZW":
					f.text = "ZW1"
				elif pron == "EU" or pron == "XEU" or pron == "NYEU":
					f.text = "YY1"
		else:
			continue
			
		if f.text not in ["IZ1", "YZ1", "SH", "S", "ZZ1", "ZW1"]:
			continue

		if f.text in ["IZ1", "YZ1"]:
			if pron in no_coart_words:
				coart_class = "no_fric"
			elif pron in coart_words:
				coart_class = "fric"
		else:
			coart_class = "NA"
			
		if pron in round_words:
			round_class = "rounded"
		else:
			round_class = "unrounded"
			
		print(acq, '\t', stim, '\t', 'Analyzing a {}, {}'.format(f.text, coart_class))

		# do the Parselmouth stuff on middle third of selected file
		wv = parselmouth.Sound(wave_file)
		wv = wv.resample(44100)

		thirds = linspace(f.t1, f.t2, 4)
		sub = wv.extract_part(from_time = thirds[1], to_time = thirds[2], preserve_times=True) 
		cog = sub.to_spectrum().get_centre_of_gravity()
		
		filt_075k = parselmouth.praat.call(sub, "Filter (stop Hann band)", 0, 750, 100)
		cog_075k = filt_075k.to_spectrum().get_centre_of_gravity()

		filt_2k = parselmouth.praat.call(sub, "Filter (stop Hann band)", 0, 2000, 100)
		cog_2k = filt_2k.to_spectrum().get_centre_of_gravity()  

		filt_3k = parselmouth.praat.call(sub, "Filter (stop Hann band)", 0, 3000, 100)
		cog_3k = filt_3k.to_spectrum().get_centre_of_gravity()    
		
		filt_4k = parselmouth.praat.call(sub, "Filter (stop Hann band)", 0, 4000, 100)
		cog_4k = filt_4k.to_spectrum().get_centre_of_gravity()        
		
		filt_5k = parselmouth.praat.call(sub, "Filter (stop Hann band)", 0, 5000, 100)
		cog_5k = filt_5k.to_spectrum().get_centre_of_gravity()
		
		# output the data in tabular format
		vals= '\t'.join([str(round(m,4)) for m in [cog, cog_075k, cog_2k, cog_3k, cog_4k, cog_5k]])
		out_row = '\t'.join([subj, acq, stim, pron, f.text, coart_class, round_class, vals])
		# ('before', before),
		# ('after', after),
		with open(acoustic_file, 'a') as out:
			out.write(out_row + '\n')
