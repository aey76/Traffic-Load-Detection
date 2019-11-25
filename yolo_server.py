###################################################################################################
# File: yolo_server.py
#
###################################################################################################
import sys, time, datetime, threading, logging

# from sys import platform

sys.path.append('./yolo3_v6')

from models import *
from utils.datasets import *
from utils.utils import *

###################################################################################################
# * YoloServer
# Wrapper class of YOLO algorithm
###################################################################################################
class YoloServer:
###################################################################################################
# * __init__: init members
###################################################################################################
    def __init__(self, byPassStr=""):
        self.weightsSource = "./yolo3_v6/weights/yolov3.weights"
        self.img_size = 416
        self.cfg = "./yolo3_v6/cfg/yolov3.cfg"
        self.data_cfg = "./yolo3_v6/data/coco.data"
        self.conf_threshold = 0.2
        self.nms_threshold = 0.2
        self.lock_key = threading.Lock()
        self.byPass = byPassStr is "ByPass"
###################################################################################################

###################################################################################################
# * setThreshold: set threshold detection
###################################################################################################
    def setThreshold(self, newThreshold):
        self.conf_threshold = newThreshold
        pass
###################################################################################################

###################################################################################################
# * loadData: load data
###################################################################################################
    def loadData(self):
        if self.byPass is True:
            return

        self.device = torch_utils.select_device()

        # Initialize model
        self.model = Darknet(self.cfg, self.img_size)

        # Load weights
        _ = load_darknet_weights(self.model, self.weightsSource)

        # Fuse Conv2d + BatchNorm2d layers
        self.model.fuse()

        # Eval mode
        self.model.to(self.device).eval()
        
        # Get classes and colors
        self.classes = load_classes("./yolo3_v6/" + parse_data_cfg(self.data_cfg)['names'])
        self.colors = [[random.randint(0, 255) for _ in range(3)] for _ in range(len(self.classes))]
###################################################################################################

###################################################################################################
# * detect: detect objects on given image
###################################################################################################
    def detect(self, rawImage, viewImage, drawBoxes):
        # start critical section to make sure only one thread using the detect function
        detToReturn = []

        if self.byPass is True:
            return viewImage, detToReturn

        with self.lock_key:
            # Get detections
            rawImage = torch.from_numpy(rawImage).unsqueeze(0).to(self.device)
            pred, _ = self.model(rawImage)
            det = non_max_suppression(pred, self.conf_threshold, self.nms_threshold)[0]

            if viewImage is not None and det is not None and len(det) > 0:
                det[:, :4] = scale_coords(rawImage.shape[2:], det[:, :4], viewImage.shape).round()

                # Print results to screen
                # for c in det[:, -1].unique():
                #     n = (det[:, -1] == c).sum()
                #     print('%g %ss' % (n, self.classes[int(c)]), end=', ')
                
                for *xyxy, conf, cls_conf, cls in det:
                    # if self.save_txt:  # Write to file
                    #     with open(self.save_path + '.txt', 'a') as file:
                    #         file.write(('%g ' * 6 + '\n') % (*xyxy, cls, conf))

                    # Add bbox to the image
                    label = '%s %.2f' % (self.classes[int(cls)], conf)
                    if self.classes[int(cls)] == "car" or self.classes[int(cls)] == "bus" or self.classes[int(cls)] == "truck":

                        # check for "big" objects, the big objects are noise and should not be handeled
                        objSizeInPixels = (int(xyxy[2])-int(xyxy[0])) * (int(xyxy[3]) - int(xyxy[1]))
                        if objSizeInPixels < 40000:
                            detToReturn.append((int(xyxy[0]), int(xyxy[1])))
                            detToReturn.append((int(xyxy[2]), int(xyxy[3])))

                            # Draw bounding boxes and labels of detections
                            if drawBoxes is True:
                                plot_one_box(xyxy, viewImage, label=label, color=self.colors[int(cls)])
                        else:
                            bigOne = 1

            return viewImage, detToReturn
###################################################################################################


###################################################################################################
# * main - test YoloServer class
###################################################################################################
if __name__ == '__main__':

    yoloServer = YoloServer()

    yoloServer.loadData()
###################################################################################################

# --- END OF FILE ---
