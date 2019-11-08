###################################################################################################
# File: gui_main.py
#
###################################################################################################
import sys, time, datetime, threading, logging
import gui_design_code as GUI
import camera_reader as CR
import yolo_server as YS

import cv2

sys.path.append('./yolo3_v6')

from detect import *
from utils.datasets import LoadWebcam

###################################################################################################
# * Ui_MainWindowLogic
#
###################################################################################################
class Ui_MainWindowLogic(GUI.Ui_MainWindow):

###################################################################################################
# * __init__: init super class and init members
###################################################################################################
    def __init__(self, yoloServer):
        super().__init__()
        self.activeViewIndex = 0
        self.logLinesCount = 0
        self.yoloServer = yoloServer
###################################################################################################

###################################################################################################
# * setupUi: setupUi super class connect events
###################################################################################################
    def setupUi(self, MainWindow):
        super().setupUi(MainWindow)
        self.log("GUI init start")

        # connect side windows mouse-press events
        self.lbl_sideView_0.mousePressEvent = lambda ev: self.setActiveView(0)
        self.lbl_sideView_1.mousePressEvent = lambda ev: self.setActiveView(1)
        self.lbl_sideView_2.mousePressEvent = lambda ev: self.setActiveView(2)
        
        # connect sensitivity slidbar event
        self.slider_sensitivity.valueChanged.connect(self.handleSensitivity)

        # build side views array for direct access
        self.sideViews = [self.lbl_sideView_0, self.lbl_sideView_1, self.lbl_sideView_2]
###################################################################################################

###################################################################################################
# * setActiveView: handle changing active view
###################################################################################################
    def setActiveView(self, newViewIndex):
        if self.activeViewIndex is not newViewIndex:
            self.log("setActiveWindow " + str(newViewIndex))
            self.activeViewIndex = newViewIndex
###################################################################################################

###################################################################################################
# * handleSensitivity: handle changing ...
###################################################################################################
    def handleSensitivity(self):
        newThreshold = self.slider_sensitivity.value() / self.slider_sensitivity.maximum()
        self.yoloServer.setThreshold(newThreshold)
        self.log("Detection sensitivity: " + str(newThreshold))
###################################################################################################

###################################################################################################
# * log: add log message to logging window
###################################################################################################
    def log(self, logMessage):
        self.logLinesCount += 1
        self.txt_Log.append(str(self.logLinesCount) + ". " + logMessage)
        self.txt_Log.ensureCursorVisible()
###################################################################################################

###################################################################################################
# * setViewImage: set the image of specific view
# convert the image from CV2 format to QT format and update the views
###################################################################################################
    def setViewImage(self, viewIndex, img):
        qformat = GUI.QtGui.QImage.Format_Indexed8
        if len(img.shape) == 3:
            if img.shape[2] == 4:
                qformat = GUI.QtGui.QImage.Format_RGBA8888
            else:
                qformat = GUI.QtGui.QImage.Format_RGB888
            img2 = GUI.QtGui.QImage(img.data,
                img.shape[1],
                img.shape[0], 
                img.strides[0], # <--- +++
                qformat)
            img2 = img2.rgbSwapped()

            self.sideViews[viewIndex].setPixmap(GUI.QtGui.QPixmap.fromImage(img2))
            if self.activeViewIndex == viewIndex:
                self.lbl_mainView.setPixmap(GUI.QtGui.QPixmap.fromImage(img2))
###################################################################################################

###################################################################################################
# * setViewState: set the state of specific view
###################################################################################################
    def setViewState(self, viewIndex, state):
        pass
###################################################################################################

###################################################################################################
# * getViewsCount: return maximum number of views the UI can handle
###################################################################################################
    def getViewsCount(self):
        return 3
###################################################################################################



###################################################################################################
# * sleepToRoundUs
#
###################################################################################################
def sleepToRoundUs(roundUs, offsetUs):
    now = datetime.datetime.now()
    usToSleep = roundUs - (now.microsecond % roundUs)
    time.sleep((offsetUs + usToSleep) / 1000000.0)
###################################################################################################

###################################################################################################
# * CarsLoad
#
###################################################################################################
class CarsLoad():

###################################################################################################
# * __init__: init super class and init members
###################################################################################################
    def __init__(self):
        self.loadMatrix = [0] * (32 * 18)
###################################################################################################

###################################################################################################
# * clear: clear loadArray
###################################################################################################
    def clear(self):
        self.loadMatrix = [0] * (32 * 18)
###################################################################################################

###################################################################################################
# * processDetectionList: Process detection list
###################################################################################################
    def processDetectionList(self, detectionList):
        newLoadMatrix = [0] * (32 * 18)

        i = 0
        while i < len(detectionList):
            x1, y1 = detectionList[i]
            x2, y2 = detectionList[i + 1]

            # handle detections on the edge of the image
            x1 = min(1279, x1)
            y1 = min(719, y1)
            x2 = min(1279, x2)
            x2 = min(719, y2)

            x1 = int(x1 / 40)
            y1 = int(y1 / 40)
            x2 = int(x2 / 40)
            y2 = int(y2 / 40)

            y = y1
            while y <= y2:
                x = x1
                while x <= x2:
                    newLoadMatrix[y * 32 + x] = self.loadMatrix[y * 32 + x] + 1
                    x += 1
                y += 1

            i += 2

        self.loadMatrix = newLoadMatrix
###################################################################################################

###################################################################################################
# * drawTrafficLoad: Process detection list
###################################################################################################
    def drawTrafficLoad(self, img0, drawStaticObjects, drawGrid):

        # Draw a grid lines
        if drawGrid:
            for y in range(0, 719, 40):
                img0 = cv2.line(img0, (0,y), (1280,y), (100,100,100), 1)

            for x in range (0, 1279, 40):
                img0 = cv2.line(img0, (x,0), (x,720), (100,100,100), 1)

        if drawStaticObjects:
            i = 0
            while i < len(self.loadMatrix):
                if self.loadMatrix[i] > 2:
                    v = self.loadMatrix[i]
                    c1 = divmod(i, 32)
                    c1 = (c1[1] * 40, c1[0] * 40)
                    c2 = (c1[0] + 39, c1[1] + 39)
                    r = min (255, v * 15)
                    cv2.rectangle(img0, c1, c2, [0, 0, r], thickness=v)
                i += 1
###################################################################################################

###################################################################################################
# * processThread
#
###################################################################################################
def processThread(ui, yolo, camIndex):
    ui.log("Background thread " + str(camIndex) + " running...")

    urls = ["https://5c328052cb7f5.streamlock.net/live/OHALIM.stream/playlist.m3u8",    # 25Hz
            "https://5c328052cb7f5.streamlock.net/live/AHISEMECH.stream/playlist.m3u8",
            "https://5d8c50e7b358f.streamlock.net/live/OFAKIM.stream/playlist.m3u8"]    # 25Hz
            # https://5c328052cb7f5.streamlock.net/live/YAARHEDERA.stream/playlist.m3u8 25Hz
    imagesPath = "D:/YOLO/gui/images/url_" + str(camIndex)
    cam = CR.CamReader(urls[camIndex], 25, imagesPath)
    # cam = CR.CamReader(urls[camIndex], 25)
    # cam = CR.DirReader(imagesPath, 25)
    carsLoad = CarsLoad()
    

    while True:
        sleepToRoundUs(1000000, 100000 * camIndex)
        imgToProcess, imgToShow = cam.nextFrame()
        # ui.log("CamReader buffer len " + str(cam.getImagesCount()))
        if imgToProcess is not None:
            img0, detectionList = yolo.detect(imgToProcess, imgToShow, ui.checkBox_drawBoxes.isChecked())
            carsLoad.processDetectionList(detectionList)
            carsLoad.drawTrafficLoad(img0, ui.checkBox_drawStaticObjects.isChecked(), ui.checkBox_drawGrid.isChecked())
            ui.setViewImage(camIndex, img0)
###################################################################################################

###################################################################################################
# * drawMainWindow : initiating main QT window and the processing thread in the background
# ! Note: This function never returns.
###################################################################################################
def drawMainWindow():
    # main objects
    app = GUI.QtWidgets.QApplication(sys.argv)
    qtMainWindow = GUI.QtWidgets.QMainWindow()
    yolo = YS.YoloServer()
    ui = Ui_MainWindowLogic(yolo)
    
    ui.setupUi(qtMainWindow)
    qtMainWindow.setWindowTitle("Roads 0.2.0")
    qtMainWindow.show()

    yolo.loadData()

    # start processThread as demon thread
    threads = []
    threads.append(threading.Thread(target=processThread, args=(ui, yolo, 0), daemon=True))
    threads.append(threading.Thread(target=processThread, args=(ui, yolo, 1), daemon=True))
    threads.append(threading.Thread(target=processThread, args=(ui, yolo, 2), daemon=True))

    threads[0].start()
    # threads[1].start()
    # threads[2].start()

    retCode = app.exec_()
    sys.exit(retCode)
###################################################################################################

###################################################################################################
# * main: call drawMainWindow
###################################################################################################
if __name__ == "__main__":
    drawMainWindow()
###################################################################################################

# --- END OF FILE ---
