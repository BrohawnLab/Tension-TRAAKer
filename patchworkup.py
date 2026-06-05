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

message = '*** You will be prompted to input file paths with this script, please read the prompts for each file location to ensure the script runs correctly. ***'
print("\n\n", message, "\n\n") 

#Where are your files?
path = input("Where are your files (folder with subfolders tifs and results)? include the final /: ")

#Printing the pathways & setting pathways
dir_path = os.path.join(path, "tifs/")
print("\n", "Your tif files have been found here:", dir_path, "\n")
save_path = os.path.join(path, "results/")
print("\n", "Your results can be found here:", save_path, "\n")

#Window_size is the width of your membrane in pixels. 
window_size = 12 		###int(input("\n\nHow many pixels wide is your membrane?: "))
KeepPlots = "True"
VisualizeNumber = "0030"		#Pick a file to visualize to check your membrane fit.
VisualizeFile = VisualizeNumber + ".png"

#Create a results file. This file has more information than you'll likely use.
header = ('File', 'Frame', '# Rows Radii Calc', 'Sigma', 'Radius', 'Mask Area', 'Sum Mask ', 'Membrane Height', 'Membrane Area', 'Sum Membrane')
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

		#Create your image folders. This script produces more data than you will likely use--omit result images as desired.
		#This folder will include images of your masked membrane--i.e. data from every row depicting the sum(n) brightest pixels in that row, where n = window_size.
		os.chdir(save_path)												
		MaskPath = save_path + filename + "_Mask"
		Path(MaskPath).mkdir(parents=True, exist_ok=True)

		#This folder will include images of your cropped masked membrane--i.e. data from only the chosen number of brightest rows, depicting the sum(n) brightest pixels in that row, where n = window_size.
		os.chdir(save_path)
		MembranePath = save_path + filename + "_Membrane"
		Path(MembranePath).mkdir(parents=True, exist_ok=True)

		#This folder will include only pixels used in the radii calculation--i.e. in each of the chosen number of brightest rows, the midpoint pixel of the sum(n) brightest pixels in that row, where n = window_size.
		os.chdir(save_path)
		RadiiPath = save_path + filename + "_Radii"
		Path(RadiiPath).mkdir(parents=True, exist_ok=True)

		#Count the number of frames.
		file_number_list = []
		im = Image.open(f)
		for i, page in enumerate(ImageSequence.Iterator(im)):
			if i % 1 == 0:
				file_number_list.append(i)
			else:
				continue 
		file_number_final = max(file_number_list)
		print(file_number_final)

		ret, images_test = cv2.imreadmulti(f,[],-1)
		img_test = images_test[10]
		plt.imshow(img_test)
		plt.show()

		#Choose the number of brightest rows that will appear in your membrane images. 
		#This number matters most if your input tif includes rows with no membrane that you would like to omit.
		CropSize = int(input("How many rows tall is your region of interest? Overestimate here: "))				
		
		#Choose the number of brightest rows that will appear in your radii calculation.
		#This number matters if you have a dim membrane and wish to avoid fitting noise. 
		#Choose the largest number of rows that reasonably tracks your membrane. 
		#Note that membrane tracking will be more difficult at high pressures, as total fluorescence has been diluted across a larger membrane area.
		MembraneLength = int(input("How many rows tall is the membrane you would like to fit? Underestimate here: "))

		#Work up each cell. g is the number of frames.
		ret, images_expt = cv2.imreadmulti(f,[],-1)
		for g in range(file_number_final+1):
			text_name = f"{g:04d}"
			file_name = text_name + ".png"
			index = int(g)
			img = images_expt[index]
			data = np.asarray(img)
			shape = data.shape
			xlim = shape[1]
			ylim = shape[0]

			#Define your variables and lists. 
			CoordM = []
			CoordR = []
			Mask_Coordinates = []
			Mask_Coordinates_Crop = []
			Radius_Coordinates = []
			Sum_List = []
			fluorescence_row_list = []
			radius_row_list = []
			mask_y = []
			mask_x = []
			mask_d = []
			membrane_y = []
			membrane_x = []
			membrane_d = []
			radius_y = []
			radius_x = []
			radius_d = []

			#Identify each row as a line of points.
			for row_index in range(ylim):
				row = data[row_index]
				Line_y = []
				Line_x = [] 
				Line_val = []
				for column_index in range(xlim):
					Line_y.append(int(row_index))										
					Line_x.append(int(column_index))									
					Line_val.append(int(row[column_index]))									
				dfLine = np.array([Line_y, Line_x, Line_val])

			#Find n brightest adjacent points in each line.
				highest_average = float('-inf')

				num_iterations = len(Line_y) - window_size + 1

				for a in range(num_iterations):
					values = dfLine[2][a:a+window_size]
					average = values.mean()

					if average > highest_average:
						highest_average = average
						
						pass
						
						highest_values = dfLine[2][a:a+window_size]
						highest_value_rows = dfLine[0][a:a+window_size]
						highest_value_cols = dfLine[1][a:a+window_size]
						middle_col = dfLine[1][int(a+(window_size/2))]

				High_Values = list(highest_values)					#These are the pixel values of the brightest n adjacent pixels in your line.
				High_Rows = list(highest_value_rows)				#These are the y coordinates of the brightest n adjacent pixels in your line.
				High_Columns = list(highest_value_cols)				#These are the x coordinates of the brightest n adjacent pixels in your line.

				for y,x in zip(High_Rows,High_Columns):				
					if [int(y),int(x)] not in CoordM:
						CoordM.append([int(y),int(x)]) 				#These are the pixel coordinates of all the brightest points in every line.

				CoordR.append([int(row_index),int(middle_col)]) 	#This is the coordinate of the midpoint of each row of n brightest adjacent pixels.
				Sum_List.append([highest_average, row_index])		#This is the pixel value of the midpoint of each row of n brightest adjacent pixels.
			
			#Crop your image to the #CropSize brightest rows.
			Sum_List.sort(reverse=True)
			for [a, y] in Sum_List[0:CropSize]:
				fluorescence_row_list.append(y)						#This is the list of #CropSize brightest rows to appear in your membrane images.

			#Crop your image to the #MembraneLength brightest rows.
			for [a, y] in Sum_List[0:MembraneLength]:
				radius_row_list.append(y)							#This is the list of #MembraneLength brightest rows to appear in your radii images/calculation.

			#Fill lists describing your masked membrane (comprising the n brightest adjacent pixels in each row).
			for [y,x] in CoordM: 									
				mask_y.append(y)
				mask_x.append(x)
				mask_d.append(int(data[y][x]))

			#Fill lists describing your masked, cropped membrane.
			for [y,x] in CoordM: 
				if y in fluorescence_row_list:
					membrane_y.append(y)
					membrane_x.append(x)
					membrane_d.append(int(data[y][x]))
			
			#Fill lists describing the pixels used for membrane radii calculations.
			for [y,x] in CoordR: 	
				if y in radius_row_list: 
					radius_y.append(y)
					radius_x.append(x)
					radius_d.append(int(data[y][x]))

			#Create a list of the pixels used for membrane radii calculations.
			for y,x in zip(radius_y,radius_x):
				Radius_Coordinates.append([x,y])
				
			#Math out membrane brightness data. 	
			sum_mask_fluorescence = sum(mask_d)					#This is the total fluorescence in your masked membrane.
			mask_area = len(mask_d)								#This is the total number of pixels in your masked membrane.
			sum_membrane_fluorescence = sum(membrane_d)			#This is the total fluorescence in your masked, cropped membrane.
			membrane_area = len(membrane_d)						#This is the total number of pixels in your masked, cropped membrane.

			#Create an array for the masked membrane.
			mask_mask = np.zeros([ylim,xlim], dtype=np.uint8)		
			for d,e,g in zip(mask_y, mask_x, mask_d):
				mask_mask[d][e] = g

			#Create an array for the masked, cropped membrane.
			membrane_mask = np.zeros([ylim,xlim], dtype=np.uint8)		
			for d,e,g in zip(membrane_y, membrane_x, membrane_d):
				membrane_mask[d][e] = g

			#Create an array for the masked, cropped membrane midpoints used for radii caluclations.
			radius_mask = np.zeros([ylim,xlim], dtype=np.uint8)		
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
				data_values = (filename, text_name, MembraneLength, sigma, r, mask_area, sum_mask_fluorescence, CropSize, membrane_area, sum_membrane_fluorescence)
				writer.writerow(data_values)
				f.close()

				#Save mask images.	
				os.chdir(MaskPath)
				savefile_raw = text_name + ".png"
				cv2.imwrite(savefile_raw, mask_mask)
				if file_name == VisualizeFile:
					cv2.imshow("Mask", mask_mask)
					cv2.waitKey(1000)
					cv2.destroyAllWindows()

				#Save membrane images. 
				os.chdir(MembranePath)
				savefile_raw = text_name + ".png"
				cv2.imwrite(savefile_raw, membrane_mask)
				if file_name == VisualizeFile:
					cv2.imshow("Membrane", membrane_mask)
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