import os, glob, cv2, numpy as np
import random
from random import shuffle

class StaticDataset():
    def __init__(self, frame_basedir, density_basedir, debug, img_size=(480, 288)):
        MEAN_VALUE = np.array([103.939, 116.779, 123.68], dtype=np.float32)   # B G R/ use opensalicon's mean_value
        self.MEAN_VALUE = MEAN_VALUE[None, None, ...]
        self.img_size = img_size
        frame_path_list = glob.glob(os.path.join(frame_basedir, '*.*'))
        density_path_list = glob.glob(os.path.join(density_basedir, '*.*'))
        if debug is True:
            print "Debug mode"
            frame_path_list = frame_path_list[:1000]
            density_path_list = density_path_list[:1000]

        self.data = []
        self.labels = []
        print len(frame_path_list)
        for (frame_path, density_path) in zip(frame_path_list, density_path_list):
            frame = cv2.imread(frame_path).astype(np.float32)
            density = cv2.imread(density_path, 0).astype(np.float32)

            frame =self.pre_process_img(frame, False)
            density = self.pre_process_img(density, True)
            self.data.append(frame)
            self.labels.append(density)
            if len(self.data) % 1 == 0:
                print len(self.data), '\r',
        print 'Done'
        self.num_examples = len(self.data)
        
        self.data = np.array(self.data)
        self.labels = np.array(self.labels)
        
        self.completed_epoch = 0
        self.index_in_epoch = 0

    def pre_process_img(self, image, greyscale=False):
        if greyscale==False:
            image = image-self.MEAN_VALUE
            image = cv2.resize(image, dsize = self.img_size)
            image = np.transpose(image, (2, 0, 1))
            image = image / 255.
        else:
            image = cv2.resize(image, dsize = self.img_size)
            image = image[None, ...]
            image = image / 255.
        return image

    def next_batch(self, batch_size):
        """Return the next `batch_size` examples from this data set."""
        start = self.index_in_epoch
        self.index_in_epoch += batch_size
        if self.index_in_epoch > self.num_examples:
            # Finished epoch
            self.completed_epoch += 1
            # Shuffle the data
            perm = np.arange(self.num_examples)
            np.random.shuffle(perm)
            self.data = self.data[perm]
            self.labels = self.labels[perm]
            # Start next epoch
            start = 0
            self.index_in_epoch = batch_size
            assert batch_size <= self.num_examples
        end = self.index_in_epoch
        return self.data[start:end], self.labels[start:end]


class VideoDataset():
    def __init__(self, frame_basedir, density_basedir, img_size=(480,288), key_frame_interval=10):
        MEAN_VALUE = np.array([103.939, 116.779, 123.68], dtype=np.float32)   # B G R/ use opensalicon's mean_value
        self.MEAN_VALUE = MEAN_VALUE[None, None, ...]
        self.img_size = img_size
        self.dataset_dict={}
        self.T = key_frame_interval
        self.step = 3
        assert self.step < self.T
        self.frame_basedir = frame_basedir
        self.density_basedir = density_basedir
        self.setup_video_dataset()

    def setup_video_dataset(self):
        # self.video_dir_list = os.listdir(self.frame_basedir)
        self.video_dir_list = glob.glob(os.path.join(self.frame_basedir, "*"))

        self.tuple_list = []

        for i in range(len(self.video_dir_list)):
            video_dir = self.video_dir_list[i]
            frame_list = glob.glob(os.path.join(video_dir, '*.*'))
            # print frame_list;exit()

            total_frame = len(frame_list)

            for j in range(total_frame):
                ceil = j + self.T
                if ceil > total_frame:
                    break
                ## random pick self.step frame in this interval
                pick_list = random.sample(range(j+2, ceil), self.step)
                for pick in pick_list:
                    assert pick < ceil and pick != j
                    tup = (i, j+1, pick) # video index, key frame index, current frame index
                    self.tuple_list.append(tup)
        
        shuffle(self.tuple_list)
        self.num_examples = len(self.tuple_list)
        print self.num_examples, "samples generated..."

        self.num_epoch = 0
        self.index_in_epoch = 0

    def get_frame_pair(self):
        if not self.index_in_epoch >= self.num_examples:
            tup = self.tuple_list[self.index_in_epoch]

            self.index_in_epoch += 1
        else:
            shuffle(self.tuple_list)
            self.index_in_epoch = 0
            self.num_epoch += 1

            tup = self.tuple_list[self.index_in_epoch]
            self.index_in_epoch += 1
        # print tup;exit()
        video_index, key_frame_index, cur_frame_index = tup
        video_dir = self.video_dir_list[video_index]
        video_name = os.path.basename(video_dir)
        print video_dir, key_frame_index, cur_frame_index
        key_frame_name_wildcard = "frame_%d.*" % key_frame_index
        cur_frame_name_wildcard = "frame_%d.*" % cur_frame_index
        key_frame_path = glob.glob(os.path.join(video_dir, key_frame_name_wildcard))[0]
        cur_frame_path = glob.glob(os.path.join(video_dir, cur_frame_name_wildcard))[0]

        gt_density_dir = os.path.join(self.density_basedir, video_name)
        # print gt_density_dir
        cur_frame_gt_path = glob.glob(os.path.join(gt_density_dir, cur_frame_name_wildcard))[0]
        # print video_name,video_dir, key_frame_path, cur_frame_path, cur_frame_gt_path;exit()

        key_frame = cv2.resize(cv2.imread(key_frame_path), dsize=self.img_size)
        cur_frame = cv2.resize(cv2.imread(cur_frame_path), dsize=self.img_size)
        cur_frame_gt = cv2.resize(cv2.imread(cur_frame_gt_path, 0), dsize=self.img_size)

        return key_frame, cur_frame, cur_frame_gt
    
    def pre_process_img(self, image, greyscale=False):
        if greyscale==False:
            image = image-self.MEAN_VALUE
            image = cv2.resize(image, dsize = self.img_size)
            image = np.transpose(image, (2, 0, 1))
            image = image[None, ...]
            image = image / 255.
        else:
            image = cv2.resize(image, dsize = self.img_size)
            image = image[None, None, ...]
            image = image / 255.
        return image