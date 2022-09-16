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
        print(cnt)
        print(type(arr))
        print(arr.shape)        
        print(len(arr)) 
        print("")        
        return arr

    def readerr(self, cnt):
        buf = self._process.stderr.read(cnt)
        return np.frombuffer(buf, dtype=np.uint8)

    def write(self, arr):
        bytes = arr.tobytes()
        print()
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
        
        ff_write_file = 'ffmpeg -y -loglevel panic -f rawvideo -pix_fmt rgb24 -s:v {0}x{1} -r 24 -i - -c:v libx264 -preset fast -crf 24 "?filename?"'
        
        #ff_write_file = 'ffmpeg -y -loglevel panic -f rawvideo -pix_fmt rgb24 -s:v {0}x{1} -r 24 -i - -c:v libx264 -preset fast -crf 24 ?filename?'
        ff_write_file = ff_write_file.format(p.width, p.height).replace("?filename?", output_path)
        print('file write')
        print(ff_write_file)
        ff_write_file = ff_write_file.split(' ')       
        #ff_read_file = 'ffmpeg -y -loglevel panic -ss 00:00:00 -t 00:00:01 -i "?filename?" -s:v {0}x{1} -vf fps=24 -f image2pipe -pix_fmt rgb24 -c:v rawvideo -'
        ff_read_file = 'ffmpeg -i ?filename? -f image2pipe -pix_fmt rgb24 -vcodec rawvideo  -'
        ff_read_file = ff_read_file.format(p.width, p.height).replace("?filename?", input_path)
        print('file read')
        print(ff_read_file)
        ff_read_file = ff_read_file.split(' ')
        #ff_read_file[5] = input_path
        encoder = ffmpeg(ff_write_file, use_stdin=True)
        decoder = ffmpeg(ff_read_file, use_stdout=True)
        #encoder.start()
        decoder.start()
        
        pull_cnt = p.width*p.height*3
        frame_num = 0
        import time
        time.sleep(2)
        while True:
            
            print()
            print(ff_write_file)
            print()
            frame_num += 1
            np_image = decoder.readout(pull_cnt)        
            PIL_image = Image.fromarray(np.uint8(np_image)).convert('RGB')
            state.job = f"{frame_num} frames processed"
            p.init_images = [PIL_image]
            proc = process_images(p)
            PIL_image = proc.images[0]
            np_image = np.asarray(PIL_image)
            #encoder.write(np_image)
        #encoder.write_eof()
        
        return Processed(p, [], p.seed, "")
