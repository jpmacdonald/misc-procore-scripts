import re
import glob
import os
import pathlib
import tempfile
import numpy as np
import imutils
import cv2
import pytesseract as pyt
from PIL import Image, ImageEnhance, ImageFilter
from PyPDF2 import PdfFileReader, PdfFileWriter
from typing import NamedTuple
from pdf2image import convert_from_path, convert_from_bytes

class Drawing:
    number = ""
    plan = ""
    date = ""
    project_number = ""

    def __init__(self, number="", plan= "", date= "", project_number= ""):
        self.number = number
        self.plan = plan
        self.date = date
        self.project_number = project_number

def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=5.0, threshold=0):
    blurred = cv2.GaussianBlur(image, kernel_size, sigma)
    sharpened = float(amount + 1) * image - float(amount) * blurred
    sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
    sharpened = np.minimum(sharpened, 255 * np.ones(sharpened.shape))
    sharpened = sharpened.round().astype(np.uint8)
    if threshold > 0:
        low_contrast_mask = np.absolute(image - blurred) < threshold
        np.copyto(sharpened, image, where=low_contrast_mask)
    return sharpened


def preprocess(image):
    img = cv2.resize(image, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
    img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    kernel = np.ones((5, 5), np.uint8)
    img = cv2.dilate(img, kernel, iterations=1)
    img = cv2.erode(img, kernel, iterations=1)
    img = cv2.GaussianBlur(img, (5, 5), 0)
    img = cv2.threshold(cv2.medianBlur(img, 3), 200, 255,
                        cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]
    img = unsharp_mask(img)
    return img


def crop(filename):
    image = cv2.imread(filename)
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray = 255*(gray < 128).astype(np.uint8)
    coords = cv2.findNonZero(gray)
    x, y, w, h = cv2.boundingRect(coords)
    result = image[y:y+h, x:x+w]
    return result


def remove_lines(image):
    result = image.copy()
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    thresh = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)[1]

    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (40, 1))
    remove_horizontal = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    cnts = cv2.findContours(
        remove_horizontal, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, (255, 255, 255), 5)

    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, 40))
    remove_vertical = cv2.morphologyEx(
        thresh, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    cnts = cv2.findContours(
        remove_vertical, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] if len(cnts) == 2 else cnts[1]
    for c in cnts:
        cv2.drawContours(result, [c], -1, (255, 255, 255), 5)
    return result


def select_roi(filename):
    image = cv2.imread(filename, 0)
    image = imutils.resize(image, width=4000)
    image_copy = image.copy()

    coordinates = []

    def shape_selection(event, x, y, flags, param):
        global coordinates
        if event == cv2.EVENT_LBUTTONDOWN:
            coordinates = [(x, y)]
        elif event == cv2.EVENT_LBUTTONUP:
            coordinates.append((x, y))
            cv2.rectangle(image, coordinates[0],
                          coordinates[1], (0, 0, 255), 2)
            cv2.imshow("image", image)

    cv2.namedWindow("image")
    cv2.setMouseCallback("image", shape_selection)
    key = cv2.waitKey(1) & 0xFF
    while key != ord('q'):
        cv2.imshow("image", image)
        key = cv2.waitKey(1) & 0xFF

        if key == ord('\n'):
            break
        if key == ord('c'):
            image = image_copy.copy()

    if len(coordinates) == 2:
        image_roi = image_copy[coordinates[0][1]:coordinates[1][1],
                               coordinates[0][0]:coordinates[1][0]]
        cv2.imshow(
            "Selected Region of Interest - Press any key to proceed", image_roi)
        cv2.waitKey(0)
    cv2.destroyAllWindows()


def get_drawing(filename):
    print(filename)
    pages = convert_from_path(filename)
    for page in pages:
        page.save(f'{filename}.png', 'PNG')
    image = cv2.imread(filename + '.png')
    img = imutils.resize(image, width=4000)
    img = remove_lines(img)

    roi_coord = [(3543, 2406), (3968, 2852)]
    image_roi = img[roi_coord[0][1]:roi_coord[1]
                    [1], roi_coord[0][0]:roi_coord[1][0]]
    image_roi = cv2.resize(image_roi, None, fx=5, fy=5,
                           interpolation=cv2.INTER_CUBIC)

    image_roi = preprocess(image_roi)
    cv2.threshold(img, 200, 255, cv2.THRESH_BINARY)

    text = pyt.image_to_string(image_roi, lang='eng',
                               config='--psm 3 --oem 3 -c tessedit_char_whitelist=\ -:.ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789')

    date_pattern = re.compile(r'\d{1,2} [A-Z]+ \d{4}')
    project_pattern = re.compile(r'\d+\.\d+\.[A-Z]+')
    draw_num_pattern = re.compile(r'[A-Z]+-*?\d+[A-Z]*(\.\d{1,2})*?')
    draw_plan_pattern = re.compile(
        r'(KEY PLAN)*[\n\r\s]*([\s\S]*)[\n\r\s]+DRAWING TITLE')

    date = re.search(date_pattern, text)
    proj_num = re.search(project_pattern, text)
    draw_num = re.search(draw_num_pattern, text)
    draw_plan = re.search(draw_plan_pattern, text)

    d = Drawing()
    if date: d.date=date.group()
    if proj_num: d.project_number=proj_num.group()
    if draw_num: d.number=draw_num.group()
    if draw_plan: d.plan=draw_plan.group(2)
    return d


def get_drawings(filename):
    try:
        pdf = PdfFileReader(open(filename, 'rb'))
        pathlib.Path('drawings').mkdir(parents=True, exist_ok=True)
        for i in range(pdf.numPages):
            rectangle = pdf.getPage(i).mediaBox
            if ((rectangle[2]//72) * (rectangle[3]//72)) == 1260:
                output = PdfFileWriter()
                output.addPage(pdf.getPage(i))
                name, ext=os.path.splitext(os.path.basename(filename))                
                filename = f'drawings/{name}-page-{i+1}{ext}'
                with open(filename, 'wb') as outputStream:
                    output.write(outputStream)
                d = get_drawing(filename)
                print(repr(normalize(d.plan)))
                print(repr(normalize(d.number)))            
    except Exception as e:
        print(e)

def normalize(string):
    string = ' '.join(string.split())
    return string.strip()

get_drawings('data/A-008.pdf')
