###################################################################################################
# File: camera_reader.py
#
###################################################################################################
import time, sys, threading, logging

sys.path.append('./yolo3_v6')

from detect import *
from utils.datasets import LoadWebcam

import numpy as np


def buildImageToProcess(imgToShow):
    # Padded resize (416 was height=self.img_size)
    imgToProcess, _, _, _ = letterbox(imgToShow, 1024)

    # Normalize RGB
    imgToProcess = imgToProcess[:, :, ::-1].transpose(2, 0, 1)  # BGR to RGB
    imgToProcess = np.ascontiguousarray(imgToProcess, dtype=np.float32)  # uint8 to float32
    imgToProcess /= 255.0  # 0 - 255 to 0.0 - 1.0

    return imgToProcess

###################################################################################################
# * CamReader - read and buffer images from web camera
#
###################################################################################################
class CamReader:

###################################################################################################
# * __init__: init super class and init members
# url - webcam URL
# cameraRate - the images rate from the camera
# storeImagesPath - supply directory name if want to store the images, the saved images can be
# "replayed" using DirReader class
###################################################################################################
    def __init__(self, url, cameraRate, storeImagesPath = ""):
        self.buff = []
        self.url = url
        self.cameraRate = cameraRate
        self.storeImagesPath = storeImagesPath
        self.storeImages = len(storeImagesPath) > 0
        self.bgThread = threading.Thread(target=self.bufferingThread, args=(url, ), daemon=True)
        self.bgThread.start()
###################################################################################################

###################################################################################################
# * bufferingThread: -
###################################################################################################
    def bufferingThread(self, url):
        cam = cv2.VideoCapture(url)
        imagesCount = 0
        while True:
            ret_val = cam.grab()

            if ret_val == True:
                if imagesCount % self.cameraRate == 0:
                    ret_val, img = cam.retrieve()
                    if ret_val == True:
                        self.buff.insert(0, img)
                        if self.storeImages is True:
                            cv2.imwrite(self.storeImagesPath + "/image_" + str(imagesCount) + ".png", img)
                imagesCount += 1
            else:
                cam.release()
                imagesCount = 0
                self.buff.clear()
                time.sleep(3)
                cam = cv2.VideoCapture(url)
###################################################################################################

###################################################################################################
# * getImagesCount: -
###################################################################################################
    def getImagesCount(self):
        return len(self.buff)
###################################################################################################

###################################################################################################
# * nextFrame: -
###################################################################################################
    def nextFrame(self):
        if len(self.buff) > 0:
            imgToShow = self.buff.pop()
            return buildImageToProcess(imgToShow), imgToShow
            
        return None, None
###################################################################################################


###################################################################################################
# * DirReader - read images from local directory
#
###################################################################################################
class DirReader:

###################################################################################################
# * __init__: init super class and init members
# imagesPath - directory path
# cameraRate - 
###################################################################################################
    def __init__(self, imagesPath, cameraRate):
        self.cameraRate = cameraRate
        self.imagesPath = imagesPath
        self.imagesCount = 0
###################################################################################################

###################################################################################################
# * getImagesCount: -
###################################################################################################
    def getImagesCount(self):
        return 0
###################################################################################################

###################################################################################################
# * nextFrame: read the next frame
###################################################################################################
    def nextFrame(self):
        imageName = "image_" + str(self.imagesCount) + ".png"
        imgToShow = cv2.imread(self.imagesPath + "/" + imageName,)

        if imgToShow is None:
            self.imagesCount = 0
            imageName = "image_" + str(self.imagesCount) + ".png"
            imgToShow = cv2.imread(self.imagesPath + "/" + imageName,)
            if imgToShow is None:
                return None, None

        self.imagesCount += self.cameraRate

        return buildImageToProcess(imgToShow), imgToShow
###################################################################################################

###################################################################################################
# * main: just test code for CamReader class
###################################################################################################
if __name__ == "__main__":
    pass
###################################################################################################

# --- END OF FILE ---
