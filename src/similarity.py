import cv2
import os
import numpy as np
import sys
from matplotlib import pyplot as plt

from lipyc.scheduler import scheduler

#https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_imgproc/py_template_matching/py_template_matching.html
#help(cv2)
def basic_compare(img, template, threshold):
    methods = ['cv2.TM_CCOEFF', 'cv2.TM_CCOEFF_NORMED', 'cv2.TM_CCORR',
            'cv2.TM_CCORR_NORMED', 'cv2.TM_SQDIFF', 'cv2.TM_SQDIFF_NORMED']
            
    for method in methods:
        method = eval(method)
        
        res = cv2.matchTemplate(img, template, method)
        loc = np.where( res >= threshold)
        
        for pt in zip(*loc[::-1]):
            return True
        print(loc)
        if loc:
            return True
    
    return False
   
def bf_matches_orb(img1, img2):#Brute-Force Matching with ORB Descriptors
    orb = cv2.ORB_create()
    
    kp1, des1 = orb.detectAndCompute(img1,None)
    kp2, des2 = orb.detectAndCompute(img2,None)
        
    bf = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=True)
    matches = bf.match(des1,des2)
    matches = sorted(matches, key = lambda x:x.distance)
    
    #ici threshold c'est une distance
    threshold = 60
    for x in matches:
        print(x.distance)
    if len(list(filter(lambda x: x.distance<threshold, matches)))>  50:
        return True
    return False

#def other_compare(img1, img2):
    #MIN_MATCH_COUNT = 10
    
    ## Initiate ORB detector
    #orb = cv2.ORB_create()

    ## find the keypoints and descriptors with SIFT
    #kp1, des1 = orb.detectAndCompute(img1,None)
    #kp2, des2 = sift.detectAndCompute(img2,None)

    #FLANN_INDEX_KDTREE = 0
    #index_params = dict(algorithm = FLANN_INDEX_KDTREE, trees = 5)
    #search_params = dict(checks = 50)

    #flann = cv2.FlannBasedMatcher(index_params, search_params)

    #matches = flann.knnMatch(des1,des2,k=2)

    ## store all the good matches as per Lowe's ratio test.
    #good = []
    #for m,n in matches:
        #if m.distance < 0.7*n.distance:
            #good.append(m)
            
    #return len(good)>MIN_MATCH_COUNT
    
def find_similarities(files, threshold=50):#O(n² moche, on peut faire de l'extraction de features, puis indexation  see opencv doc
    
    method = eval('cv2.TM_CCOEFF')
    similarities = []
    for file1 in files:
        for file2 in files:
            if file1.md5 != file2.md5:
                img1 = cv2.imread(scheduler.get_file( file1.md5 ).name,cv2.IMREAD_GRAYSCALE) 
                img2 = cv2.imread(scheduler.get_file( file2.md5 ).name,cv2.IMREAD_GRAYSCALE) 
               
                h1, w1 = img1.shape
                h2, w2 = img2.shape
                
                if h2<=h1 and w2<=w1 and basic_compare(img1, img2, threshold):
                #if h2<=h1 and w2<=w1 and bf_matches_orb(img1, img2):
                #if h2<=h1 and w2<=w1 and other_compare(img1, img2):
                    similarities.append( (file1,file2) )

    return similarities

#cv2.imshow('image',img1)
#cv2.waitKey(0)
#cv2.destroyAllWindows()
#r1 = cv2.compareHist(hist1, hist2, 0)
#print("Correlation %f" % r1)

#r2 = cv2.matchTemplate(img1, img2, cv2.CV_TM_SQDIFF)
#print("Template match %f" % r1)

#plt.plot(hist, color="r")
#plt.xlim([0,256])
#plt.show()
