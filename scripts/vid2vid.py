import math
import os
import sys
import traceback

import modules.scripts as scripts
import gradio as gr

from modules.processing import Processed, process_images
from PIL import Image
from modules.shared import opts, cmd_opts, state



from subprocess import Popen, PIPE
import numpy as np
import sys

class ffmpeg:
    def __init__(self, cmdln, use_stdin=False, use_stdout=False, use_stderr=False, print_to_console=True):
        self._process = None
        # self._use_stdin = use_stdin
        # self._use_stdout = use_stdout
        # self._use_stderr = use_stderr
        self._cmdln = cmdln
        self._stdin = None
        
        if use_stdin:
            self._stdin = PIPE
            
        self._stdout = None
        self._stderr = None
        
        if print_to_console:
            self._stderr = sys.stdout
            self._stdout = sys.stdout
            
        if use_stdout:
            self._stdout = PIPE
           #self._qq = BytesIO()
            #self._stdout = self._qq.fileno()
            
        if use_stderr:
            self._stderr = PIPE

        self._process = None
        

    def start(self):
        self._process = Popen(
            self._cmdln
            , stdin=self._stdin
            , stdout=self._stdout
            , stderr=self._stderr
        )
        #from io import BufferedWriter,BufferedReader
        #self.writer = BufferedWriter(self._process.stdin)
        #self.reader = BufferedReader(self._process.stdout)

    # read  cnt bytes as np array uint8
    def readout(self, cnt=None):
        #self.reader.flush()

        #buf = self._process.stdout.read(cnt)
        if cnt is None:
            buf = self._process.stdout.read()
        else:
            buf = self._process.stdout.read(cnt)
        arr = np.frombuffer(buf, dtype=np.uint8)
        #print(cnt)
        #print(type(arr))
        #print(arr.shape)        
        #print(len(arr)) 
        #print("")        
        return arr

    def readerr(self, cnt):
        buf = self._process.stderr.read(cnt)
        return np.frombuffer(buf, dtype=np.uint8)

    def write(self, arr):
        bytes = arr.tobytes()
        #print()
        print(arr.shape)
        print()
        #self._process.stdin.write(bytes)
        self._process.stdin.write(bytes)
        #self.writer.flush()
        #self._process.stdin.flush()


    def write_eof(self):
        if self._stdin != None:
            self._process.stdin.close()

    def is_running(self):
        return self._process.poll() is None



class Script(scripts.Script):
    def title(self):
        return "vid2vid"

    def show(self, is_img2img):
        return is_img2img

    def ui(self, is_img2img):
        input_path = gr.Textbox(label="Input file path", lines=1)
        output_path = gr.Textbox(label="Output file path", lines=1)

        return [input_path, output_path]

    def run(self, p, input_path, output_path):
        p.do_not_save_grid = True
        p.do_not_save_samples = True
        
        ff_write_file = 'ffmpeg -y -loglevel panic -f rawvideo -pix_fmt rgb24 -s:v {0}x{1} -r 1 -i - -c:v libx264 -preset fast -crf 24 ?filename?'
        
        #ff_write_file = 'ffmpeg -y -loglevel panic -f rawvideo -pix_fmt rgb24 -s:v {0}x{1} -r 24 -i - -c:v libx264 -preset fast -crf 24 ?filename?'
        ff_write_file = ff_write_file.format(p.width, p.height).replace("?filename?", output_path)
        #print('file write')
        #print(ff_write_file)
        ff_write_file = ff_write_file.split(' ')       
        #ff_read_file = 'ffmpeg -y -loglevel panic -ss 00:00:00 -t 00:00:01 -i "?filename?" -s:v {0}x{1} -vf fps=24 -f image2pipe -pix_fmt rgb24 -c:v rawvideo -'
        ff_read_file = 'ffmpeg -loglevel panic -ss 00:00:20 -t 00:00:50 -i ?filename? -s:v {0}x{1} -vf fps=1 -f image2pipe -pix_fmt rgb24 -vcodec rawvideo -'
        ff_read_file = ff_read_file.format(p.width, p.height).replace("?filename?", input_path)
        #print('file read')
        #print(ff_read_file)
      
        ff_read_file = ff_read_file.split(' ')
        #print('file read')
        #print(ff_read_file)  
        #print('file read')
        #print(ff_read_file)  
        #ff_read_file[5] = input_path
        encoder = ffmpeg(ff_write_file, use_stdin=True)
        decoder = ffmpeg(ff_read_file, use_stdout=True)
        encoder.start()
        decoder.start()
        
        pull_cnt = p.width*p.height*3
        frame_num = 0
        import time
        import cv2
        from cv2 import cvtColor, COLOR_BGR2RGB
        cv2.startWindowThread()
        cv2.namedWindow("vid2vid streamig")

        first_frame = True
        while True:            
            #print()
            #print(ff_write_file)
            #print()            
                            
            np_image = decoder.readout(pull_cnt)  
            if len(np_image)==0:
                break;
            PIL_image = Image.fromarray(np.uint8(np_image).reshape((p.height,p.width, 3)), mode="RGB" )
            frame_num += 1            
            state.job = f"{frame_num} frames processed"
            p.init_images = [PIL_image]
            proc = process_images(p)  
            if len(proc.images)==0:
                break;
            PIL_image = proc.images[0]
            img_rgb = cvtColor(np.array(PIL_image), COLOR_BGR2RGB)
            cv2.imshow('vid2vid streamig',img_rgb) 
            cv2.waitKey(1)
            if first_frame:
                #cv2.waitKey(1)
                first_frame = False
            else:
                #cv2.waitKey(1)
                pass
            np_image = np.asarray(PIL_image)
            encoder.write(np_image)
        encoder.write_eof()
        #cv2.destroyAllWindows() 
        
        return Processed(p, [], p.seed, "")
