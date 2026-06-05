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
path = input("Where are your files (folder with subfolders tifs, pngs, and results)? include the final /: ")

#Printing the pathways & setting pathways
dir_path = os.path.join(path, "tifs/")
print("\n", "Your tif files have been found here:", dir_path, "\n")
png_path = os.path.join(path, "pngs/")
print("\n", "Your pngs can be found here:", png_path, "\n")
save_path = os.path.join(path, "results/")
print("\n", "Your results can be found here:", save_path, "\n")

VisualizeNumber = "green_0004"					#Pick a file to visualize to check your membrane fit.
VisualizeFile = VisualizeNumber + ".png"

#Creating ResultsFile. This file has more information than you'll likely use.
header = ('File', 'Frame', 'Workup Threshold', 'Binary Mask Cutoff', 'Close Kernel', 'Cell Pixel Count', 'Sum G Cell', 'Sum R Cell', 'R/G Cell')
resultsfile1 = save_path +'Results.csv'
f = open(resultsfile1, 'w')
# create the csv writer
writer = csv.writer(f)
# Writing header
writer.writerow(header)
f.close()

#Create pngs of each tif. The below assumes a 2 color tif, with your test data in channel 1 (in demo, red) and control data in channel 2 (in demo, green). 
#This script creates and saves separate pngs so that you can visually confirm your data has sorted correctly. See poke workup for script that omits this step.
os.chdir(dir_path)
for filename in os.listdir(dir_path):
	f = os.path.join(dir_path, filename)
	if fnmatch.fnmatch(filename, '*.tif'):
		print(filename)
		im = Image.open(f)
		IndivPath = png_path + filename
		Path(IndivPath).mkdir(parents=True, exist_ok=True)
		os.chdir(IndivPath)
		for i, page in enumerate(ImageSequence.Iterator(im)):
			if i % 2 == 0:
				g = i // 2
				page.save("red_" + f"{g:04d}" + ".png")
			else:
				g = (i-1) // 2
				page.save("green_" + f"{g:04d}" + ".png")
	else: 
		continue

os.chdir(png_path)
for filename in os.listdir(png_path):
	l = os.path.join(png_path, filename)
	if os.path.isdir(l):
		
		#Create your image folders.
		os.chdir(save_path)
		CellPath = save_path + filename + "_Cell"    
		Path(CellPath).mkdir(parents=True, exist_ok=True)    

		os.chdir(CellPath)    
		CellGreen = CellPath + "/Green"    
		CellRed = CellPath + "/Red"    
		Path(CellGreen).mkdir(parents=True, exist_ok=True)    
		Path(CellRed).mkdir(parents=True, exist_ok=True)    

		os.chdir(l)

		#Test whether you like your thresholding. You can omit this entire section if your data is homogeneous & you hard code the input_thresh and close_kernel values.
		if_cont = "n"
		while if_cont == "n":
			test_green = VisualizeFile
			img_g = cv2.imread(test_green,-1)
			
			blur_kernel = 20      ###int(input("\n\nWhat size is your blur kernel? Recommended 0-20: "))
			input_thresh = int(input("\n\nWhat is the threshold for your binary mask? Type a value from 1 to 255. 10-30 recommended for single cells, 2-20 recommended for multiple: "))
			
			#Blur out pixels to avoid membrane gaps. Convert to binary mask.
			blurred_test = cv2.blur(img_g/64, (blur_kernel,blur_kernel)).astype(np.uint8)			#img_g/64 is here for visualization purposes (so you can see how well even a dim cell is being masked in the pop up). Note that this will supersaturate your image (for masking purposes only).		
			ret, binary_test = cv2.threshold(blurred_test, input_thresh, 255, cv2.THRESH_BINARY)
			cv2.imshow("Binary", binary_test)
			cv2.waitKey(1000)
			cv2.destroyAllWindows()

			close_kernel = int(input("\n\nWhat is the close kernel for your binary mask? Type a value from 0 (no gaps) to 50 (large gaps): "))
			dilation_kernel = 20    ###int(input("\n\nWhat size is your dilation kernel? Recommended 0-20: "))
			erosion_kernel = 10     ###int(input("\n\nWhat size is your erosion kernel? Recommended 0-20: "))

			#Close cell & remove exterior junk.
			close_test = closing(binary_test, disk(close_kernel)).astype(bool)												
			clean_test = remove_small_objects(close_test, min_size=10000).astype(np.uint8)		#Adjust min_size according to your cell/debris size.
			c_test = cv2.normalize(clean_test, 0, 0, 255, cv2.NORM_MINMAX)
			cv2.imshow("Clean", c_test)
			cv2.waitKey(1000)
			cv2.destroyAllWindows()
			
			#Dilate and erode cell mask to encompass as much of membrane as possible.
			dilation_test = dilation(clean_test, disk(dilation_kernel))													
			erosion_test = erosion(dilation_test, disk(erosion_kernel)).astype(np.uint8)									
			cell_test = cv2.normalize(erosion_test, 0, 0, 255, cv2.NORM_MINMAX)
			
			#Visualize your cell mask. Reject your inputs and restart if you have not successfully masked your cell.
			img_gt = cv2.imread(test_green,0)
			h, w = img_gt.shape[:2]
			red_img = np.zeros((h,w,3), dtype='uint8')
			red_img[:,:,2] = blurred_test*10
			blue_img = np.zeros((h,w,3), dtype='uint8')
			blue_img[:,:,0] = cell_test
			cv2.imshow("Cell", red_img + blue_img)
			cv2.waitKey(1000)
			cv2.destroyAllWindows()

			if_cont = input("\n\nDo you wish to continue with these inputs? y or n?: ")

		#Count the number of green pngs.
		file_number = 0
		for png in os.listdir(l):
			if os.path.isfile(os.path.join(l, png)):
				file_number += 1
		file_number_final = int(file_number / 2)

		#Work up each cell. g is the number of green frames.
		for g in range(file_number_final): 
			os.chdir(l)
			text_name = f"{g:04d}"
			green_name = "green_" + text_name 
			red_name = "red_" + text_name 
			file_name_green = green_name + ".png"
			file_name_red = red_name + ".png"	

			print("\nOpening file ", file_name_green, "\n")

			img = cv2.imread(file_name_green,-1)	
			data = np.asarray(img)
			shape = data.shape
			xlim = shape[1]
			ylim = shape[0]

			imgred = cv2.imread(file_name_red,-1)		
			datared = np.asarray(imgred)
			shapered = datared.shape
			xlimred = shapered[1]
			ylimred = shapered[0]

			patch_thresh = 1500 				#Adjust this value according to your data. 1500 is roughly 10x background in my 16-bit images.

		#Mask membrane.
			#Blur out pixels to avoid membrane gaps.
			blurred_green = cv2.blur(img/64, (blur_kernel,blur_kernel)).astype(np.uint8)	

			#Convert image to binary mask.
			ret, binary_green = cv2.threshold(blurred_green, input_thresh, 255, cv2.THRESH_BINARY)

			#Close, remove junk, fill in cell. Mask_cell creates a list of the locations of all pixels in your cell mask.
			close_green = closing(binary_green, disk(close_kernel)).astype(bool)											
			clean_green = remove_small_objects(close_green, min_size=10000)				#Adjust min_size according to your cell/debris size.
			dilation_green = dilation(clean_green, disk(dilation_kernel))													
			erosion_green = erosion(dilation_green, disk(erosion_kernel)).astype(np.uint8)									
			cell_green = cv2.normalize(erosion_green, 0, 0, 255, cv2.NORM_MINMAX)
			mask_cell = np.argwhere(cell_green == 255).tolist()   


			#Create mask lists. 
			mask_cell_x = []   					#This will comprise the x values of all pixels in your cell mask.
			mask_cell_y = []   					#This will comprise the y values of all pixels in your cell mask.
			mask_cell_g = []   					#This will comprise the green (channel 2) values of all pixels in your cell mask.
			mask_cell_r = []   					#This will comprise the red (channel 1) values of all pixels in your cell mask.

		#Run all math and make all images for cell masks.
			#Fill cell mask coordinate lists and match with raw data.  
			for [y, x] in mask_cell:   
				mask_cell_y.append(y)   
				mask_cell_x.append(x)   
				mask_cell_g.append(int(data[y][x]))   
				mask_cell_r.append(int(datared[y][x]))   

			#Create an array for the green cell.   
			mask_green_cell = np.zeros([ylim,xlim], dtype=np.uint16)   
			for d,e,g in zip(mask_cell_y, mask_cell_x, mask_cell_g):   
				mask_green_cell[d][e] = g  
			mask_green_cell[mask_green_cell < patch_thresh] = 0 			#This eliminates all pixels dimmer than your patch threshold in channel 2 (green) of your cell mask.
			green_cell_flat = mask_green_cell.flatten()
			green_cell_list = green_cell_flat.tolist() 						#This creates a list of all thresholded green pixel values in your cell mask.

			#Create an array for the red cell.   
			mask_red_cell = np.zeros([ylim,xlim], dtype=np.uint16)			
			for d,e,r in zip(mask_cell_y, mask_cell_x, mask_cell_r):
				mask_red_cell[d][e] = r
			mask_red_cell[mask_green_cell < patch_thresh] = 0   			#This finishes masking channel 1 (red) according to channel 2 (green).
			red_cell_flat = mask_red_cell.flatten()
			red_cell_list = red_cell_flat.tolist() 							#This creates a list of all thresholded red pixel values in your cell mask.

			#Math out cell brightness data.    
			sum_green_cell = sum(green_cell_list)							#This is the sum of all channel 2 (green) pixels in your cell mask.
			sum_red_cell = sum(red_cell_list)								#This is the sum of all channel 1 (red) pixels in your cell mask.
			cell_area = np.count_nonzero(green_cell_flat)					#This is the size of your cell mask (total pixel count).

			try:
				#Update Results. 
				f = open(resultsfile1, 'a')
				writer = csv.writer(f)
				data_values = (filename, text_name, patch_thresh, input_thresh*64, close_kernel, cell_area, sum_green_cell, sum_red_cell, sum_red_cell / sum_green_cell)
				writer.writerow(data_values)
				f.close()
				
				#Make cell green.	
				os.chdir(CellGreen)
				savefile_raw = green_name + ".png"
				cv2.imwrite(savefile_raw, mask_green_cell)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Cell Green", cell_green)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make cell red.	
				os.chdir(CellRed)
				savefile_raw = red_name + ".png"
				cv2.imwrite(savefile_raw, mask_red_cell)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Cell Red", cell_red)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

			except: 
				continue
		else: 
				continue

print('\n\n****   Completed!   *****\n\n')


	