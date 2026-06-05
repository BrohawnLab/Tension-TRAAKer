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
from itertools import zip_longest 
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

#Window_range is the width of the mask, or the radial window in which this program will search for the membrane.
#Larger windows are needed for membranes with greater brightness variability (because the mask hugs dimmer regions more tightly).
#Window_range = 30 is approximately 15% slower than window_range = 20.
window_range = 20 				###int(input("\n\nHow many pixels wide is your membrane mask? Recommended 20–30: "))

#Window_size_real is the width of the membrane, i.e., the number n brightest adjacent points that compose the brightess radial lines 
#from the outer edge to the inner edge of the membrane. 
window_size_real = 6 			###int(input("\n\nHow many pixels wide is your membrane? Recommended 3-10: "))
VisualizeNumber = "green_0004"  				#Pick a file to visualize to check your membrane fit.
VisualizeFile = VisualizeNumber + ".png"

#Create a results file. This file has more information than you'll likely use.
header = ('File', 'Frame', 'Workup Threshold', 'Threshold Pixel Count', 'Sum G Threshold', 'Sum R Threshold', 'R/G Threshold', 'Binary Mask Cutoff', 'Close Kernel', 'Crop', 'Mask Width', 'Mask Pixel Count', 'Sum G Mask', 'Sum R Mask', 'R/G Mask', 'Membrane Width', 'Membrane Pixel Count', 'Sum G Membrane', 'Sum R Membrane', 'R/G Membrane', 'Patch Threshold', 'Patch Pixel Count', 'Sum G Patches', 'Sum R Patches', 'R/G Patches', 'Avg R/G per Patch Pixel', 'Cell Pixel Count', 'Sum G Cell', 'Sum R Cell', 'R/G Cell')
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
		
		#Create your image folders. This script produces more data than you will likely use--omit result images as desired.
		os.chdir(save_path)
		CellPath = save_path + filename + "_Cell"   
		MaskPath = save_path + filename + "_Mask"
		MembranePath = save_path + filename + "_Membrane"
		PatchPath = save_path + filename + "_Patch"
		Path(CellPath).mkdir(parents=True, exist_ok=True)    
		Path(MaskPath).mkdir(parents=True, exist_ok=True)
		Path(MembranePath).mkdir(parents=True, exist_ok=True)
		Path(PatchPath).mkdir(parents=True, exist_ok=True)

		#This folder will include images of your cells, with all pixels outside your mask set to zero. Channels 1 (red) and 2 (green) are saved separately. Cells are thresholded according to channel 2 (green).
		os.chdir(CellPath)    
		CellGreen = CellPath + "/Green"   
		CellRed = CellPath + "/Red"    
		Path(CellGreen).mkdir(parents=True, exist_ok=True)    
		Path(CellRed).mkdir(parents=True, exist_ok=True)   

		#This folder will include images of your membrane mask (here 20 pixels wide), with all pixels outside your mask set to zero. Channels 1 (red) and 2 (green) are saved separately. No threshold is applied.
		os.chdir(MaskPath)
		MaskGreen = MaskPath + "/Green"
		MaskRed = MaskPath + "/Red"
		Path(MaskGreen).mkdir(parents=True, exist_ok=True)
		Path(MaskRed).mkdir(parents=True, exist_ok=True)

		#This folder will include images of your membrane (here 6 pixels wide), with all pixels outside your mask set to zero. Channels 1 (red) and 2 (green) are saved separately. No threshold is applied.
		os.chdir(MembranePath)
		MembraneGreen = MembranePath + "/Green"
		MembraneRed = MembranePath + "/Red"
		Path(MembraneGreen).mkdir(parents=True, exist_ok=True)
		Path(MembraneRed).mkdir(parents=True, exist_ok=True)

		#This folder will include images of your thresholded membrane (here 6 pixels wide, with average brightness > 1500 AU (16-bit) in channel 2), with all pixels outside your mask set to zero. Channels 1 (red) and 2 (green) are saved separately.
		os.chdir(PatchPath)
		PatchGreen = PatchPath + "/Green"
		PatchRed = PatchPath + "/Red"
		Path(PatchGreen).mkdir(parents=True, exist_ok=True)
		Path(PatchRed).mkdir(parents=True, exist_ok=True)

		os.chdir(l)

		#Test whether you like a binary mask of your cell. You can omit this entire section if your data is homogeneous & you hard code the input_thresh and close_kernel values.
		if_cont = "n"
		while if_cont == "n":
			test_green = VisualizeFile
			img_g = cv2.imread(test_green,-1)
			
			blur_kernel = 20      ###int(input("\n\nWhat size is your blur kernel? Recommended 0-20: "))
			input_thresh = int(input("\n\nWhat is the threshold for your binary mask? Type a value from 1 to 255. 10-30 recommended for single cells, 2-20 recommended for multiple: "))
			
			#Blur out pixels to avoid membrane gaps. Convert to binary mask.
			blurred_test = cv2.blur(img_g/64, (blur_kernel,blur_kernel)).astype(np.uint8)		#img_g/64 is here for visualization purposes (so you can see how well even a dim cell is being masked in the pop up). Note that this will supersaturate your image (for masking purposes only).
			ret, binary_test = cv2.threshold(blurred_test, input_thresh, 255, cv2.THRESH_BINARY)
			cv2.imshow("Binary", binary_test)
			cv2.waitKey(1000)
			cv2.destroyAllWindows()

			close_kernel = int(input("\n\nWhat is the close kernel for your binary mask? Type a value from 0 (no gaps) to 50 (large gaps): "))
			dilation_kernel = 20    ###int(input("\n\nWhat size is your dilation kernel? Recommended 0-20: "))
			erosion_kernel = 10     ###int(input("\n\nWhat size is your erosion kernel? Recommended 0-20: "))

			#Close cell & remove exterior junk.
			close_test = closing(binary_test, disk(close_kernel)).astype(bool)												
			clean_test = remove_small_objects(close_test, min_size=10000).astype(np.uint8)	#Adjust min_size according to your cell/debris size.
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

		#Test whether you like your membrane mask. You can omit this entire section if your data is homogeneous & you hard code the input_crop value.
		if_conts = "n"
		while if_conts == "n":
			input_crop = int(input("\n\nHow much do you need to shrink your mask for it to cross the membrane? Type a pixel count, recommended 40–50: "))
			
			img_gt = cv2.imread(test_green,0)
			ylim, xlim = img_gt.shape[:2]

			#Identify cell outline and shrink to cell membrane.
			blank_test = np.zeros([ylim,xlim,1], dtype=np.uint8)
			contours_test, hierarchy_test = cv2.findContours(cell_test, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
			sel_test = []
			for contour_test in contours_test:
				area_test = cv2.contourArea(contour_test)
				if area_test > 5000:
					sel_test.append(contour_test)
			blankpic_test = cv2.drawContours(blank_test, sel_test, -1, 255, input_crop)

			#Identify and view cell membrane.
			blurred_test_2 = blurred_test/1000
			contours_int_test, hierarchy_int_test = cv2.findContours(blankpic_test, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_NONE)
			membrane_test = cv2.drawContours(blurred_test_2, contours_int_test[1:100], -1, 255, window_range)

			#Visualize your cell mmembrane mask. Reject your inputs and restart if you have not successfully masked your membrane.
			red_pic = np.zeros((ylim, xlim,3), dtype='uint8')
			red_pic[:,:,2] = img_gt*3
			blue_membrane = np.zeros((ylim, xlim,3), dtype='uint8')
			blue_membrane[:,:,0] = membrane_test
			cv2.imshow("Mask", red_pic + blue_membrane)
			cv2.waitKey(1000)
			cv2.destroyAllWindows()

			if_conts = input("\n\nDo you wish to continue with these inputs? y or n?: ")

		#Now that you've chosen your input parameters, it's time to apply these to your data. Count the number of green pngs.
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

		#Mask the membrane.
			#Blur out pixels to avoid membrane gaps.
			blurred_green = cv2.blur(img/64, (blur_kernel,blur_kernel)).astype(np.uint8)	#img/64 is here to match how the cell is being masked to the tester script above.

			#Convert image to binary mask.
			ret, binary_green = cv2.threshold(blurred_green, input_thresh, 255, cv2.THRESH_BINARY)

			#Close, remove junk, fill in cell. Mask_cell creates a list of the locations of all pixels in your cell mask.
			close_green = closing(binary_green, disk(close_kernel)).astype(bool)											
			clean_green = remove_small_objects(close_green, min_size=10000)				#Adjust min_size according to your cell/debris size.
			dilation_green = dilation(clean_green, disk(dilation_kernel))													
			erosion_green = erosion(dilation_green, disk(erosion_kernel)).astype(np.uint8)									
			cell_green = cv2.normalize(erosion_green, 0, 0, 255, cv2.NORM_MINMAX)
			mask_cell = np.argwhere(cell_green == 255).tolist()   

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

			#Visualize each cell mask as it is created, if desired.
			###img_gtx = cv2.imread(file_name_green,0)
			###h, w = img_gtx.shape[:2]
			###red_pic = np.zeros((h,w,3), dtype='uint8')
			###red_pic[:,:,2] = img_gtx*3
			###blue_membrane = np.zeros((h,w,3), dtype='uint8')
			###blue_membrane[:,:,0] = membrane
			###cv2.imshow("Binary", red_pic + blue_membrane)
			###cv2.waitKey(1000)
			###cv2.destroyAllWindows()

			#Create mask of cell membrane. Coord creates a list of the locations of all pixels in your membrane mask.
			blank2 = np.zeros([ylim,xlim,1], dtype=np.uint8)
			mask = cv2.drawContours(blank2, contours_int[1:100], -1, 1, window_range)
			coord = np.argwhere(mask == 1).tolist()

			#Create mask lists. 
			mask_cell_x = []   #This will comprise the x values of all pixels in your cell mask.
			mask_cell_y = []   #This will comprise the y values of all pixels in your cell mask.
			mask_cell_g = []   #This will comprise the green (channel 2) values of all pixels in your cell mask.
			mask_cell_r = []   #This will comprise the red (channel 1) values of all pixels in your cell mask.
			mask_x = []		   #This will comprise the x values of all pixels in your membrane mask.
			mask_y = []		   #This will comprise the y values of all pixels in your membrane mask.
			mask_g = []        #This will comprise the green (channel 2) values of all pixels in your membrane mask.
			mask_r = []        #This will comprise the red (channel 1) values of all pixels in your membrane mask.

		#Run all math and make all images for cell and membrane masks.
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
			mask_green_cell[mask_green_cell < patch_thresh] = 0    #This eliminates all pixels dimmer than your patch threshold in channel 2 (green) of your cell mask.
			green_cell_flat = mask_green_cell.flatten()
			green_cell_list = green_cell_flat.tolist() 		       #This creates a list of all thresholded green pixel values in your cell mask.

			#Create an array for the red cell.   
			mask_red_cell = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(mask_cell_y, mask_cell_x, mask_cell_r):
				mask_red_cell[d][e] = r
			mask_red_cell[mask_green_cell < patch_thresh] = 0 		#This finishes masking channel 1 (red) according to channel 2 (green).
			red_cell_flat = mask_red_cell.flatten()
			red_cell_list = red_cell_flat.tolist() 					#This creates a list of all thresholded red pixel values in your cell mask.

			#Math out cell brightness data.    
			sum_green_cell = sum(green_cell_list)					#This is the sum of all channel 2 (green) pixels in your cell mask.
			sum_red_cell = sum(red_cell_list)						#This is the sum of all channel 1 (red) pixels in your cell mask.
			cell_area = np.count_nonzero(green_cell_flat)			#This is the size of your cell mask (total pixel count).

			#Fill cell membrane mask coordinate lists and match with raw data.  
			for [y, x, u] in coord:
				mask_y.append(y)
				mask_x.append(x)
				mask_g.append(int(data[y][x]))
				mask_r.append(int(datared[y][x]))

			#Create an array for the green membrane mask.
			mask_green = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,g in zip(mask_y, mask_x, mask_g):
				mask_green[d][e] = g

			#Create an array for the red membrane mask.
			mask_red = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(mask_y, mask_x, mask_r):
				mask_red[d][e] = r

			#Math out membrane mask brightness data. 
			sum_green_mask = sum(mask_g)						#This is the sum of all channel 2 (green) pixels in your membrane mask. Note no thresholding was applied here.
			sum_red_mask = sum(mask_r)							#This is the sum of all channel 1 (red) pixels in your membrane mask. Note no thresholding was applied here.
			mask_area = len(mask_g)								#This is the size of your membrane mask (total pixel count).

			#Find the outer contour of the membrane mask.
			blank3 = np.zeros([ylim,xlim,1], dtype=np.uint8)
			contours_outer, hierarchy_outer = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_NONE)
			edge = cv2.drawContours(blank3, contours_outer, -1, 255, 1)
			coord_edge = np.argwhere(edge == 255).tolist()		#This creates a list of all pixel locations composing the outer edge of your membrane mask.

			#Find inner contour of the membrane mask. Confirm that it is actually inside your outer contour.
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
			coord_inner_edge = np.argwhere(inner_edge == 255).tolist() #This creates a list of all pixel locations composing the inner edge of your membrane mask.
			###cv2.imshow("Full", edge + inner_edge)
			###cv2.waitKey(1000)
			###cv2.destroyAllWindows()

			#Find n pixels in inner contour nearest to outer contour. This allows you to draw lines from the outer edge to the inner edge of the membrane mask.
			#Along these lines, you will eventually choose sum(n) brightest pixels radially from the outer edge to the inner edge of the green membrane mask.
			#Currently this script finds the nearest 20 pixels in the inner contour & chooses every 2 (10 total).
			#You'll note that many lines overlap; this is to account for wiggly bits of the cell membrane--i.e., that some lines cross >1 membrane. 
			#Identifying these points is fast. Creating lines between them is slow. Choose wisely.
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

			#Two alternate methods for drawing lines across your cell membrane are: 

			#Method 1:
			#Choose sum(n) brightest pixels from outer edge to inner edge of green membrane mask along row or column.
			#Replace script above with this if you want to draw lines along a row or column.
			#This results in a narrower mask. It does not decrease calculation time. 
			###for [ye, xe, ue] in coord_edge: 
				###for [yn, xn, un] in coord_inner_edge:
					###if yn == ye:
						###outer_list.append([ye, xe])
						###inner_list.append([yn, xn])
					###if xn == xe: 
						###outer_list.append([ye, xe])
						###inner_list.append([yn, xn])

			#Method 2:
			#Choose sum(n) brightest pixels radially from outer edge to center of green cell.
			#Replace script above with this if you want to draw lines to the center of the cell. This is significantly faster.
			#This method often omits portions of wiggly membranes--i.e., when one line to the center of the cell crosses the membrane twice.
			###for p in contours_outer:
				###Mo = cv2.moments(p)
				###if Mo['m00'] != 0:
					###cxo = int(Mo['m10']/Mo['m00'])
					###cyo = int(Mo['m01']/Mo['m00'])
			###for [ye, xe, ue] in coord_edge: 
				###rr, cc = line(ye,xe,cyo,cxo)	#continue with Line_y = 
			
			#Create coordinate lists describing the cell membrane (membrane: unthresholded, M; patch: thresholded, P).
			CoordM = []
			CoordP = []
	
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

			#Find n brightest adjacent points in each line. n = window_size_real as set at the top of this script.
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

				High_Values = list(highest_values)					#These are the pixel values of your brightest n adjacent pixels in your line.
				High_Rows = list(highest_value_rows)				#These are the y coordinates of your brightest n adjacent pixels in your line.
				High_Columns = list(highest_value_cols)				#These are the x coordinates of your brightest n adjacent pixels in your line.

			#Collate n brightest adjacent pixels in each line into a coordinate list. Discard repeated pixels.
				for y,x in zip(High_Rows,High_Columns):
					if [int(y),int(x)] not in CoordM:
			 			CoordM.append([int(y),int(x)]) 
			
			#Collate n brightest adjacent pixels into a coordinate list iff avg(n) from the original line is greater than the set threshold (patch_thresh).	
			#Discard repeated pixels.	
				if highest_average > patch_thresh:				
					High_Rows_Patch = list(highest_value_rows)	
					High_Columns_Patch= list(highest_value_cols)		
					for y,x in zip(High_Rows_Patch,High_Columns_Patch):					
						if [int(y),int(x)] not in CoordP:			
			 				CoordP.append([int(y),int(x)]) 		

		#Create membrane and membrane patch lists.
			membrane_x = []							#This will comprise the x values of all pixels in your cell membrane.
			membrane_y = []							#This will comprise the y values of all pixels in your cell membrane.
			membrane_g = []							#This will comprise the channel 2 (green) values of all pixels in your cell membrane.
			membrane_r = []							#This will comprise the channel 1 (red) values of all pixels in your cell membrane.
			patch_x = []							#This will comprise the x values of all pixels in your thresholded cell membrane.
			patch_y = []							#This will comprise the y values of all pixels in your thresholded cell membrane.
			patch_g = []							#This will comprise the channel 2 (green) values of all pixels in your thresholded cell membrane.
			patch_r = []							#This will comprise the channel 1 (red) values of all pixels in your thresholded cell membrane.

		#Run all math and make all images for membrane.
			#Fill membrane coordinate lists and match with raw data. 			
			for [y,x] in CoordM:
				membrane_y.append(y)
				membrane_x.append(x)
				membrane_g.append(int(data[y][x]))
				membrane_r.append(int(datared[y][x]))

			#Math out membrane brightness data. 	
			sum_green_membrane = sum(membrane_g)					#This is the sum of all channel 2 (green) pixels in your membrane.
			sum_red_membrane = sum(membrane_r)						#This is the sum of all channel 1 (red) pixels in your membrane.
			membrane_area = len(membrane_g)							#This is the size of your membrane (by pixel count).

			#Create an array for the green membrane.
			membrane_green = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,g in zip(membrane_y, membrane_x, membrane_g):
				membrane_green[d][e] = g

			#Create an array for the red membrane.
			membrane_red = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(membrane_y, membrane_x, membrane_r):
				membrane_red[d][e] = r
		
		#Run all math and make all images for thresholded membrane (patches).
			#Fill patch coordinate lists and match with raw data. 	 
			for [y,x] in CoordP:
				patch_y.append(y)
				patch_x.append(x)
				patch_g.append(int(data[y][x]))
				patch_r.append(int(datared[y][x]))

			#Math out membrane patch brightness data. 
			sum_green_patch = sum(patch_g)							#This is the sum of all channel 2 (green) pixels in your thresholded membrane (patch).
			sum_red_patch = sum(patch_r)							#This is the sum of all channel 1 (red) pixels in your thresholded membrane (patch).
			patch_area = len(patch_g)								#This is the size of your thresholded membrane (by pixel count).

			#Create an array for the green patches.
			patch_green = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,g in zip(patch_y, patch_x, patch_g):
				patch_green[d][e] = g

			#Create an array for the red patches.
			patch_red = np.zeros([ylim,xlim], dtype=np.uint16)		
			for d,e,r in zip(patch_y, patch_x, patch_r):
				patch_red[d][e] = r

		#Run all math for pixel by pixel brightness data. 
		#While the results file includes this data, I have simply found it to be a noisier version of the thresholded membrane data.
		#Rather than calculating sum(red)/sum(green) across the entirety of a given mask (e.g., cell mask, membrane mask, membrane, thresholded membrane (patch)), this calculates red/green per pixel and averages the results.
			#Math out pixel by pixel brightness data.
			patch_g_array = np.array(patch_g)
			patch_g_array[patch_g_array == 0] = 1                   #This prevents division errors when the green pixel value is zero. Rare but annoying.
			patch_r_array = np.array(patch_r)
			patch_r_g = patch_r_array/patch_g_array
			sum_patch_pixRG = sum(patch_r_g)

		#Run all math for purely thresholded data.
		#While the results file includes this data, it's simply the unmasked version of the cell data.
		#This is a straight threshold applied to the green image with no masking at all. i.e., if you don't want a particular bit of cell debris included, you need to manually delete it in the green (channel 2) image.
		#This is mainly useful if you'd like to sanity check your data.
			#Threshold your channel 2 (green) image. 
			green_thresh = np.asarray(img)
			green_thresh[green_thresh < patch_thresh] = 0
			green_flat = green_thresh.flatten()
			green_list = green_flat.tolist()
			
			#Mask your channel 1 (red) image according to your thresholded green image.
			red_thresh = np.asarray(imgred)
			red_thresh[green_thresh < patch_thresh] = 0
			red_flat = red_thresh.flatten()
			red_list = red_flat.tolist()

			#Math out threshold brightness data. 
			sum_green_threshold = sum(green_list)					#This is the sum of all channel 2 (green) pixels in your thresholded image.
			sum_red_threshold = sum(red_list)						#This is the sum of all channel 1 (red) pixels in your thresholded image.
			threshold_area = np.count_nonzero(green_flat)			#This is number of pixels you're summing. 

			try:
				#Update Results.
				f = open(resultsfile1, 'a')
				writer = csv.writer(f)
				data_values = (filename, text_name, patch_thresh, threshold_area, sum_green_threshold, sum_red_threshold, sum_red_threshold / sum_green_threshold, input_thresh*64, close_kernel, input_crop, window_range, mask_area, sum_green_mask, sum_red_mask, sum_red_mask / sum_green_mask, window_size_real, membrane_area, sum_green_membrane, sum_red_membrane, sum_red_membrane / sum_green_membrane, patch_thresh, patch_area, sum_green_patch, sum_red_patch, sum_red_patch / sum_green_patch, sum_patch_pixRG / patch_area, cell_area, sum_green_cell, sum_red_cell, sum_red_cell / sum_green_cell)
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

				#Make membrane mask green.
				os.chdir(MaskGreen)
				savefile_raw = green_name + ".png"
				cv2.imwrite(savefile_raw, mask_green)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Mask Green", mask_green)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make membrane mask red.
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

				#Make thresholded membrane (patch) green.
				os.chdir(PatchGreen)
				savefile_raw = green_name + ".png"
				cv2.imwrite(savefile_raw, patch_green)
				#if file_name_green == VisualizeFile:
					#cv2.imshow("Patch Green", patch_green)
					#cv2.waitKey(1000)
					#cv2.destroyAllWindows()

				#Make thresholded membrane (patch) red.
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


	