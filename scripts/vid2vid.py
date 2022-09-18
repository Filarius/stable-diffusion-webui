# Author: Filarius
# https://github.com/Filarius

import math
import os
import sys
import traceback

import modules.scripts as scripts
import gradio as gr

from modules.processing import Processed, process_images
from PIL import Image
from modules.shared import opts, cmd_opts, state
from modules import processing


from subprocess import Popen, PIPE
import numpy as np
import sys

class ffmpeg:
    def __init__(self, cmdln, use_stdin=False, use_stdout=False, use_stderr=False, print_to_console=True):
        self._process = None
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

    def readout(self, cnt=None):
        if cnt is None:
            buf = self._process.stdout.read()
        else:
            buf = self._process.stdout.read(cnt)
        arr = np.frombuffer(buf, dtype=np.uint8)
        
        return arr

    def readerr(self, cnt):
        buf = self._process.stderr.read(cnt)
        return np.frombuffer(buf, dtype=np.uint8)

    def write(self, arr):
        bytes = arr.tobytes()
        self._process.stdin.write(bytes)

    def write_eof(self):
        if self._stdin != None:
            self._process.stdin.close()

    def is_running(self):
        return self._process.poll() is None



class Script(scripts.Script):
    def title(self):
        return "vid2vid v.0a"

    def show(self, is_img2img):
        return is_img2img

    def ui(self, is_img2img):
        input_path = gr.Textbox(label="Input file path", lines=1)
        output_path = gr.Textbox(label="Output file path", lines=1)
        crf = gr.Slider(label="CRF (quality, less is better, x264 param)", minimum=1, maximum=40, step=1, value=24)
        fps = gr.Textbox(label="FPS", value="24", lines=1)
        start_time = gr.Textbox(label="Start time", value="hh:mm:ss", lines=1)
        end_time = gr.Textbox(label="End time", value="hh:mm:ss", lines=1)
        show_preview = gr.Checkbox(label='Show preview', value=False)



        return [input_path, output_path, crf, fps, start_time, end_time, show_preview]

    def run(self, p, input_path, output_path, crf, fps, start_time, end_time, show_preview):
        processing.fix_seed(p)
        p.subseed_strength == 0
        seed = p.seed
        p.do_not_save_grid = True
        p.do_not_save_samples = True
        p.batch_count = 1
        
        start_time = start_time.strip()
        end_time = end_time.strip()
        if start_time == 'hh:mm:ss' or start_time == '':
            start_time = '00:00:00'            
        if end_time == 'hh:mm:ss':
            end_time = '' 
        if end_time != '': 
            end_time = ' -to ' + end_time 
            
        time_interval = " -ss " + start_time #single space on beginnig for spacing!
        if (end_time != ''):
            time_interval = time_interval + end_time
        
        ff_write_file = 'ffmpeg -y -loglevel panic -f rawvideo -pix_fmt rgb24 -s:v {w}x{h} -r {fps} -i - -c:v libx264 -preset fast -crf {crf} ?filename?'
        ff_write_file = ff_write_file.format(w=p.width, h=p.height, fps=fps, crf=crf)
        ff_read_file = 'ffmpeg -loglevel panic{time_interval} -i ?filename? -s:v {w}x{h} -vf fps={fps} -f image2pipe -pix_fmt rgb24 -vcodec rawvideo -'
        ff_read_file = ff_read_file.format(time_interval=time_interval, w=p.width, h=p.height, fps=fps)
        ff_read_file = ff_read_file.split(' ')
        ff_write_file = ff_write_file.split(' ')
        
        ff_read_file = [w.replace('?filename?', input_path) for w in ff_read_file]
        ff_write_file = [w.replace('?filename?', output_path) for w in ff_write_file]

        encoder = ffmpeg(ff_write_file, use_stdin=True)
        decoder = ffmpeg(ff_read_file, use_stdout=True)
        encoder.start()
        decoder.start()
        
        pull_cnt = p.width*p.height*3
        frame_num = 0
        import time
        if show_preview:
            import cv2
            from cv2 import cvtColor, COLOR_BGR2RGB
            try:
                cv2.destroyAllWindows()
            finally:
                pass
            cv2.startWindowThread()
            cv2.namedWindow("vid2vid streamig")

        first_frame = True
        
        while True:
            batch = []
            for _ in range(p.batch_size):
                np_image = decoder.readout(pull_cnt)
                if len(np_image)==0:
                    break;
                PIL_image = Image.fromarray(np.uint8(np_image).reshape((p.height,p.width, 3)), mode="RGB" )
                batch.append(PIL_image)
                frame_num += 1
            if len(batch) == 0:
                break
            state.job = f"{frame_num} frames processed"
            p.init_images = batch
            p.seed = [seed for _ in batch] # keep same seed in batch, fix
            proc = process_images(p)  
            if len(proc.images) == 0:
                break;
            if show_preview:
                img_rgb = cvtColor(np.array(proc.images[0]), COLOR_BGR2RGB)
                cv2.imshow('vid2vid streamig',img_rgb)
                cv2.waitKey(1)

            for i in range(len(batch)):
                PIL_image = proc.images[i]
                np_image = np.asarray(PIL_image)
                encoder.write(np_image)

        encoder.write_eof()
        if show_preview:
            cv2.destroyAllWindows() 
        
        return Processed(p, [], p.seed, "")
