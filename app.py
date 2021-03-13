import numpy as np
import cv2
from object_detector import ObjectDetector
from gesture_classifier import GestureClassifier
import webbrowser
from constants import *
from typing import List
from functools import reduce
import time


class App():
    def __init__(self):
        # camera setup
        self.cam = cv2.VideoCapture(0)
        self.width = int(self.cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        self.height = int(self.cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # detector & classifier setup
        self.search_hand = SEARCH_FOR_HAND  # when False detector uses predefined area
        self.classifier = GestureClassifier()
        self.background = None

        # other
        self.display = cv2.namedWindow("frame", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("frame", WINDOW_WIDTH, WINDOW_HEIGHT)
        cv2.moveWindow("frame", WINDOW_WIDTH//3, WINDOW_HEIGHT//3)

        # setting up hand detector
        self.hand_detector = ObjectDetector()
        # self.time_interval = 0.5  # minimal time between predictions

    def run(self):
        _, frame = self.cam.read()
        self.background = np.copy(frame)
        background_counter = 0
        background_candidate = np.copy(frame)

        while True:
            _, frame = self.cam.read()

            if background_counter > BACKGROUND_TIMER:
                frameDelta = cv2.absdiff(background_candidate, frame)
                _, thresh = cv2.threshold(frameDelta, BACKGROUND_DIFF_PIX, 1, cv2.THRESH_BINARY)
                # thresh = frameDelta

                background_change = np.sum(thresh) / np.prod(frame.shape)
                print(f"background_change={background_change}")
                print()
                if background_change < BACKGROUND_DIFF:
                    self.background = np.copy(background_candidate)
                    print("background updated")
                else:
                    print("background update failed")
                background_candidate = np.copy(frame)
                background_counter = 0
            background_counter += 1


            should_close = self.process_input()
            if should_close:
                break

            if self.search_hand:
                gestures = self.detect_objects(frame)
            else:
                gestures = [GestureData([0, 0, 1, 1], 0, 1.)]

            # cv2.cvtColor(self.background, cv2.COLOR_BGR2HSV)
            # mask = cv2.absdiff(self.background, frame)
            mask = cv2.absdiff(cv2.cvtColor(self.background, cv2.COLOR_BGR2HSV), cv2.cvtColor(frame, cv2.COLOR_BGR2HSV))
            mask = np.mean(mask, axis=2)
            _, mask = cv2.threshold(mask, 20, 255, cv2.THRESH_BINARY)

            gestures, img = self.make_predictions(gestures, mask)
            frame_to_show = self.annotate_frame(frame, gestures)

            cv2.imshow("frame", frame_to_show)
            cv2.imshow("img", img)
            # time.sleep(2)

    def annotate_frame(self, frame, gestures: List[GestureData]):
        frame_to_show = np.copy(frame)

        for hand in gestures:
            if hand.object_id != 0:
                continue

            box = hand.box
            score = hand.object_score

            p1 = (int(box[1] * self.width), int(box[0] * self.height))
            p2 = (int(box[3] * self.width), int(box[2] * self.height))
            frame_to_show = cv2.rectangle(frame_to_show, p1, p2, (0, 255, 0), 5)
            text_position = (p1[0] + 20, p2[1] - 20)

            cv2.addText(frame_to_show, f"{hand.gesture_label} conf={score:.2f}", text_position,
                        nameFont="Times",
                        pointSize=30, color=(0, 255, 255))


        cv2.displayStatusBar('frame', "to get help press 'h'")

        return frame_to_show

    def process_input(self):
        key_input = cv2.waitKey(1)
        if key_input == ord('q'):
            return True

        if key_input == ord('h'):
            webbrowser.open(
                'https://github.com/werkaaa/Python_project/blob/master/README.md',
                new=2)
        # changes between predefined area and hand searching
        if key_input == ord('a'):
            self.search_hand = not self.search_hand
        return False

    def detect_objects(self, frame):
        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        return self.hand_detector.process_image(img)

    def make_predictions(self, gestures: List[GestureData], frame):
        img = frame
        for hand in gestures:
            box = hand.box
            y1, x1 = int(box[1] * self.width), int(box[0] * self.height)
            y2, x2 = int(box[3] * self.width), int(box[2] * self.height)

            margin = 50
            x1, y1 = self._clip_image_coord(x1-margin, y1-margin)
            x2, y2 = self._clip_image_coord(x2+margin*2, y2+margin)
            img = frame[x1:x2, y1:y2] # x - vertical, y - horizontal

            label = self.classifier.classify(img)
            hand.gesture_label = label
            # hand.gesture_score = score

        return gestures, img

    def _clip_image_coord(self, x, y):
        x = np.clip(x, 0, self.height)
        y = np.clip(y, 0, self.width)
        return x, y

    def __del__(self):
        self.cam.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    App().run()
