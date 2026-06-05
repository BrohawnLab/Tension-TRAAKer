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
window_size = 6    ###int(input("\n\nHow many pixels wide is your membrane?: "))
KeepPlots = "True"
VisualizeNumber = "0003"		#Pick a file to visualize to check your membrane fit.
VisualizeFile = VisualizeNumber + ".png"

#Creating a results file.
header = ('File', 'Frame', 'Sum Red', 'Sum Green', 'Sum R/G', 'Mask Area', 'Red List', 'Green List')
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

			imgred = images_expt[red_index]
			datared = np.asarray(imgred)
			shapered = datared.shape
			xlimred = shapered[1]
			ylimred = shapered[0]

			#Define your variables and lists. 
			CoordM = []
			CoordR = []
			Mask_Coordinates = []

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
						highest_valuesred = dfLinered[2][a:a+window_size]
						highest_averagered = highest_valuesred.mean()

						highest_value_rows = dfLine[0][a:a+window_size]
						highest_value_cols = dfLine[1][a:a+window_size]
						middle_col = dfLine[1][int(a+(window_size/2))]

				High_Values = list(highest_values)				#These are the pixel values of the brightest n adjacent green pixels in your line.
				High_ValuesRed = list(highest_valuesred)		#These are the red pixel values of the same pixels as chosen above.
				High_Rows = list(highest_value_rows)			#These are the y coordinates of the brightest n adjacent pixels in your line.
				High_Columns = list(highest_value_cols)			#These are the x coordinates of the brightest n adjacent pixels in your line.


				for y,x in zip(High_Rows,High_Columns):			#These are the pixel coordinates of all the brightest points in every line.
					if [int(y),int(x)] not in CoordM:
						CoordM.append([int(y),int(x)]) 

				CoordR.append([int(row_index),int(middle_col)]) #This is the coordinate of the midpoint of each row of n brightest adjacent pixels.
				Row_List.append(row_index)
				Green_List.append(int(highest_average))			#This is a list of the average green (channel 2) value of each row of n brightest adjacent pixels.
				Red_List.append(int(highest_averagered))		#This is a list of the average red (channel 1) value of the same pixels.

			#Fill lists describing your masked membrane (comprising the n brightest adjacent pixels in each row, chosen from the green channel (2)).
			for [y,x] in CoordM: 
				mask_y.append(y)
				mask_x.append(x)
				mask_d.append(int(data[y][x]))
				mask_e.append(int(datared[y][x]))

				
			#Math out membrane brightness data. 	
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

			#Create an array for the math.
			#Each column is a frame of the input tif, with column number = frame.
			#Each row within a column is sum(red)/sum(green) for the corresponding row of masked pixels in that frame.
			#This sum(red)/sum(green) value is multiplied by 1000 for ease of visualization in a 16-bit image.
			math_mask = np.zeros([ylim,file_number_final+1], dtype=np.uint16)		
			for d,e,l in zip(Row_List, Green_List, Red_List):
				math_mask[d][g] = int(l * 1000 / e)

			try:
				#Update Results.
				f = open(resultsfile1, 'a')
				writer = csv.writer(f)
				data_values = (filename, text_name, sum_red, sum_green, sum_red / sum_green, mask_area, Red_List, Green_List)
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



				else:
					continue

			finally:
				continue

	print('\n\n****   Completed!   *****\n\n')