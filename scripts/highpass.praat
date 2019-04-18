# Extracts mean formant values, H1, H2, and spectral tilt measures
# dynamically across an duration defined by the textgrid. 
# The number of interval values extracted is equal to numintervals below.
# Writes results to a textfile.
# Christian DiCanio, 2007 - revised 2008 to include output amplitude values.
# Revised in 2012 to work iteratively across a directory.
# Modified again in 2017 and 2018 by Matt Faytak to add high-pass filter and
# calculate intensity and harmonicity (HNR).

form Extract Formant data from labelled points
	sentence Directory_name: SUZHOU_40_FA\sauce\
	positive Phone_tier_number 1
	positive Word_tier_number 2
	sentence Interval_label_1 IY1
	sentence Interval_label_2 IZ1
	sentence Interval_label_3 YY1
	sentence Interval_label_4 YZ1
	sentence Interval_label_5 S
	sentence Interval_label_6 SH
	sentence Interval_label_7 ZZ1
	sentence Interval_label_8 ZW1
	comment Filter settings
	positive Low_pass 4500
	positive Smoothing 50
	comment Intensity settings
	positive Minimum_pitch 100
	positive Analysis_points_time_step 0.005
   	sentence Log_file _out
endform

numintervals = 7
#Number of intervals you wish to extract information from.

# set up header
fileappend 'directory_name$''log_file$'.txt subj'tab$'file'tab$'label'tab$'word'tab$'
for i to numintervals
 	fileappend 'directory_name$''log_file$'.txt int'i''tab$'
endfor
fileappend 'directory_name$''log_file$'.txt 'newline$'

# Here, you make a listing of all the sound files in a directory.

Create Strings as file list... list 'directory_name$'\*.wav
num = Get number of strings

for ifile to num
	select Strings list
	filename$ = Get string... ifile
	Read from file... 'directory_name$''filename$'
	# Resample to 16 kHz
	soundID1$ = selected$("Sound")
	dot_tg_path$ = replace$ (soundID1$, "_ch1", ".ch1", 1)
	# Resample... 16000 50
	# high-pass filter
	Filter (stop Hann band)... 0 low_pass smoothing
	soundID2 = selected("Sound")
	Read from file... 'directory_name$'/'dot_tg_path$'.TextGrid
	textGridID = selected("TextGrid")
	num_labels = Get number of intervals... phone_tier_number

# fileappend 'directory_name$''log_file$'.txt 

# iterate over all intervals in phone tier; check if they contain desired segment
for i to num_labels
	select 'textGridID'
	label$ = Get label of interval... phone_tier_number i
		if label$ = interval_label_1$ or label$ = interval_label_2$ or label$ = interval_label_3$ or label$ = interval_label_4$ or label$ = interval_label_5$ or label$ = interval_label_6$ or label$ = interval_label_7$ or label$ = interval_label_8$
      		intvl_start = Get starting point... phone_tier_number i
			intvl_end = Get end point... phone_tier_number i
			phone_center = (intvl_start + intvl_end)/2
			word_interval = Get interval at time... word_tier_number phone_center
			word_label$ = Get label of interval... word_tier_number word_interval
			fileappend 'directory_name$''log_file$'.txt 'directory_name$''tab$''filename$''tab$''label$''tab$''word_label$'
			select 'soundID2'
			Extract part... intvl_start intvl_end Rectangular 1 no
			intID = selected("Sound")	
			To Intensity... 'minimum_pitch' 'analysis_points_time_step' no
			invl_int = selected("Intensity")

			# go through numintervals chunks of the selected sound
			chunkID  = (intvl_end-intvl_start)/numintervals
			for j to numintervals
				hnr = Get mean... (j-1)*chunkID j*chunkID
				if j = numintervals
					fileappend 'directory_name$''log_file$'.txt
 	           			... 'tab$''hnr''newline$'
				else
					fileappend 'directory_name$''log_file$'.txt
   	         			... 'tab$''hnr'
					endif

			endfor
			
		select 'intID'
		Remove

		select 'invl_int'
		Remove

		else
			# do nothing

   		endif

endfor
endfor
select all
Remove