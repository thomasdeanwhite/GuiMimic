import config as cfg
from yolo import Yolo
from cv2 import imread, resize
import cv2
import numpy as np
import tensorflow as tf
import sys
import gc
import math
import random
import os
import pickle
import re

debug = False

tf.logging.set_verbosity(tf.logging.INFO)

def normalise_point(point, val):
    i = point*val
    return i, math.floor(i)

def normalise_label(label):
    px, cx = normalise_point(max(0, min(0.999, label[0])), cfg.grid_shape[0])
    py, cy = normalise_point(max(0, min(0.999, label[1])), cfg.grid_shape[1])
    return [
        px,
        py,
        max(0, min(cfg.grid_shape[0], label[2]*cfg.grid_shape[0])),
        max(0, min(cfg.grid_shape[1], label[3]*cfg.grid_shape[1])),
        label[4]
    ], (cx, cy)

def load_files(raw_files):
    raw_files = [f.replace("/data/acp15tdw", "/home/thomas/experiments") for f in raw_files]
    label_files = [f.replace("/images/", "/labels/") for f in raw_files]
    label_files = [f.replace(".png", ".txt") for f in label_files]

    pickle_files = [f.replace("/images/", "/pickle/") for f in raw_files]
    pickle_files = [f.replace(".png", ".pickle") for f in pickle_files]

    images = []
    labels = []
    object_detection = []

    for i in range(len(raw_files)):
        pickle_f = pickle_files[i]


        pickled_data = []

        if os.path.isfile(pickle_f):
            pickled_data = pickle.load(open(pickle_f, "rb"))
            images.append(pickled_data[0])
            labels.append(pickled_data[1])
        else:
            f = raw_files[i]
            f_l = label_files[i]

            if not os.path.isfile(f) or not os.path.isfile(f_l):
                continue

            image = np.int16(imread(f, 0))
            height, width = image.shape

            aspect = height/width

            padding_x = 0
            padding_y = 0

            if aspect > 1: # portrait
                padding_x = round((height-width)/2)
                for i in range(padding_x):
                    elements = np.transpose(np.expand_dims(np.zeros([image.shape[0]]), 0))
                    image = np.append(elements, image, 1)
                for i in range(padding_x):
                    elements = np.transpose(np.expand_dims(np.zeros([image.shape[0]]), 0))
                    image = np.append(image, elements, 1)
            else: #landscape
                padding_y = round((width-height)/2)
                for i in range(padding_y):
                    elements = np.transpose(np.expand_dims(np.zeros([image.shape[1]]), 1))
                    image = np.append(elements, image, 0)
                for i in range(padding_y):
                    elements = np.transpose(np.expand_dims(np.zeros([image.shape[1]]), 1))
                    image = np.append(image, elements, 0)

            image = np.uint8(resize(image, (cfg.width, cfg.height)))
            image = np.reshape(image, [cfg.width, cfg.height, 1])

            images.append(image)

            # read in format [c, x, y, width, height]
            # store in format [c], [x, y, width, height]
            with open(f_l, "r") as l:
                imglabs = [[[0 for i in
                             range(5 + len(yolo.names))] for i in
                            range(cfg.grid_shape[1])] for i in
                           range(cfg.grid_shape[0])]

                for i in range(cfg.grid_shape[0]):
                    for j in range(cfg.grid_shape[1]):
                        imglabs[i][j][0] = j
                        imglabs[i][j][1] = i

                for line in l:
                    elements = line.split(" ")
                    #print(elements[1:3])
                    normalised_label, centre = normalise_label([float(elements[1]), float(elements[2]),
                                                                float(elements[3]), float(elements[4]), 1])

                    if padding_x > 0:
                        ratio = 1-(2*padding_x)/height
                        newx = cfg.grid_shape[0] * (0.5 + (normalised_label[0]/cfg.grid_shape[0] - 0.5)*ratio)
                        normalised_label[0] = newx
                        normalised_label[2] = normalised_label[2] * ratio
                    elif padding_y > 0:
                        ratio = 1-(2*padding_y)/width
                        newy = cfg.grid_shape[1] * (0.5 + (normalised_label[1]/cfg.grid_shape[1] - 0.5)*ratio)
                        normalised_label[1] = newy
                        normalised_label[3] = normalised_label[3] * ratio

                    x = max(0, min(int(normalised_label[0]), cfg.grid_shape[0]-1))
                    y = max(0, min(int(normalised_label[1]), cfg.grid_shape[1]-1))

                    classes = [0 for i in range(len(yolo.names))]

                    imglabs[y][x] = np.concatenate((normalised_label, classes), axis=0)
                    imglabs[y][x][5+int(elements[0])] = 1
                labels.append(imglabs)

            imglabs = np.array(imglabs)

            pickled_data = [image, imglabs]

            pickle.dump(pickled_data, open(pickle_f, "wb"))

    for im in range(len(images)):
        image = images[im]

        labs = labels[im]

        height, width, channels = image.shape

        median_col = np.median(image)

        # for lnx in range(len(labs)):
        #     for lny in range(len(labs[lnx])):
        #         if random.random() < cfg.removal_probability:
        #             # label removed
        #             lbl = labs[lnx][lny]
        #             lbl[0] = lbl[0] / cfg.grid_shape[0]
        #             lbl[1] = lbl[1] / cfg.grid_shape[1]
        #             lbl[2] = lbl[2] / cfg.grid_shape[0]
        #             lbl[3] = lbl[3] / cfg.grid_shape[1]
        #             x1, y1 = (int(width * (lbl[0] - lbl[2]/2)),
        #                     int(height * (lbl[1] - lbl[3]/2)))
        #             x2, y2 = (int(width * (lbl[0] + lbl[2]/2)),
        #                           int(height * (lbl[1] + lbl[3]/2)))
        #             cv2.rectangle(image,
        #                         (x1, y1),
        #                         (x2, y2),
        #                           median_col, -1, 4)
        #
        #             labels[im][lnx][lny] = [0, 0, 0, 0, 0]
        #             object_detection[im][lnx][lny] = 0

        if random.random() < cfg.brightness_probability:
            brightness = int(random.random()*cfg.brightness_var*2)-cfg.brightness_var
            image = np.maximum(0, np.minimum(255, np.add(image, brightness)))

        if random.random() < cfg.contrast_probability:
            contrast = (random.random() * cfg.contrast_var * 2) - cfg.contrast_var

            contrast_diff = np.multiply(image - np.mean(image), contrast).astype(np.uint8)
            image = np.maximum(0, np.minimum(255, np.add(image, contrast_diff)))

        if random.random() < cfg.invert_probability:
            image = 255 - image

        if random.random() < cfg.dimension_probability:
            # crop or padd image
            rand_num = random.random()
            if rand_num < 0.3333: #pad

                new_width = int(random.random() * (width) + width)
                new_height = int(random.random() * (height) + height)

                new_x = int(random.random() * (new_width-width))
                new_y = int(random.random() * (new_height-height))

                img = np.zeros([new_height, new_width, channels]).astype(np.uint8) + int(np.median(image))

                img[new_y:new_y+height, new_x:new_x+width] = image

                image = img

                mult_x = width / new_width
                mult_y = height / new_height

                labs_copy = np.copy(labels[im])

                for lnx in range(len(labs)):
                    for lny in range(len(labs[lnx])):
                        labels[im][lnx][lny] = [0 for i in range(5+len(yolo.names))]

                for lnx in range(len(labs)):
                    for lny in range(len(labs[lnx])):

                        lbl = labs_copy[lnx][lny]
                        if lbl[4] == 1:
                            lbl[0] = max(0, min(cfg.grid_shape[0]-1, (new_x/new_width + (lbl[0] / cfg.grid_shape[0] * mult_x)) * cfg.grid_shape[0]))
                            lbl[1] = max(0, min(cfg.grid_shape[1]-1, (new_y/new_height + (lbl[1] / cfg.grid_shape[1] * mult_y)) * cfg.grid_shape[1]))
                            lbl[2] = lbl[2] * mult_x
                            lbl[3] = lbl[3] * mult_y

                            labels[im][int(lbl[1])][int(lbl[0])] = lbl

            elif rand_num < 0.6666: #crop
                new_width = int((random.random() * width/2)+width*0.75)
                new_height = int((random.random() * height/2)+height*0.75)

                new_x = int(random.random() * width*0.25)
                new_y = int(random.random() * height*0.25)

                img = np.zeros([new_height, new_width, channels]).astype(np.uint8) + int(np.median(image))

                max_x = min(new_x + new_width, width) - new_x
                max_y = min(new_y + new_height, height) - new_y

                img[0:max_y, 0:max_x] = image[new_y:new_y+max_y, new_x:new_x+max_x]

                image = img

                mult_x = width / new_width
                mult_y = height / new_height
                labs_copy = np.copy(labels[im])

                for lnx in range(len(labs)):
                    for lny in range(len(labs[lnx])):
                        object_detection[im][lnx][lny] = 0
                        labels[im][lnx][lny] = [0 for i in range(5+len(yolo.names))]

                for lnx in range(len(labs)):
                    for lny in range(len(labs[lnx])):

                        lbl = labs_copy[lnx][lny]
                        if lbl[4] == 1:
                            lbl[0] = ((lbl[0] / cfg.grid_shape[0] * mult_x)-new_x/new_width) * cfg.grid_shape[0]
                            lbl[1] = ((lbl[1] / cfg.grid_shape[1] * mult_y)-new_y/new_height) * cfg.grid_shape[1]
                            lbl[2] = lbl[2] * mult_x
                            lbl[3] = lbl[3] * mult_y

                            if (lbl[0] >= 0 and lbl[1] >= 0 and lbl[0] < cfg.grid_shape[0] and lbl[1] < cfg.grid_shape[1] ): # check if element is in screenshot
                                labels[im][int(lbl[1])][int(lbl[0])] = lbl

            else: # tile
                new_width = width * 2
                new_height = height * 2

                img = np.zeros([new_height, new_width, channels]).astype(np.uint8) + int(np.median(image))

                copy_chance = 0.9

                copies = [random.random() < copy_chance, random.random() < copy_chance, random.random() < copy_chance, random.random() < copy_chance]

                if copies[0]:
                    img[:height, :width] = np.copy(image)

                if copies[1]:
                    img[height:, :width] = np.copy(image)

                if copies[2]:
                    img[:height, width:] = np.copy(image)

                if copies[3]:
                    img[height:, width:] = np.copy(image)

                image = img

                labs_copy = np.copy(labels[im])

                for lnx in range(len(labs)):
                    for lny in range(len(labs[lnx])):
                        object_detection[im][lnx][lny] = 0
                        labels[im][lnx][lny] = [0 for i in range(5+len(yolo.names))]

                disp_x = cfg.grid_shape[0]/2
                disp_y = cfg.grid_shape[1]/2

                for lnx in range(len(labs)):
                    for lny in range(len(labs[lnx])):
                        lbl = labs_copy[lnx][lny] / 2
                        lbl[4] = lbl[4] * 2
                        if lbl[4] == 1:

                            x, y = (lbl[0], lbl[1])

                            if copies[0]:
                                labels[im][int(y)][int(x)] = np.copy(lbl)

                            if copies[1]:
                                lbc2 = np.copy(lbl)
                                lbc2[1] += disp_y
                                labels[im][int(lbc2[1])][int(lbc2[0])] = lbc2

                            if copies[2]:
                                lbc2 = np.copy(lbl)
                                lbc2[0] += disp_x
                                labels[im][int(lbc2[1])][int(lbc2[0])] = lbc2

                            if copies[3]:
                                lbc2 = np.copy(lbl)
                                lbc2[0] += disp_x
                                lbc2[1] += disp_y
                                labels[im][int(lbc2[1])][int(lbc2[0])] = lbc2

        image = cv2.resize(image, (cfg.height, cfg.width))

        image = np.reshape(image, [cfg.width, cfg.height, 1])

        images[im] = image

        if debug:
            height, width, chan = image.shape

            print(labs)

            for lnx in range(len(labs)):
                for lny in range(len(labs[lnx])):

                    lbl = labs[lnx][lny]

                    col = 0

                    if (lbl[4] > 0):
                        col = 255

                    lbl[0] = lbl[0]/cfg.grid_shape[0]
                    lbl[1] = lbl[1]/cfg.grid_shape[1]
                    lbl[2] = lbl[2]/cfg.grid_shape[0]
                    lbl[3] = lbl[3]/cfg.grid_shape[1]
                    x1, y1 = (int(width * (lbl[0] - lbl[2]/2)),
                              int(height * (lbl[1] - lbl[3]/2)))
                    x2, y2 = (int(width * (lbl[0] + lbl[2]/2)),
                              int(height * (lbl[1] + lbl[3]/2)))
                    cv2.rectangle(image,
                                  (x1, y1),
                                  (x2, y2),
                                  127, 3, 4)

                    cv2.rectangle(image,
                                  (int((x1+x2)/2-1), int((y1+y2)/2-1)),
                                  (int((x1+x2)/2+1), int((y1+y2)/2+1)),
                                  127, 3, 4)

                    cv2.rectangle(image,
                                  (int(lny/cfg.grid_shape[0]*width), int(lnx/cfg.grid_shape[0]*height)),
                                  (int((1+lny)/cfg.grid_shape[1]*width), int((1+lnx)/cfg.grid_shape[1]*height)),
                                  col, 1, 4)

            cv2.imshow('image',image)
            cv2.waitKey(0)
            cv2.destroyAllWindows()


    return images, labels

def modify_learning_rate(epoch):
    ep = epoch

    # return learning rate in accordance to YOLO paper
    if ep == 0:
        return 0.001
    if ep < 10:
        return 0.001+(0.01-0.001)/((10-epoch))

    if ep < 75:
        return 0.01

    if ep < 105:
        return 0.001

    return 0.01 / ep


if __name__ == '__main__':

    training_file = cfg.data_dir + "/" + cfg.train_file

    pattern = re.compile(".*\/([0-9]+).*")

    training_images = []

    real_images = []

    with open(training_file, "r") as tfile:
        for l in tfile:
            training_images.append(l.strip())



    valid_file = cfg.data_dir + "/" + cfg.validate_file

    valid_images = []

    with open(valid_file, "r") as tfile:
        for l in tfile:
            valid_images.append(l.strip())

    for i in ['train.txt', 'test.txt', 'validate.txt']:

        valid_file = cfg.data_dir + "/" + i

        with open(valid_file, "r") as tfile:
            for l in tfile:
                file_num = int(pattern.findall(l)[-1])

                if file_num <= 243:
                    #print(file_num)
                    real_images.append(l.strip())

    print("Found", len(real_images), "real GUI screenshots.")

    #valid_images = random.sample(valid_images, cfg.batch_size)

    with tf.device(cfg.gpu):

        tf.reset_default_graph()

        yolo = Yolo()

        yolo.create_network()

        yolo.set_training(True)

        yolo.create_training()

        learning_rate = tf.placeholder(tf.float64)
        learning_r = cfg.learning_rate_start
        update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)

        with tf.control_dependencies(update_ops):
            yolo.set_update_ops(update_ops)

            train_step = tf.train.MomentumOptimizer(learning_rate, cfg.momentum). \
                    minimize(yolo.loss)

        saver = tf.train.Saver()

        model_file = cfg.weights_dir + "/model.ckpt"

        valid_batches = math.ceil(len(valid_images)/cfg.batch_size) if cfg.run_all_batches else 1

        real_batches = math.ceil(len(real_images)/cfg.batch_size) if cfg.run_all_batches else 1

        gpu_options = tf.GPUOptions(allow_growth=True)

        config = tf.ConfigProto(allow_soft_placement = True)

        with tf.Session(config=config) as sess:

            init_op = tf.global_variables_initializer()

            print("Initialising Memory Values")
            model = sess.run(init_op)

            #print(tf.get_default_graph().as_graph_def())

            if os.path.isfile(os.getcwd() + "/" + cfg.weights_dir + "/checkpoint"):
                saver.restore(sess, model_file)
                print("Restored model")
            else:
                print("Training from scratch.")

            if (cfg.enable_logging):
                train_writer = tf.summary.FileWriter( './logs/1/train ', sess.graph)

            print("!Finished Initialising Memory Values!")
            image_length = len(training_images)
            batches = math.ceil(image_length/cfg.batch_size) if cfg.run_all_batches else 1
            print("Starting training:", image_length, "images in", batches, "batches.")

            anchors = np.reshape(np.array(cfg.anchors), [-1, 2]) / cfg.width * cfg.grid_shape[0]

            print("anchors", anchors.shape)

            random.shuffle(valid_images)
            with open("training.csv", "w") as file:
                file.write("epoch,dataset,loss,loss_position,loss_dimension,loss_obj,loss_class\n")

            for i in range(cfg.epochs):
                #random.shuffle(training_images)
                yolo.set_training(False)

                losses = [0, 0, 0, 0, 0]

                for j in range(valid_batches):
                    gc.collect()

                    lower_index = j*cfg.batch_size
                    upper_index = min(len(valid_images), ((j+1)*cfg.batch_size))

                    v_imgs, v_labels = load_files(
                        valid_images[lower_index:upper_index])

                    v_imgs = (np.array(v_imgs)/127.5)-1

                    v_labels = np.array(v_labels)

                    if len(v_labels) == 0:
                        continue

                    if cfg.enable_logging and i == 0:
                        merge = tf.summary.merge_all()
                        summary, _ = sess.run([merge, yolo.loss], feed_dict={
                            yolo.train_bounding_boxes: v_labels,
                            yolo.x: v_imgs,
                            yolo.anchors: anchors
                        })

                        train_writer.add_summary(summary, 0)

                    predictions, loss, lp, ld, lo, lc = sess.run([yolo.output,
                        yolo.loss, yolo.loss_position, yolo.loss_dimension,
                        yolo.loss_obj, yolo.loss_class], feed_dict={
                        yolo.train_bounding_boxes: v_labels,
                        yolo.x: v_imgs,
                        yolo.anchors: anchors,
                        yolo.iou_threshold: 0.5,
                        yolo.object_detection_threshold: cfg.object_detection_threshold
                    })


                    # lr = 3
                    # ur = 6
                    # p1 = predictions[0, lr:ur, lr:ur, 5, 4]
                    #
                    # p2 = v_labels[0, lr:ur, lr:ur, 4]

                    #iou = iou[0, lr:ur, lr:ur]

                    # print(p1,"\n")
                    # print(p2, "\n")
                    # print(p2 - p1)

                    del(v_imgs, v_labels, predictions)

                    losses[0] += loss
                    losses[1] += lp
                    losses[2] += ld
                    losses[3] += lo
                    losses[4] += lc

                for li in range(len(losses)):
                    losses[li] = losses[li] / valid_batches

                loss_string = str(i) + "," + "Validation"

                for l in range(len(losses)):
                    loss_string = loss_string + "," + str(losses[l])


                with open("training.csv", "a") as file:
                    file.write(loss_string + "\n")

                print(loss_string)

                yolo.set_training(False)

                losses = [0, 0, 0, 0, 0]

                for j in range(real_batches):
                    gc.collect()

                    lower_index = j*cfg.batch_size
                    upper_index = min(len(real_images), ((j+1)*cfg.batch_size))

                    v_imgs, v_labels = load_files(
                        real_images[lower_index:upper_index])

                    v_imgs = (np.array(v_imgs)/127.5)-1

                    v_labels = np.array(v_labels)

                    if len(v_labels) == 0:
                        continue

                    if cfg.enable_logging and i == 0:
                        merge = tf.summary.merge_all()
                        summary, _ = sess.run([merge, yolo.loss], feed_dict={
                            yolo.train_bounding_boxes: v_labels,
                            yolo.x: v_imgs,
                            yolo.anchors: anchors
                        })

                        train_writer.add_summary(summary, 0)

                    predictions, \
                    loss, lp, ld, lo, lc, = sess.run([
                        yolo.output,
                        yolo.loss, yolo.loss_position, yolo.loss_dimension, yolo.loss_obj, yolo.loss_class], feed_dict={
                        yolo.train_bounding_boxes: v_labels,
                        yolo.x: v_imgs,
                        yolo.anchors: anchors,
                        yolo.iou_threshold: 0.5,
                        yolo.object_detection_threshold: cfg.object_detection_threshold
                    })


                    del(v_imgs, v_labels, predictions)

                    losses[0] += loss
                    losses[1] += lp
                    losses[2] += ld
                    losses[3] += lo
                    losses[4] += lc

                for li in range(len(losses)):
                    losses[li] = losses[li] / real_batches

                loss_string = str(i) + "," + "Real"

                for l in range(len(losses)):
                    loss_string = loss_string + "," + str(losses[l])


                with open("training.csv", "a") as file:
                    file.write(loss_string + "\n")

                print(loss_string)

                #learning_r = (cfg.learning_rate_start-cfg.learning_rate_min)*pow(cfg.learning_rate_decay, i) \
                #             + cfg.learning_rate_min

                learning_r = modify_learning_rate(i)
                print("Learning rate:", learning_r)
                yolo.set_training(True)

                print("Training")

                losses = [0, 0, 0, 0, 0]

                for j in range(batches):
                    gc.collect()
                    if (cfg.enable_logging):
                        merge = tf.summary.merge_all()



                    lower_index = j * cfg.batch_size
                    upper_index = min(len(training_images), (j+1)*cfg.batch_size)
                    imgs, labels = load_files(
                        training_images[lower_index:upper_index])

                    imgs = (np.array(imgs)/127.5)-1

                    labels = np.array(labels)


                    if len(labels) == 0:
                        continue

                    if (cfg.enable_logging):
                        summary, _, predictions, loss, lp, ld, lo, lc = sess.run([
                            merge, train_step, yolo.output,
                            yolo.loss, yolo.loss_position, yolo.loss_dimension, yolo.loss_obj, yolo.loss_class], feed_dict={
                            yolo.train_bounding_boxes: labels,
                            yolo.x: imgs,
                            yolo.anchors: anchors,
                            learning_rate: learning_r,
                            yolo.iou_threshold: 0.5,
                            yolo.object_detection_threshold: cfg.object_detection_threshold
                        })
                        losses[0] += loss
                        losses[1] += lp
                        losses[2] += ld
                        losses[3] += lo
                        losses[4] += lc


                        train_writer.add_summary(summary, i+1)
                    else:

                        assert not np.any(np.less(labels[..., 2:4], 0))

                        _, predictions, loss, lp, ld, lo, lc = sess.run([
                            train_step, yolo.output,
                            yolo.loss, yolo.loss_position, yolo.loss_dimension, yolo.loss_obj, yolo.loss_class], feed_dict={
                            yolo.train_bounding_boxes: labels,
                            yolo.x: imgs,
                            yolo.anchors: anchors,
                            learning_rate: learning_r,
                            yolo.iou_threshold: 0.5,
                            yolo.object_detection_threshold: cfg.object_detection_threshold
                        })

                        assert not np.any(np.less(predictions[..., 2:4], 0))

                        losses[0] += loss
                        losses[1] += lp
                        losses[2] += ld
                        losses[3] += lo
                        losses[4] += lc



                    del(imgs)
                    del(labels)

                for li in range(len(losses)):
                    losses[li] = losses[li] / batches


                loss_string = str(i) + "," + "Training"

                for l in range(len(losses)):
                    loss_string = loss_string + "," + str(losses[l])


                with open("training.csv", "a") as file:
                    file.write(loss_string + "\n")

                print(loss_string + "\n")


                if i % 10 == 0:
                    save_path = saver.save(sess, str(i) + model_file)

                save_path = saver.save(sess, model_file)


            gc.collect()

            sys.exit()