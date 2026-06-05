Tension-TRAAKer

Overview: 
  
  This folder includes scripts to mask membranes (channel 2 when 2 or more channels exist) and calculate fluorescence changes in   those membranes (as channel 1/channel 2 when 2 or more channels exist). Scripts are heavily annotated; outputs are summarized in the Script Outputs.xlsx.
  
  Briefly: 

  membraneworkup.py can be used to mask a cell and serially crop it to the outermost plasma membrane. The mask is built from data in channel 2 of a 2 channel tif; fluorescence is reported for both channels within this mask. This script outputs total fluorescence for the cell mask, the membrane mask, the membrane, and the thresholded membrane of a cell. This script iterates across all tifs in an input folder with subfolders tifs, pngs, and results. Each tif file should include a fluorescent cell or patch of cells with bright plasma membrane(s) and minimal external debris.

  cellworkup.py is a truncated version of membraneworkup.py, and can be used to mask a cell using data in channel 2 of a 2 channel tif; fluorescence is then reported for both channels within this mask. This script iterates across all tifs in an input folder with subfolders tifs, pngs, and results. Each tif file should include a fluorescent cell or patch of cells with bright plasma membrane(s) and minimal external debris.

  patchworkup.py can be used to mask excised cell patches (single channel tifs) according to membrane brightness. Within the masked membrane, the membrane midpoint is determined for each of n brightest rows and fit to a circle (https://pypi.org/project/circle-fit/) to determine the radius of curvature of the patch. Total fluorescence is also reported for each masked membrane. This script iterates across all tifs in an input folder with subfolders tifs and results. Each tif file should include a fluorescent patch of membrane that has been oriented vertically with no visible debris (i.e., the membrane extends from the top of the image to the bottom). The script is agnostic to the direction of membrane curvature. 

  pokeworkup.py can be used to mask cell membranes in cropped cells according to the data in channel 2 of a 3 channel tif; fluorescence is reported for channels 1 and 2 within this mask. This script outputs both total fluorescence for the cell membrane, and channel 1/channel 2 fluorescence for each row of the cell membrane. The latter data can be used to build a spatially precise kymograph describing membrane fluorescence change through time. This script iterates across all tifs in an input folder with subfolders tifs and results. Each tif file should include a fluorescent patch of membrane that has been oriented vertically with no visible debris (i.e., the membrane extends from the top of the image to the bottom). 
  
  For the membraneworkup, cellworkup, and patchworkup scripts, several values are left to the user’s discretion, e.g., the threshold for masking the cell, the close kernel for said mask, and the erosion value for locating and centering the cell membrane. These values are chosen iteratively by the user, with pause points automated to allow for mask visualization and subsequent value edits. Recommended values are included in the script; depending on the homogeneity of the user's data, these values can be hard coded. 

System requirements: 
  Hardware: a standard desktop or laptop computer. Higher RAM improves runtime, particularly of the membraneworkup.py script. 
  Software: This package has been tested on macOS: Sonoma 14.6.1 running Python 3.12.5. It depends primarily on python stacks: csv, numpy, scipy, imageio, PIL, skimage, and circle_fit. Specific required stacks are listed at the top of each script.

Installation guide (minutes, depending on how many of the requisite python stacks you already have installed): 
  1. Download desired script and associated demo folder.
  2. Confirm that the demo folder comprises the subfolders described above, with three .tifs in the tifs subfolder.
  3. Access your desired enviroment in Terminal. To create a new conda environment for the management of dependencies:
        conda create --name
        conda activate name
        conda install pip
  4. Confirm that all packages described in lines 1–34 of the downloaded script are installed in your environment. If one or more are not:
        pip install numpy pandas scipy imageio #[... et al]
  7. Load and run the script in Terminal, e.g.:
        cd .../
        python membraneworkup.py
  8. Follow instructions as they appear.
  9. Check the results folder for output files. These are: a results file, with all parameters calculated by the script (see the Script Outputs.xlsx for specifics); several folders of masked images labelled according to .tif name and image category. These folders and their contents are explicitly described in the annotations/comments within each script.
  10. Modify the script as desired.
     In all scripts, certain parameters have been hard coded and others left to user discretion. Code has been commented out next to all hard coded parameters; re-insertion will enable greater user control. Conversely, for homogenous data, all user input parameters can be changed to integers to reduce user interaction and improve run time.
     Similarly, several methods to identify the plasma membrane are provided in the membraneworkup script, all of which have been commented out except for the one applied to the Tension TRAAKer construct screen. The pros and cons of these methods are described in the script annotations; sub in/out according to your data workup needs.

License: GNU General Public License v3.0



