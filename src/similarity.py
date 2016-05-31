import cv2
import os
import numpy as np
import sys
from matplotlib import pyplot as plt
#sys.path.append('/usr/local/lib/python3.4/site-packages')
from lipyc.scheduler import scheduler

def find_similarities(files, threshold=0.95):#O(n² moche, on peut faire de l'extraction de features, puis indexation  see opencv doc
    similarities = []
    for file1 in files:
        for file2 in files:
            if file1.md5 != file2.md5:
                img1 = cv2.imread(scheduler.get_file( file1.md5 ).name,cv2.IMREAD_GRAYSCALE) 
                img2 = cv2.imread(scheduler.get_file( file2.md5 ).name,cv2.IMREAD_GRAYSCALE) 
                hist1 = cv2.calcHist([img1], [0], None, [256], [0,256])
                hist2 = cv2.calcHist([img2], [0], None, [256], [0,256])
                
                h1, w1 = img1.shape
                h2, w2 = img2.shape
                
                if h2<=h1 and w2<=w1:
                    template_flag = cv2.matchTemplate(img1, img2, 0) > threshold
                else:
                    template_flag = True
                
                if cv2.compareHist(hist1, hist2, 0) > threshold and template_flag:
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
