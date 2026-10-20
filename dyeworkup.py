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
from skimage.morphology import remove_small_holes	###
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

#Window_range is the width of the mask, or the radial window in which this program will search for the membrane.
#Larger windows are needed for membranes with greater brightness variability (because the mask hugs dimmer regions more tightly).
#Window_range = 30 is approximately 15% slower than window_range = 20.
window_range = 20 				###int(input("\n\nHow many pixels wide is your membrane mask? Recommended 20–30: "))

#Window_size_real is the width of the membrane, i.e., the number n brightest adjacent points that compose the brightess radial lines 
#from the outer edge to the inner edge of the membrane. 
window_size_real = 6 			###int(input("\n\nHow many pixels wide is your membrane? Recommended 3-10: "))
VisualizeNumber = "green_0000"
VisualizeFile = VisualizeNumber + ".png"

#Creating ResultsFile1
header = ('File', 'Frame', 'Workup Threshold', 'Binary Mask Cutoff', 'Close Kernel', 'Crop', 'Mask Width', 'Mask Pixel Count', 'Sum G Mask', 'Sum R Mask', 'Patch Threshold', 'Patch Pixel Count', 'Sum G Patches', 'Sum R Patches', 'Cell Pixel Count', 'Sum G Cell', 'Sum R Cell', 'Avg R Mem Brightness', 'Avg R Background Brightness')
resultsfile1 = save_path +'Results.csv'
f = open(resultsfile1, 'w')
# create the csv writer
writer = csv.writer(f)
# Writing header
writer.writerow(header)
f.close()

#Create pngs of each tif.
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
		MaskPath = save_path + filename + "_Mask"
		MembranePath = save_path + filename + "_Membrane"
		PatchPath = save_path + filename + "_Patch"
		Path(CellPath).mkdir(parents=True, exist_ok=True)    
		Path(MaskPath).mkdir(parents=True, exist_ok=True)
		Path(MembranePath).mkdir(parents=True, exist_ok=True)
		Path(PatchPath).mkdir(parents=True, exist_ok=True)

		os.chdir(CellPath)    
		CellGreen = CellPath + "/Green"    
		CellRed = CellPath + "/Red"    
		Path(CellGreen).mkdir(parents=True, exist_ok=True)    
		Path(CellRed).mkdir(parents=True, exist_ok=True)    

		os.chdir(MaskPath)
		MaskGreen = MaskPath + "/Green"
		MaskRed = MaskPath + "/Red"
		Path(MaskGreen).mkdir(parents=True, exist_ok=True)
		Path(MaskRed).mkdir(parents=True, exist_ok=True)

		os.chdir(MembranePath)
		MembraneGreen = MembranePath + "/Green"
		MembraneRed = MembranePath + "/Red"
		Path(MembraneGreen).mkdir(parents=True, exist_ok=True)
		Path(MembraneRed).mkdir(parents=True, exist_ok=True)

		os.chdir(PatchPath)
		PatchGreen = PatchPath + "/Green"
		PatchRed = PatchPath + "/Red"
		Path(PatchGreen).mkdir(parents=True, exist_ok=True)
		Path(PatchRed).mkdir(parents=True, exist_ok=True)

		os.chdir(l)


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

			print("\nOpening file ", filename, "\n")

			blur_kernel = 20
			input_thresh = int(input("\n\nWhat is the threshold for your binary mask? Type a value from 1 to 255. 10-30 recommended for single cells, 2-20 recommended for multiple: "))
			close_kernel = int(input("\n\nWhat is the close kernel for your binary mask? Type a value from 0 (no gaps) to 50 (large gaps): "))
			dilation_kernel = 20
			erosion_kernel = 10
			input_crop = int(input("\n\nHow much do you need to shrink your mask for it to cross the membrane? Type a pixel count, recommended 40–50: "))

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

			patch_thresh = 1500

		#Mask membrane.
			#Blur out pixels to avoid membrane gaps.
			blurred_green = cv2.blur(img/64, (blur_kernel,blur_kernel)).astype(np.uint8)	#img_g/64 is here for visualization purposes (so you can see how well even a dim cell is being masked in the pop up). The blur/close kernels compensate for wrapping if it occurs. Change to np.clip to skip close.  

			#Convert image to binary mask.
			ret, binary_green = cv2.threshold(blurred_green, input_thresh, 255, cv2.THRESH_BINARY)

			#Close, remove junk, fill in cell.
			close_green = closing(binary_green, disk(close_kernel)).astype(bool)											
			clean_green = remove_small_objects(close_green, min_size=10000)
			hole_green = remove_small_holes(clean_green, area_threshold=50000)	### 100000 or 50000
			dilation_green = dilation(hole_green, disk(dilation_kernel))													
			erosion_green = erosion(dilation_green, disk(erosion_kernel)).astype(np.uint8)									
			cell_green = cv2.normalize(erosion_green, 0, 0, 255, cv2.NORM_MINMAX)
			mask_cell = np.argwhere(cell_green == 255).tolist()   ##new

			#Identify cell outline.
			blank = np.zeros([ylim,xlim,1], dtype=np.uint8)
			contours, hierarchy = cv2.findContours(cell_green, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
			sel = []
			for contour in contours:
				area = cv2.contourArea(contour)
				if area > 5000:
					sel.append(contour)
			blankpic = cv2.drawContours(blank, sel, -1, 255, input_crop)

			#Identify and view cell membrane.
			blurred_green_2 = blurred_green/1000
			contours_int, hierarchy_int = cv2.findContours(blankpic, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
			membrane = cv2.drawContours(blurred_green_2, contours_int[1:100], -1, 255, window_range)

			img_gtx = cv2.imread(file_name_green,0)
			h, w = img_gtx.shape[:2]
			red_pic = np.zeros((h,w,3), dtype='uint8')
			red_pic[:,:,2] = img_gtx*3
			blue_membrane = np.zeros((h,w,3), dtype='uint8')
			blue_membrane[:,:,0] = membrane
			#cv2.imshow("Binary", red_pic + blue_membrane)
			#cv2.waitKey(1000)
			#cv2.destroyAllWindows()

			#Create mask of cell membrane.
			blank2 = np.zeros([ylim,xlim,1], dtype=np.uint8)
			mask = cv2.drawContours(blank2, contours_int[1:100], -1, 1, window_range)
			coord = np.argwhere(mask == 1).tolist()

			#Create mask lists. 
			mask_cell_x = []   
			mask_cell_y = []   
			mask_cell_g = []   
			mask_cell_r = []  
			mask_x = []
			mask_y = []
			mask_g = []
			mask_r = []

		#Run all math and make all images for mask.
			#Match up cell coordinate lists with raw data.     
			for [y, x] in mask_cell:   
				mask_cell_y.append(y)   
				mask_cell_x.append(x)   
				mask_cell_g.append(int(data[y][x]))   
				mask_cell_r.append(int(datared[y][x]))   

			#Create an array for the green cell.  
			mask_green_cell = np.zeros([ylim,xlim], dtype=np.uint16)   
			for d,e,g in zip(mask_cell_y, mask_cell_x, mask_cell_g):   
				mask_green_cell[d][e] = g  
			green_cell_flat = mask_green_cell.flatten()
			green_cell_list = green_cell_flat.tolist() 

			#Create an array for the red cell.   
			mask_red_cell = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(mask_cell_y, mask_cell_x, mask_cell_r):
				mask_red_cell[d][e] = r
			red_cell_flat = mask_red_cell.flatten()
			red_cell_list = red_cell_flat.tolist() 

			#Math out cell brightness data.    
			sum_green_cell = sum(green_cell_list)
			sum_red_cell = sum(red_cell_list)
			cell_area = np.count_nonzero(green_cell_flat)

			#Match up mask coordinate list with raw data. 
			for [y, x, u] in coord:
				mask_y.append(y)
				mask_x.append(x)
				mask_g.append(int(data[y][x]))
				mask_r.append(int(datared[y][x]))

			#Create an array for the green mask.
			mask_green = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,g in zip(mask_y, mask_x, mask_g):
				mask_green[d][e] = g

			#Create an array for the red mask.
			mask_red = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(mask_y, mask_x, mask_r):
				mask_red[d][e] = r

			#Math out mask brightness data. 
			sum_green_mask = sum(mask_g)
			sum_red_mask = sum(mask_r)
			mask_area = len(mask_g)

			#Find outer contour.
			blank3 = np.zeros([ylim,xlim,1], dtype=np.uint8)
			contours_outer, hierarchy_outer = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
			edge = cv2.drawContours(blank3, contours_outer, -1, 255, 1)
			coord_edge = np.argwhere(edge == 255).tolist()
	
			#Find the center of the cell. Can be used to find membrane from outer contour to center of cell. Significantly faster.
			#for p in contours_outer:
				#Mo = cv2.moments(p)
				#if Mo['m00'] != 0:
					#cxo = int(Mo['m10']/Mo['m00'])
					#cyo = int(Mo['m01']/Mo['m00'])

			#Find inner contour.
			blank4 = np.zeros([ylim,xlim,1], dtype=np.uint8)
			contours_inner, hierarchy_inner = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_NONE)
			contours_inner_true = []
			for contour_inner in contours_inner[1:100]:
				M = cv2.moments(contour_inner)
				if M['m00'] != 0:
					cx = int(M['m10']/M['m00'])
					cy = int(M['m01']/M['m00'])
				inside = cv2.pointPolygonTest(contours_outer[0], (cx,cy), False)
				if inside == 1:
					contours_inner_true.append(contour_inner)
			inner_edge = cv2.drawContours(blank4, contours_inner_true, -1, 255, 1)
			coord_inner_edge = np.argwhere(inner_edge == 255).tolist()
			#cv2.imshow("Full", edge + inner_edge)
			#cv2.waitKey(1000)
			#cv2.destroyAllWindows()

			#Find n points in inner contour nearest to outer contour. Currently finding nearest 20 pts & choosing every 2 (10 total). Identifying these points is fast.
			outer_list = []
			inner_list = []
			for [ye, xe, ue] in coord_edge: 
				ordered_list = []
				for [yi, xi, ui] in coord_inner_edge:
					di = math.sqrt((xe-xi)*(xe-xi)+(ye-yi)*(ye-yi))
					ordered_list.append([di, yi, xi])
				ordered_list.sort()
				for [di, yi, xi] in ordered_list[0:20:2]:
					inner_list.append([yi, xi])
				outer_list.extend([ye, xe] for i in range(10))

			#This is script to match the outer countour to points in the inner contour on the same column or row. Results in a narrower mask. Does not decrease calculation time.
			#for [ye, xe, ue] in coord_edge: 
				#for [yn, xn, un] in coord_inner_edge:
					#if yn == ye:
						#outer_list.append([ye, xe])
						#inner_list.append([yn, xn])
					#if xn == xe: 
						#outer_list.append([ye, xe])
						#inner_list.append([yn, xn])

			#Create coordinate lists.
			CoordM = []
			CoordP = []

			#Choose sum(n) brightest pixels radially from outer edge to inner edge of green membrane mask.
			#This code is for drawing lines from outer contour to the center of the cell.
			#for [ye, xe, ue] in coord_edge: 
				#rr, cc = line(ye,xe,cyo,cxo)	#continue with below

			#Draw lines from the outer point list to the inner point list.
			for [ye, xe], [yn, xn] in zip(outer_list, inner_list):				
				rr, cc = line(ye,xe,yn,xn)
				Line_y = []
				Line_x = [] 
				Line_val = []
				for y, x in zip(rr, cc):
					Line_y.append(int(y))										
					Line_x.append(int(x))									
					Line_val.append(int(mask_green[y][x]))									
				dfLine = np.array([Line_y, Line_x, Line_val])

			#Find n brightest adjacent points in each line.
				highest_average = float('-inf')

				num_iterations = len(Line_y) - window_size_real + 1

				for a in range(num_iterations):
					values = dfLine[2][a:a+window_size_real]
					average = values.mean()

					if average > highest_average:
						highest_average = average
						
						pass
						
						highest_values = dfLine[2][a:a+window_size_real]
						highest_value_rows = dfLine[0][a:a+window_size_real]
						highest_value_cols = dfLine[1][a:a+window_size_real]

				High_Values = list(highest_values)
				High_Rows = list(highest_value_rows)
				High_Columns = list(highest_value_cols)

			#Collate n brightest points into a coordinate list.
				for y,x in zip(High_Rows,High_Columns):
					if [int(y),int(x)] not in CoordM:
			 			CoordM.append([int(y),int(x)]) 
			
			#Collate n brightest points into a coordinate list iff avg(n) from the original line >10x background (est by image mode).		
				if highest_average > patch_thresh:				
					High_Rows_Patch = list(highest_value_rows)	
					High_Columns_Patch= list(highest_value_cols)		
					for y,x in zip(High_Rows_Patch,High_Columns_Patch):					
						if [int(y),int(x)] not in CoordP:			
			 				CoordP.append([int(y),int(x)]) 		

		#Create membrane and membrane patch lists.
			membrane_x = []
			membrane_y = []
			membrane_g = []
			membrane_r = []
			patch_x = []
			patch_y = []
			patch_g = []
			patch_r = []

		#Run all math and make all images for membrane.
			#Match up membrane coordinate list with raw data. 			
			for [y,x] in CoordM:
				membrane_y.append(y)
				membrane_x.append(x)
				membrane_g.append(int(data[y][x]))
				membrane_r.append(int(datared[y][x]))

			#Math out membrane brightness data. 	
			sum_green_membrane = sum(membrane_g)
			sum_red_membrane = sum(membrane_r)
			membrane_area = len(membrane_g)

			#Create an array for the green membrane.
			membrane_green = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,g in zip(membrane_y, membrane_x, membrane_g):
				membrane_green[d][e] = g

			#Create an array for the red membrane.
			membrane_red = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(membrane_y, membrane_x, membrane_r):
				membrane_red[d][e] = r
		
		#Run all math and make all images for membrane patches.
			#Match up patch coordinate list with raw data. 
			for [y,x] in CoordP:
				patch_y.append(y)
				patch_x.append(x)
				patch_g.append(int(data[y][x]))
				patch_r.append(int(datared[y][x]))

			#Math out membrane patch brightness data. 
			sum_green_patch = sum(patch_g)
			sum_red_patch = sum(patch_r)
			patch_area = len(patch_g)

			#Math out pixel by pixel brightness data.
			patch_g_array = np.array(patch_g)
			patch_g_array[patch_g_array == 0] = 1                   ###this prevents division errors when (for whatever reason) green pixel is zero. take with a grain of salt.
			patch_r_array = np.array(patch_r)
			patch_r_g = patch_r_array/patch_g_array
			sum_patch_pixRG = sum(patch_r_g)

			#Create an array for the green patches.
			patch_green = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,g in zip(patch_y, patch_x, patch_g):
				patch_green[d][e] = g

			#Create an array for the red patches.
			patch_red = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(patch_y, patch_x, patch_r):
				patch_red[d][e] = r


			try:
				#Update Results
				f = open(resultsfile1, 'a')
				writer = csv.writer(f)
				data_values = (filename, text_name, patch_thresh, input_thresh*64, close_kernel, input_crop, window_range, mask_area, sum_green_mask, sum_red_mask, patch_thresh, patch_area, sum_green_patch, sum_red_patch, cell_area, sum_green_cell, sum_red_cell, sum_red_patch / patch_area, (sum_red_cell - sum_red_patch) / (cell_area - patch_area))
				writer.writerow(data_values)
				f.close()
				
				#Make cell green.	###new
				os.chdir(CellGreen)
				savefile_raw = green_name + ".png"
				cv2.imwrite(savefile_raw, mask_green_cell)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Cell Green", cell_green)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make cell red.	###new
				os.chdir(CellRed)
				savefile_raw = red_name + ".png"
				cv2.imwrite(savefile_raw, mask_red_cell)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Cell Red", cell_red)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make mask green.
				os.chdir(MaskGreen)
				savefile_raw = green_name + ".png"
				cv2.imwrite(savefile_raw, mask_green)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Mask Green", mask_green)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make mask red.
				os.chdir(MaskRed)
				savefile_raw = red_name + ".png"
				cv2.imwrite(savefile_raw, mask_red)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Mask Red", mask_red)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make membrane green.
				os.chdir(MembraneGreen)
				savefile_raw = green_name + ".png"
				cv2.imwrite(savefile_raw, membrane_green)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Membrane Green", membrane_green)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make membrane red.
				os.chdir(MembraneRed)
				savefile_raw = red_name + ".png"
				cv2.imwrite(savefile_raw, membrane_red)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Membrane Red", membrane_red)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make patch green.
				os.chdir(PatchGreen)
				savefile_raw = green_name + ".png"
				cv2.imwrite(savefile_raw, patch_green)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Patch Green", patch_green)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make patch red.
				os.chdir(PatchRed)
				savefile_raw = red_name + ".png"
				cv2.imwrite(savefile_raw, patch_red)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Patch Red", patch_red)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()
				#else:
					#os.chdir(dir_path)

			except: 
				continue
		else: 
				continue

print('\n\n****   Completed!   *****\n\n')


	