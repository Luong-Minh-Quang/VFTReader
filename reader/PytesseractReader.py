import traceback
from control.ExtractionControl import ExtractionControl
from typing import Text
from reader.ReportReader import ReportReader
from datetime import datetime
from tkinter import EventType

from models.VFTReport import VFTReport
import pytesseract
from PIL import Image
import pdf2image
import os
import numpy as np
import re
from math import floor

class PytesseractReader(ReportReader):

    def __init__(self) -> None:
        #TODO: Find a way to set the path for pytesseract
        pytesseract.pytesseract.tesseract_cmd = "C:/Program Files/Tesseract-OCR/tesseract.exe"
        self.poppler =  "C:/Users/HP - PC/Downloads/poppler-0.68.0_x86/poppler-0.68.0/bin"
        self.patterns = {
            "Name": re.compile("Patient:\s*(.*)"),
            "Birth": re.compile("Date of Birth:\s*(.*)"),
            "Gender": re.compile("Gender:\s*(.*)"),
            "ID": re.compile("Patient ID:\s*(.*)"),
            #"FIXMON": re.compile("Fixation Monitor: (.*)"),
            #"FIXTAR": re.compile("Fixation Target: (.*)"),
            "FIXLOS": re.compile("Fixation Losses:\s*(.*)"),
            "FPR": re.compile("False POS Errors:\s*(.*)"),
            "Duration": re.compile("Test Duration: (.*)"),
            "FNR": re.compile("False NEG Errors:\s*(.*)"),
            "Fovea": re.compile("Fovea:\s*(.*)"),
            "Pattern": re.compile(".*(\d\d\s*-\s*\d).*"),
            "Stimulus": re.compile("Stimulus:\s*(.*)\s*Date:.*"),
            "Date": re.compile("Stimulus:.*Date:\s*(.*)\s*"),
            "Background": re.compile("Background:\s*(.*)\s*Time:.*"),
            "Time": re.compile("Background:.*Time:\s*(.*)\s*"),
            "Strategy": re.compile("Strategy:\s*(.*)\s*Age:.*"),
            "Age": re.compile("Strategy:.*Age:\s*(.*)\s*"),
            "GHT": re.compile("GHT:\s*(.*)"),
            "VFI": re.compile("VFI:\s*(.*)"),
            "MD": re.compile("MD\d+-\d+:\s*(.*)"),
            "MDp": re.compile("MD\d+-\d+:\s*.*(P\s*<\s*.*%)"),
            "PSD": re.compile("PSD\d+-\d+:\s*(.*)"),
            "PSDp": re.compile("PSD\d+-\d+:\s*.*(P\s*<\s*.*%)"),
            "Name": re.compile("Patient: (.*)")
        }
        self.values = {}
        self.numdB_pattern = re.compile('FIELD\s*(\S*)\s*FIELD')
        
        self.numdB_aux = Image.open("numdB_aux.png")
     

    #report_height = 2340
    #report_width = 1655
    def read(self, dir, curActivity: ExtractionControl):
        filelist = []
        reportList = []
        self.curActivity = curActivity
        for filename in os.listdir(dir):
            if filename.endswith(".Pdf"): 
                filelist.append(filename) 
        length =len(filelist)
        curActivity.logNumFiles(length)
        i = 0
        for filename in filelist:
            try:

                curActivity.logCurFile(filename, i, length)
                i+=1
                reportList.append(self.readfile(dir, filename))
                curActivity.refresh()
            except Exception as e:
                curActivity.logError()
                traceback.print_exc()
                
            
                
        return reportList
    def pdf_to_img(self, pdf_file):
        #TODO: Same for poppler
        return pdf2image.convert_from_path(pdf_file, poppler_path= self.poppler)

    def ocr_num(self, image):
        text = pytesseract.image_to_string(image, config= "--psm 7 -c tessedit_char_whitelist=FIELD-<0123456789")
        return text

    def ocr_core(self, file):
        text = pytesseract.image_to_string(file)
        return text
    def concat_images(self, imga, imgb):
        """
        Combines two color image ndarrays side-by-side.
        """
        print("imga: ", imga.shape)
        print("imgb: ", imgb.shape)
        ha,wa = imga.shape[:2]
        hb,wb = imgb.shape[:2]
        max_height = np.max([ha, hb])
        total_width = wa+wb
        new_img = np.zeros(shape=(max_height, total_width, 3))
        new_img[:ha,:wa]=imga
        new_img[:hb,wa:wa+wb]=imgb
        return new_img

    def concat_n_images(self, image_list):
        """
        Combines N color images from a list of image paths.
        """
        output = None
        for i, img in enumerate(image_list):
            if i==0:
                output = img
            else:
                output = self.concat_images(output, img)
        return output

    def readfile(self, dir, filename):
        if "OD" in filename:
            eyeSide = "Right"
        elif "OS" in filename:
            eyeSide = "Left"
        
        pdf_file = os.path.join(dir, filename)
        images = self.pdf_to_img(pdf_file)
        self.curActivity.refresh()
        for pg, img in enumerate(images):
            arr = np.array(img)
            #Crop graphs
            sensGraph = img.crop((361, 622, 852, 1115))
            MDGraph = img.crop((190, 1090, 518, 1416))
            PSDGraph = img.crop((700, 1090, 1028, 1416))
            resultInfo = img.crop((1100, 1250, 1600, 1550))
            
            #Delete axis from graph
            sensGraph_arr = np.array(sensGraph)
            MDGraph_arr = np.array(MDGraph)         
            PSDGraph_arr = np.array(PSDGraph)
            #Refresh is called to prevent "not responding" program
            self.curActivity.refresh()

            arr[0:230, 910:1150] = (255,255,255)
            arr[320:380, :1100] = (255, 255, 255)
            arr[622:1100, 300:1500] = (255, 255, 255)
            arr[1100:, :] = (255, 255, 255)

            cropped = Image.fromarray(arr)
      
            #main_pattern = re.compile('Patient: (.*)\n*Date of Birth: (.*)\n*Gender: (.*)\n*Patient ID: (.*)\n*Fixation Monitor: (.*)\n*Fixation Target: (.*)\n*Fixation Losses: (.*)\n*False POS Errors: (.*)\n*False NEG Errors: (.*)\n*Test Duration: (.*)\n*Fovea: (.*)\n*.*(\d\d\s*-\s*\d).*\n*Stimulus: (.*) Date: (.*)\n*Background: (.*) Time: (.*)\n*Strategy: (.*) Age: (.*)')
            main_text = self.ocr_core(cropped)
            print(main_text)
            
            #Refresh is called to prevent "not responding" program
            
            self.curActivity.refresh()
            #test_results_pattern = re.compile('GHT:\s*(.*)\n*VFI:\s*(.*)\n*MD\d+-\d+:\s*(.*)(P\s*<\s*.*%)\n*PSD\d+-\d+:\s*(.*)(P\s*<\s*.*%)')
            test_result_text = self.ocr_core(resultInfo)
            print(test_result_text)
            fulltext = main_text + "\n" + test_result_text
            for k, v in self.patterns.items():
                match = v.search(fulltext)
                if match:
                    self.values[k] = match.group(1)
                else:
                    self.values[k] = ""
            try:
                FIXLOS, FIXTST = self.values["FIXLOS"].split("/")
            except ValueError:
                FIXLOS = self.values["FIXLOS"]
                FIXTST = ""
            #Refresh is called to prevent "not responding" program
            self.curActivity.refresh()
            return VFTReport(filename, eyeSide, self.values["Date"] + " " + self.values["Time"], self.values["Age"],self.values["ID"], FIXLOS, FIXTST, self.values["FNR"], self.values["FPR"], self.values["Duration"],self.values["GHT"], self.values["VFI"], self.values["MD"], self.values["MDp"], self.values["PSD"], self.values["PSDp"],  self.values["Pattern"], self.values["Strategy"], self.values["Stimulus"], self.values["Background"], self.values["Fovea"] ,self.image2data(sensGraph_arr), self.image2data(MDGraph_arr), self.image2data(PSDGraph_arr), 0)




    def image2data(self, image):
        
        image[(floor(image.shape[1]/2)-6):(floor(image.shape[1]/2)+6),:] = (255, 255, 255)
        image[:, (floor(image.shape[0]/2)-6):(floor(image.shape[0]/2)+6)] = (255, 255, 255)
        

        
        index = 0
        arr = [[0 for i in range(10)] for j in range(10)]
        
        
        for i in range(10):
            for j in range(10):
                val_img = Image.fromarray(image[floor(i * image.shape[0] / 10):floor((i+1) * image.shape[0] / 10),floor(j * image.shape[0] / 10):floor((j+1) * image.shape[0] / 10)])
                val_img.resize((50, 50))
                images = [self.numdB_aux.copy(), val_img, self.numdB_aux.copy()]
                widths, heights = zip(*(i.size for i in images))

                total_width = sum(widths)
                max_height = max(heights)
                new_im = Image.new('RGB', (total_width, max_height), color="white")
                
                x_offset = 0
                for im in images:
                    y_offset = floor((50 - im.height)/2)
                    new_im.paste(im, (x_offset,y_offset))
                    x_offset += im.size[0]

                match = self.numdB_pattern.search(self.ocr_num(new_im))
                if match and match.group(1) != "-":
                    arr[i][j] = match.group(1)
                else:
                    arr[i][j] = ""

                
            #Refresh is called to prevent "not responding" program
            self.curActivity.refresh()
        for i in arr:
            print(i)
        print("\n"*3)
        return arr
    
    def grid(self, image):
        for i in range(10):
            image[floor(image.shape[1]/10 * i) ,:] = (0, 0, 0)
            image[:,floor(image.shape[0]/10 * i)] = (0, 0, 0)
            
        Image.fromarray(image).show()


            
