import circle_fit
from circle_fit import taubinSVD
import os 
import fnmatch                                                                                           
import csv    
import xlsxwriter                                                                                       
import os.path                                                                                       
import matplotlib.pyplot as plt
import pandas as pd                                                                      
import numpy as np   
from numpy import asarray
import cv2                                                                                
from scipy import linalg                       
import imageio
from imageio import imread
from scipy.optimize import curve_fit
from itertools import zip_longest #load stuff
import statistics
import traceback
import sys
from pathlib import Path
from PIL import Image, ImageSequence
import png
from matplotlib import colormaps
import ast
import skimage as skimage
from skimage.draw import line
from skimage.morphology import dilation		
from skimage.morphology import disk		
from skimage.morphology import erosion		
from skimage.morphology import remove_small_objects		
from skimage.morphology import closing		
import math

##SETUP##

message = '*** You will be prompted to input file paths with this script, please read the prompts for each file location to ensure the script runs correctly. Note that membranes should stretch toward the left side of your images for truncated radii calculations to be correct.***'
print("\n\n", message, "\n\n") 

#Where are your files?
path = input("Where are your files (folder with subfolders tifs and results)? include the final /: ")

#Printing the pathways & setting pathways
dir_path = os.path.join(path, "tifs/")
print("\n", "Your tif files have been found here:", dir_path, "\n")
save_path = os.path.join(path, "results/")
print("\n", "Your results can be found here:", save_path, "\n")

#Window_size is the width of your membrane in pixels. 
window_size = 4    				###int(input("\n\nHow many pixels wide is your membrane?: "))
KeepPlots = "True"
VisualizeNumber = "0003"		#Pick a file to visualize to check your membrane fit.
VisualizeFile = VisualizeNumber + ".png"

#Creating a results file.
header = ('File', 'Frame', 'Sum Red', 'Sum Green', 'R/G', 'Mask Area', 'Membrane Length', 'Sigma', 'Radius')
resultsfile1 = save_path +'Results.csv'
f = open(resultsfile1, 'w')
# create the csv writer
writer = csv.writer(f)
# Writing header
writer.writerow(header)
f.close()

os.chdir(dir_path)
for filename in os.listdir(dir_path):
	f = os.path.join(dir_path, filename)
	if fnmatch.fnmatch(filename, '*.tif'):
		print(filename)

		#Create your image folders.
		#This folder will comprise your channel 2 (green) masked membrane.
		os.chdir(save_path)
		GreenPath = save_path + filename + "_Green"
		Path(GreenPath).mkdir(parents=True, exist_ok=True)

		#This folder will comprise your channel 1 (red) masked membrane.
		os.chdir(save_path)
		RedPath = save_path + filename + "_Red"
		Path(RedPath).mkdir(parents=True, exist_ok=True)

		#This folder will comprise the data describing sum(red)/sum(green) for each row of your masked membrane.
		os.chdir(save_path)
		MathPath = save_path + filename + "_Math"
		Path(MathPath).mkdir(parents=True, exist_ok=True)

		#This folder will include only pixels used in the radii calculation--i.e. in each of the chosen number of brightest rows, the midpoint pixel of the sum(n) brightest pixels in that row, where n = window_size.
		os.chdir(save_path)   
		RadiiPath = save_path + filename + "_Radii"   
		Path(RadiiPath).mkdir(parents=True, exist_ok=True)   

		#Count the number of frames. The input data for this script has 3 channels: 1, red; 2, green; 3, transmission. 
		file_number_list = []
		im = Image.open(f)
		for i, page in enumerate(ImageSequence.Iterator(im)):
			if i % 3 == 0:
				g = i // 3
				file_number_list.append(g)
			else:
				continue 
		file_number_final = max(file_number_list)
		print(file_number_final)

		ret, images_test = cv2.imreadmulti(f,[],-1)   
		img_test = images_test[int(file_number_final-1)]   
		plt.imshow(img_test)   
		plt.show()   

		#Choose the number of leftmost rows that will appear in your radii calculation.
		#This number matters if your tif includes membrane outside of the curved patch whose tension you're trying to calculate. 
		#Choose the largest number of rows that reasonably tracks your membrane. 
		#Note that membrane tracking will be more difficult at high pressures, as total fluorescence has been diluted across a larger membrane area.
		#If your membrane becomes dimmer than unwanted intracellular fluorescence, turn on the script break in lines 206-207 to avoid fitting noise.
		
		MembraneLength = int(input("How many rows tall is the membrane you would like to fit a circle to? Underestimate to only fit the patch apex. Only the n leftmost rows of membrane will be fit: "))   

		#Work up each cell. g is the number of frames.
		ret, images_expt = cv2.imreadmulti(f,[],-1)
		for g in range(file_number_final+1):
			text_name = f"{g:04d}"
			file_name = text_name + ".png"
			green_index = int(g*3+1)
			red_index = int(g*3)

			img = images_expt[green_index]
			data = np.asarray(img)
			shape = data.shape
			xlim = shape[1]
			ylim = shape[0]
			###MembraneLength = ylim			#Swap this for MembraneLength above if you'd like to fit each tif top to bottom for the radius workup.

			imgred = images_expt[red_index]
			datared = np.asarray(imgred)
			shapered = datared.shape
			xlimred = shapered[1]
			ylimred = shapered[0]

			#Define your variables and lists. 
			CoordM = []
			CoordR = []

			Col_List = []   
			Radius_Coordinates = []   
			radius_row_list = []   
			radius_y = []   
			radius_x = []   
			radius_d = []   

			Row_List = []
			Green_List = []
			Red_List = []

			mask_y = []
			mask_x = []
			mask_d = []
			mask_e = []


			#Identify each row as a line of points.
			for row_index in range(ylim):
				row = data[row_index]
				rowred = datared[row_index]

				Line_y = []
				Line_x = [] 
				Line_val = []
				Line_redval = []

				for column_index in range(xlim):
					Line_y.append(int(row_index))										
					Line_x.append(int(column_index))									
					Line_val.append(int(row[column_index]))
					Line_redval.append(int(rowred[column_index]))								
				dfLine = np.array([Line_y, Line_x, Line_val])
				dfLinered = np.array([Line_y, Line_x, Line_redval])

			#Find n brightest adjacent green pixels in each line.
				highest_average = float('-inf')

				num_iterations = len(Line_y) - window_size + 1

				for a in range(num_iterations):
					values = dfLine[2][a:a+window_size]
					average = values.mean()

					nearest_values = dfLine[2][a+1:a+window_size+1]			
					nearest_average = nearest_values.mean()					#This determines whether the next iteration will have a higher average than the current one.

					outside = dfLine[2][0:4]						
					outside_average = outside.mean()						#This assigns an average extracellular green background value. Chosen as the first n pixels in each row.

					if average > highest_average:
						highest_average = average  							#This is the average green value of the brightest n adjacent pixels.

						pass
						
						highest_values = dfLine[2][a:a+window_size]			#These are the values of the brightest n adjacent green pixels.
						highest_valuesred = dfLinered[2][a:a+window_size]	#These are the red values of those pixels.
						highest_averagered = highest_valuesred.mean()		#This is the average red value of those pixels.

						highest_value_rows = dfLine[0][a:a+window_size]		
						highest_value_cols = dfLine[1][a:a+window_size]
						first_col = dfLine[1][a]                        	#This chooses the first column in each row of brightest n adjacent pixels; it's going to be used to exclude rows outside of the patch apex from the radii calculation.
						middle_col = dfLine[1][int(a+(window_size/2))]		#This chooses the middle column in ach row of brightest n adjacent pixels; it's the "center" of the membrane.

						###if average > nearest_average and average > 10*outside_average: 	#This halts the search for the brightest n adjacent pixels at the first local maximum above a given threshold (here 10x background).
							###break   														#Put this back if your membrane has significant intracellular noise. Note that your cell needs to be oriented extracellular-->intracellular for this to improve membrane fit.  

				High_Values = list(highest_values)					#These are the pixel values of the brightest n adjacent green pixels in your line.
				High_ValuesRed = list(highest_valuesred)			#These are the red pixel values of the same pixels as chosen above.
				High_Rows = list(highest_value_rows)				#These are the y coordinates of the brightest n adjacent pixels in your line.
				High_Columns = list(highest_value_cols)				#These are the x coordinates of the brightest n adjacent pixels in your line.

				for y,x in zip(High_Rows,High_Columns):				#These are the pixel coordinates of all the brightest points in every line.
					if [int(y),int(x)] not in CoordM:
						CoordM.append([int(y),int(x)]) 

				CoordR.append([int(row_index),int(middle_col)])		#This is the coordinate of the midpoint of each row of n brightest adjacent pixels.
				Row_List.append(row_index)
				Green_List.append(int(highest_average))				#This is a list of the average green (channel 2) value of each row of n brightest adjacent pixels.
				Red_List.append(int(highest_averagered))			#This is a list of the average red (channel 1) value of the same pixels.
				Col_List.append([first_col, row_index])		    	#This is the first (leftmost) pixel in each row of n brightest adjacent pixels. Sub first_col for highest_average if you want to choose radii workup points by brightness. Change False to True in line 232.

			#Fill lists describing your masked membrane (comprising the n brightest adjacent pixels in each row, chosen from the green channel (2)).
			for [y,x] in CoordM: 
				mask_y.append(y)
				mask_x.append(x)
				mask_d.append(int(data[y][x]))
				mask_e.append(int(datared[y][x]))

			#Crop your image to the #MembraneLength leftmost rows of bright pixels to more accurately approximate the radii of the patch apex.
			Col_List.sort(reverse=False) 
			for [a, y] in Col_List[0:MembraneLength]:   
				radius_row_list.append(y)							

			#Fill lists describing the pixels used for membrane radii calculations.  
			for [y,x] in CoordR: 	  
				if y in radius_row_list:  
					radius_y.append(y)   
					radius_x.append(x)   
					radius_d.append(int(data[y][x]))   

			#Create a list of the pixels used for membrane radii calculations.  
			for y,x in zip(radius_y,radius_x):   
				Radius_Coordinates.append([x,y])   

			#Math out membrane and background brightness data. 	
			sum_green = sum(mask_d)								#This is the total green (channel 2) fluorescence in the masked membrane.
			sum_red = sum(mask_e)								#This is the total red (channel 1) fluorescence in the masked membrane.
			mask_area = len(mask_d)								#This is the total number of pixels in the masked membrane.

			#Create an array for the green membrane (channel 2).
			green_mask = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,m in zip(mask_y, mask_x, mask_d):
				green_mask[d][e] = m

			#Create an array for the red membrane (channel 1).
			red_mask = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,n in zip(mask_y, mask_x, mask_e):
				red_mask[d][e] = n

			#Create an array for a kymograph. 
			#Each column is a frame of the input tif, with column number = frame.
			#Each row within a column is sum(red)/sum(green) for the corresponding row of masked pixels in that frame.
			#This sum(red)/sum(green) value is multiplied by 1000 for ease of visualization in a 16-bit image.
			math_mask = np.zeros([ylim,file_number_final+1], dtype=np.uint16)		
			for d,e,l in zip(Row_List, Green_List, Red_List):
				math_mask[d][g] = int(l * 1000 / e)

			#Create an array for the membrane midpoints used for radii caluclations.  
			radius_mask = np.zeros([ylim,xlim], dtype=np.uint16)		 
			for d,e,r in zip(radius_y, radius_x, radius_d):  
				radius_mask[d][e] = r   

			try:
				#Calculate the curvature of the membrane.    
				PercentList1 = Radius_Coordinates  
				xc, yc, r, sigma = taubinSVD(Radius_Coordinates)  
				print(r)   

				#Update Results.
				f = open(resultsfile1, 'a')
				writer = csv.writer(f)
				data_values = (filename, text_name, sum_red, sum_green, sum_red / sum_green, mask_area, MembraneLength, sigma, r)  
				writer.writerow(data_values)
				f.close()

				#Make masked green membrane.	
				os.chdir(GreenPath)
				savefile_raw = text_name + ".png"
				cv2.imwrite(savefile_raw, green_mask)
				if file_name == VisualizeFile:
					cv2.imshow("Green", green_mask)
					cv2.waitKey(1000)
					cv2.destroyAllWindows()

				#Make masked red membrane. 
				os.chdir(RedPath)
				savefile_raw = text_name + ".png"
				cv2.imwrite(savefile_raw, red_mask)
				if file_name == VisualizeFile:
					cv2.imshow("Red", red_mask)
					cv2.waitKey(1000)
					cv2.destroyAllWindows()


				#Make math membrane. Open this folder in FIJI and click Image > Stacks > Z Project > Projection Type: Sum Slices > OK to yield a kymograph. 
				os.chdir(MathPath)
				savefile_raw = text_name + ".png"
				cv2.imwrite(savefile_raw, math_mask)
				if file_name == VisualizeFile:
					cv2.imshow("Math", math_mask)
					cv2.waitKey(1000)
					cv2.destroyAllWindows()

				#Save radii images.    
				os.chdir(RadiiPath)    
				savefile_raw = text_name + ".png"   
				cv2.imwrite(savefile_raw, radius_mask)   
				if file_name == VisualizeFile:   
					cv2.imshow("Radius", radius_mask)  
					cv2.waitKey(1000)   
					cv2.destroyAllWindows()   

				else:
					continue

			finally:
				continue

	print('\n\n****   Completed!   *****\n\n')