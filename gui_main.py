###################################################################################################
# File: gui_main.py
#
###################################################################################################

import os, sys, time, datetime, threading, logging
import gui_design_code as GUI
import camera_reader as CR
import yolo_server as YS

# to allow debuging QThreads
import ptvsd

import cv2

sys.path.append('./yolo3_v6')

from detect import *
from utils.datasets import LoadWebcam

from PyQt5 import QtGui
from PyQt5 import QtCore

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
        self.recordingOn = False
        self.graph_lock_key = threading.Lock()
        self.loadHistory_0 = [0] * 200
        self.loadHistory_1 = [0] * 200
        self.loadHistory_2 = [0] * 200
        self.loadHistoryArr = [self.loadHistory_0, self.loadHistory_1, self.loadHistory_2]
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

        # connect Start Record
        self.pushButton_StartRecord.clicked.connect(self.handleStartRecord)

        # build side views array for direct access
        self.sideViews = [self.lbl_sideView_0, self.lbl_sideView_1, self.lbl_sideView_2]
        self.progressBars = [self.progressBar_0, self.progressBar_1, self.progressBar_2]
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
# * handleStartRecord: handle recording push button
###################################################################################################
    def handleStartRecord(self):
        if self.recordingOn is False:
            self.pushButton_StartRecord.setText('Stop Recording')
            self.recordingOn = True
        else:
            self.pushButton_StartRecord.setText('Start Recording')
            self.recordingOn = False
###################################################################################################

###################################################################################################
# * isRecordingActive: Return the recording state
###################################################################################################
    def isRecordingActive(self):
        return self.recordingOn
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
# * setLoadProgressBar: set the traffic load bar of view
###################################################################################################
    def setLoadProgressBar(self, camIndex, trafficLevel):
        self.progressBars[camIndex].setValue(min(trafficLevel, 200))

        self.loadHistoryArr[camIndex].append(int(trafficLevel / 2))
        self.loadHistoryArr[camIndex].pop(0)
        self.updateGraph()
###################################################################################################

###################################################################################################
# * getViewsCount: return maximum number of views the UI can handle
###################################################################################################
    def getViewsCount(self):
        return 3
###################################################################################################

###################################################################################################
# * updateGraph: plot the 3 loadHistory lists
###################################################################################################
    def updateGraph(self):

        with self.graph_lock_key:
            self.MplWidget.canvas.axes.clear()
            self.MplWidget.canvas.axes.set_ylabel("traffic load")
            self.MplWidget.canvas.axes.set_ylim(0, 100)
            self.MplWidget.canvas.axes.plot(self.loadHistory_0)
            self.MplWidget.canvas.axes.plot(self.loadHistory_1)
            self.MplWidget.canvas.axes.plot(self.loadHistory_2)
            #self.MplWidget.canvas.axes.set_title('Traffic Load Graph')
            self.MplWidget.canvas.draw()
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
# * TrafficLoad
#
###################################################################################################
class TrafficLoad():

###################################################################################################
# * __init__: init super class and init members
###################################################################################################
    def __init__(self):
        self.loadMatrix = []
        self.img0WidthPixels = 0
        self.img0HeightPixels = 0
        self.img0WidthBoxes = 0
        self.img0HeightBoxes = 0
###################################################################################################

###################################################################################################
# * setImageDimensions:
###################################################################################################
    def setImageDimensions(self, imgShape):
        self.img0WidthPixels = imgShape[1]
        self.img0HeightPixels = imgShape[0]
        self.img0WidthBoxes = int(self.img0WidthPixels / 20) + 1
        self.img0HeightBoxes = int(self.img0HeightPixels / 20) + 1

        if len(self.loadMatrix) == 0:
            self.loadMatrix = [0] * (self.img0WidthBoxes * self.img0HeightBoxes)
###################################################################################################

###################################################################################################
# * processDetectionList: Process detection list
###################################################################################################
    def processDetectionList(self, detectionList):
        newLoadMatrix = [0] * (self.img0WidthBoxes * self.img0HeightBoxes)

        i = 0
        while i < len(detectionList):
            x1, y1 = detectionList[i]
            x2, y2 = detectionList[i + 1]

            # handle detections on the edge of the image
            x1 = min(self.img0WidthPixels - 1, x1)
            y1 = min(self.img0HeightPixels - 1, y1)
            x2 = min(self.img0WidthPixels - 1, x2)
            y2 = min(self.img0HeightPixels - 1, y2)

            x1 = int(x1 / 20)
            y1 = int(y1 / 20)
            x2 = int(x2 / 20)
            y2 = int(y2 / 20)

            for y in range(y1, y2+1):
                for x in range(x1, x2+1):
                    newLoadMatrix[y * self.img0WidthBoxes + x] = self.loadMatrix[y * self.img0WidthBoxes + x] + 1

            i += 2

        self.loadMatrix = newLoadMatrix

        # Count numbers in the list
        trafficLoadValue = sum(map(lambda x : x > 10, self.loadMatrix))
        return trafficLoadValue
###################################################################################################

###################################################################################################
# * drawTrafficGrid: Draw a grid lines
###################################################################################################
    def drawTrafficGrid(self, img0):
        for y in range(0, self.img0HeightPixels, 20):
            img0 = cv2.line(img0, (0, y), (self.img0WidthPixels, y), (100,100,100), 1)

        for x in range (0, self.img0WidthPixels, 20):
            img0 = cv2.line(img0, (x, 0), (x, self.img0HeightPixels), (100,100,100), 1)
###################################################################################################

###################################################################################################
# * drawTrafficLoad: Process detection list
###################################################################################################
    def drawTrafficLoad(self, img0):
        i = 0
        while i < len(self.loadMatrix):
            if self.loadMatrix[i] > 2:
                v = self.loadMatrix[i]
                c1 = divmod(i, self.img0WidthBoxes)
                c1 = (c1[1] * 20, c1[0] * 20)
                c2 = (c1[0] + 19, c1[1] + 19)
                r = min (255, v * 15)
                cv2.rectangle(img0, c1, c2, [0, 0, r], thickness=3)
            i += 1
###################################################################################################

###################################################################################################
# * ProcessThreadClass
#
###################################################################################################
class ProcessThreadClass(QtCore.QThread):

    # QT Signals must be public to allow connection from other classes
    updateTrafficLoadSignal = QtCore.pyqtSignal(int, int)

    def __init__(self, ui, yolo, camIndex):
        super().__init__()
        self.ui_ = ui
        self.yolo_ = yolo
        self.camIndex_ = camIndex

        # process source according to camIndex and create cam reader
        f = open("sources.txt", "r")
        sourcesList = [line for line in f]
        f.close()

        sourceLine = sourcesList[9 + camIndex]

        if sourceLine.startswith("http"):
            # trim the file name from __file__ (__file__ is the full path of the file with the file name)
            mainPyPath = __file__[0 : -len(os.path.basename(__file__))]
            imagesPath = mainPyPath + "images\\url_" + str(camIndex)
            sourceLineSplit = sourceLine.split(",")
            self.cam = CR.CamReader(sourceLineSplit[0], int(sourceLineSplit[1]), imagesPath)
        else:
            self.cam = CR.DirReader(sourceLine.split("\n")[0])

    def run(self):
        # make this thread debug-able
        ptvsd.debug_this_thread()

        # take self variables to local variables just to make coding easy
        ui = self.ui_
        yolo = self.yolo_
        camIndex = self.camIndex_

        ui.log("Background thread " + str(camIndex) + " start to run...")

        trafficLoad = TrafficLoad()
        
        while True:
            sleepToRoundUs(1000000, 100000 * camIndex)
            messageToLog = self.cam.recordImages(ui.isRecordingActive())
            if len(messageToLog) > 0:
                ui.log(messageToLog)
            imgToProcess, imgToShow = self.cam.nextFrame()
            # ui.log("CamReader buffer len " + str(cam.getImagesCount()))
            if imgToProcess is not None:
                img0, detectionList = yolo.detect(imgToProcess, imgToShow, ui.checkBox_drawBoxes.isChecked())
                
                trafficLoad.setImageDimensions(img0.shape)

                trafficLoadValue = trafficLoad.processDetectionList(detectionList)
                self.updateTrafficLoadSignal.emit(camIndex, trafficLoadValue)

                if ui.checkBox_drawGrid.isChecked() is True:
                    trafficLoad.drawTrafficGrid(img0)

                if ui.checkBox_drawStaticObjects.isChecked() is True:
                    trafficLoad.drawTrafficLoad(img0)

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
    yolo = YS.YoloServer("") # ByPass
    ui = Ui_MainWindowLogic(yolo)
    
    ui.setupUi(qtMainWindow)
    qtMainWindow.setWindowTitle("Roads 0.3.0")
    qtMainWindow.show()

    yolo.loadData()

    # create and start processThread
    threads = [None] * 3
    for i in range(0, 3):
        threads[i] = ProcessThreadClass(ui, yolo, i)
        threads[i].updateTrafficLoadSignal.connect(ui.setLoadProgressBar)
        threads[i].start()
        
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
