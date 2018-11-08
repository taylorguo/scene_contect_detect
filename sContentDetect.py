#!/usr/bin/python
# coding: UTF-8
# Python3.6

# Standard Library Imports
from __future__ import print_function
import os
import time
import math
from string import Template

# import 3'rd supporting modules
import cv2
from imutils.video import count_frames

## https://github.com/Breakthrough/PySceneDetect
import scenedetect
from scenedetect.video_manager import VideoManager
from scenedetect.scene_manager import SceneManager
from scenedetect.frame_timecode import FrameTimecode
from scenedetect.stats_manager import StatsManager
from scenedetect.detectors import ContentDetector


class TethysSceneDetector():

    def __init__(self):

        self.video_path = ""
        self.fps = 0


    def find_scenes(self, video_path):
        # instance scenedetect objects to detect scenes using ContentDetector
        # input:  string- video path;
        # return: scene_list in FrameTimecode format, see below detail sample / explaination.
        self.video_path = video_path
        video_manager = VideoManager([self.video_path])
        self.fps = video_manager.get_framerate()
        nFrames = count_frames(self.video_path)

        stats_manager = StatsManager()
        scene_manager = SceneManager(stats_manager)

        # select ContentDetector to detect scenes
        # Threshhold = 30 by default, set it lower if density is darker, say 27
        # it can be analyzed from output scene timecode or generated images against video
        scene_manager.add_detector(ContentDetector())
        base_timecode = video_manager.get_base_timecode()

        scene_list = []

        try:
            # set downscale factor according to resolution ratio to improve speed
            video_manager.set_downscale_factor()

            video_manager.start()

            # scene detection on video_manager(video_path)
            scene_manager.detect_scenes(frame_source=video_manager)

            # scene_list = scene_manager.get_cut_list(base_timecode)
            scene_list = scene_manager.get_scene_list(base_timecode)


        finally:
            video_manager.release()

        if scene_list == []:
            scene_list = [(FrameTimecode(0, self.fps), FrameTimecode(nFrames, self.fps))]

        # return a list of tuple to indicate each scene start & end frame number in FrameTimecode
        # looks like:       [(FrameTimecode(frame=0, fps=4.358900), FrameTimecode(frame=68, fps=4.358900))]
        # another examples: [(FrameTimecode(frame=0, fps=23.976024), FrameTimecode(frame=90, fps=23.976024)), ...,
        #                    (FrameTimecode(frame=1966, fps=23.976024), FrameTimecode(frame=1980, fps=23.976024))
        #                   ]
        return scene_list


    def convert_to_frames(self, scene_list):
        # convert FrameTimecode to frames number by calling FrameTimecode function
        # input:  list - scene_list(in FrameTimecode type)
        # return: list - frames_scene_list (in tuple(Int) type)
        frames_scene_list = []
        for scene in scene_list:
            start_frames = scene[0].get_frames()
            end_frames = scene[1].get_frames()
            frames_scene_list.append((start_frames, end_frames))

        return frames_scene_list


    def convert_to_timecode(self, scene_list):
        # convert FrameTimecode to timecode by calling FrameTimecode function
        # input:  list - scene_list(in FrameTimecode type)
        # return: list - timecode_scene_list (in tuple(‘HH:MM:SS.nnn’) type)
        timecode_scene_list = []
        for scene in scene_list:
            start_timecode = scene[0].get_timecode()
            end_timecode = scene[1].get_timecode()
            timecode_scene_list.append((start_timecode, end_timecode))

        return timecode_scene_list


    def convert_to_seconds(self, scene_list):
        # convert FrameTimecode to seconds by calling FrameTimecode function
        # input:  list - scene_list(in FrameTimecode type)
        # return: list - seconds_scene_list (in tuple(float) type)
        seconds_scene_list = []
        for scene in scene_list:
            start_seconds = scene[0].get_seconds()
            end_seconds = scene[1].get_seconds()
            seconds_scene_list.append((start_seconds, end_seconds))

        return seconds_scene_list


    def generate_images(self, video_path, folder_name):
        # open video / VideoManager to get scene_list, generate 3 images per scene
        # input:  string- video path;
        # return: scene_list in FrameTimecode format, see below detail sample / explaination.
        scene_list = self.find_scenes(video_path)

        num_images = 3
        image_extension = "jpg"

        # Reset video manager and downscale factor.

        video_manager = VideoManager([video_path])
        video_manager.set_downscale_factor(1)
        video_manager.start()

        print("Detect Scenes:", len(scene_list))
        print(" **** Generating output images (%d per scene)..."%num_images)

        completed = True

        # Generate image filename
        image_name_template = "$VIDEO_NAME-Scene-$SCENE_NUMBER-$IMAGE_NUMBER"
        filename_template = Template(image_name_template)

        if scene_list:
            scene_num_format = '%0'
            scene_num_format += str(max(3, math.floor(math.log(len(scene_list), 10)) + 1)) + 'd'
            image_num_format = '%0'
            image_num_format += str(math.floor(math.log(num_images, 10)) + 2) + 'd'

        # cut every scene into a number of frames/images(indicate by num_images)[here is 3]
        # save frame timecode of every group to a list (timecode_list
        timecode_list = dict()

        for i in range(len(scene_list)):
            timecode_list[i] = []

        middle_images = num_images - 2
        for i, (start_time, end_time) in enumerate(scene_list):
            timecode_list[i].append(start_time)
            duration = (end_time.get_frames() - 1) - start_time.get_frames()
            duration_increment = None
            duration_increment = int(duration / (middle_images + 1))
            for j in range(middle_images):
                timecode_list[i].append(start_time + ((j + 1) * duration_increment))

            # End FrameTimecode is always the same frame as the next scene's start_time
            # (one frame past the end), so we need to subtract 1 here.
            timecode_list[i].append(end_time - 1)
        #########################################

        img_folder = self.create_folder(folder_name)
        output_dir = os.path.join(os.path.dirname(os.path.realpath(__file__)), img_folder)

        for i in timecode_list:
            for j, image_timecode in enumerate(timecode_list[i]):
                video_manager.seek(image_timecode)
                video_manager.grab()
                ret_val, frame_im = video_manager.retrieve()
                if ret_val:
                    cv2.imwrite(os.path.join(os.path.dirname(os.path.realpath(__file__)), img_folder,
                                             "%s.%s" % (filename_template.safe_substitute(
                                                        VIDEO_NAME=folder_name,
                                                        SCENE_NUMBER=scene_num_format % (i + 1),
                                                        IMAGE_NUMBER=image_num_format % (j + 1)
                                                        ), image_extension)),
                                frame_im)

                else:
                    completed = False
                    break

        if completed is True: video_manager.release()

        # in case of video_manager failure
        if not completed:
            print("Could not generate all output images.")

        return output_dir


    ### Create folder to generate images
    def create_folder(self, folder_name):
        img_folder = folder_name
        isExists = os.path.exists(img_folder)
        if not isExists:
            os.makedirs(img_folder)
            print(" **** Scene images folder \"" + img_folder + "\" created, generating pictures ...")
            return img_folder
        else:
            # if folder exist，print message
            print(" **** \"" + img_folder + "\" image folder exist")
            return img_folder
        return img_folder


#######  used to download mp4 video ######

def download_video(url_address):
    # 下载mp4视频文件
    ADDRESS_ITEM = url_address.split("/")
    VIDEO_PREFIX = ADDRESS_ITEM[-2]
    EXT_NAME = "mp4"
    saved_file_name = VIDEO_PREFIX + "." + EXT_NAME

    # for Python3
    from urllib import request
    f = request.urlopen(url_address)
    video_data = f.read()
    with open(saved_file_name, "wb") as code:
        code.write(video_data)

    current_path = os.path.dirname(os.path.realpath(__file__))

    full_file_path = os.path.join(current_path, saved_file_name)

    return saved_file_name

##########################################


if __name__ == "__main__":
    # VIDEO_PATH = "/Users/taylorguo/Documents/Innotech/qtt_mp4/2girls.mp4"
    # VIDEO_PATH = "/Users/taylorguo/Documents/Innotech/qtt_mp4/goldeneye.mp4"

    VIDEO_URL = "http://v-qtt.quduopai.cn/qdp-sjsp-mp4-hd/7dd8c2cca8484f219d6e1566c90740a2/hd.mp4"
    VIDEO_PATH = download_video(VIDEO_URL)

    tsd = TethysSceneDetector()
    # s_list = tsd.find_scenes(VIDEO_PATH)
    # # print(s_list)
    # f_list = tsd.convert_to_frames(s_list)
    # print(f_list,"\n")
    # tc_list = tsd.convert_to_timecode(s_list)
    # print(tc_list,"\n")
    # ss_list = tsd.convert_to_seconds(s_list)
    # print(ss_list)
    print(" ---- Created images folder: ", tsd.generate_images(VIDEO_PATH, "test"))

