import config as cfg
from yolo import Yolo
import cv2
import numpy as np
import tensorflow as tf
import sys
import gc
import math
import random
import os
import pyautogui
from operator import itemgetter
import time
import subprocess
import Xlib
import time
from pynput import keyboard
import data_loader
import timeit

running = True

debug = False

quit_counter = 3

def on_release(key):
    global running, quit_counter
    if key == keyboard.Key.f1:
        quit_counter -= 1
        if quit_counter == 0:
            running = False
            print("Killing tester.")

sub_window = False

def get_window_size(window_name):
    global sub_window
    sub_window = False
    try:
        display = Xlib.display.Display()
        root = display.screen().root

        win_names = window_name.split(":")

        win_names.append("java") # java file browser

        windowIDs = root.get_full_property(display.intern_atom('_NET_CLIENT_LIST'), Xlib.X.AnyPropertyType).value
        wid = 0
        win = None
        for windowID in windowIDs:
            window = display.create_resource_object('window', windowID)
            name = window.get_wm_name() # Title
            tags = window.get_wm_class()
            if tags != None and len(tags) > 1:
                name = tags[1]
            if debug:
                print(window.get_wm_class())
            if isinstance(name, str):
                for w_n in win_names:
                    if w_n.lower() in name.lower():
                        # if wid != 0:
                        #     sub_window = True
                        #     if random.random() < 0.05:
                        #         print("Killing window")
                        #         os.system("xkill -id " + wid)
                        wid = windowID
                        win = window
                        window.set_input_focus(Xlib.X.RevertToParent, Xlib.X.CurrentTime)
                        window.configure(stack_mode=Xlib.X.Above)
                        #prop = window.get_full_property(display.intern_atom('_NET_WM_PID'), Xlib.X.AnyPropertyType)
                        #pid = prop.value[0] # PID

        geom = win.get_geometry()

        app_x, app_y, app_w, app_h = (geom.x, geom.y, geom.width, geom.height)

        try:
            parent_win = win.query_tree().parent

            while parent_win != 0:
                #print(parent_win)
                p_geom = parent_win.get_geometry()
                app_x += p_geom.x
                app_y += p_geom.y
                parent_win = parent_win.query_tree().parent
        except Exception as e:
            print('Screen cap failed: '+ str(e))
        return app_x, app_y, app_w, app_h
    except Exception as e:
        print('Screen cap failed: '+ str(e))
    return 0, 0, 0, 0

def generate_input_string():
    if random.random() < 0.5:
        return "Hello World!"
    else:
        return str(random.randint(-10000, 10000))

def convert_coords(x, y, w, h, aspect):
    if aspect > 1: # width is bigger than height
        h = h * aspect
        y = y - ((y - 0.5)*(1-aspect))
    elif aspect < 1:
        w = w * aspect
        x = x - ((x - 0.5)*(1-1/aspect))

    return x, y, w, h

def perform_interaction(best_box):
    x = int(max(app_x+5, min(app_x + app_w - 5, app_x + (best_box[1]*app_w))))
    y = int(max(app_y+5, min(app_y + app_h - 5, app_y + (best_box[2]*app_h))))

    # y_start = max(app_y, min(app_y + height - 5, app_y + int(height*(best_box[2] - best_box[4]/2))-5))
    # y_end = max(app_y+5, min(app_y + height, app_y + int(height*(best_box[2]+best_box[4]/2))+5))
    #
    # x_start = max(app_x, min(app_x + width - 5, app_x + int(width*(best_box[1]-best_box[3]/2))-5))
    # x_end = max(app_x + 5, min(app_x + width, app_x + int(width*(best_box[1]+best_box[3]/2))+5))
    #
    # image_clicked = raw_image[y_start:y_end,
    #                           x_start:x_end]
    #
    # output_img = output_dir + "/images/" + str(event)
    #
    # np.save(output_img, image_clicked)
    #
    # cv2.imwrite(output_img + ".jpg", image_clicked)
    #
    # widget = yolo.names[int(best_box[0])]
    #
    # interactions.append([widget, event, input_string])
    #
    #
    # with open(test_file, "a+") as t_f:
    #     t_f.write(widget + "," + str(event) + "\n")
    #
    # pyautogui.moveTo(x, y)
    #
    # event = event + 1
    #
    # if widget == "button" or widget == "tabs" or widget == "menu" \
    #         or widget == "menu_item" or widget == "toggle_button":
    #     if (random.random() < 0.5):
    #         pyautogui.click(x, y)
    #     else:
    #         pyautogui.rightClick(x, y)
    # elif widget == "list" or widget == "scroll_bar" or widget == "slider":
    #     x = random.randint(x_start, x_end)
    #     y = random.randint(y_start, y_end)
    #     pyautogui.moveTo(x, y)
    #     action = random.random()
    #     if action < 0.4:
    #         pyautogui.click(x, y)
    #     elif action < 0.5:
    #         pyautogui.rightClick(x, y)
    #     else:
    #         pyautogui.click(x, y)
    #         x = random.randint(x_start, x_end)
    #         y = random.randint(y_start, y_end)
    #         pyautogui.dragTo(x, y)
    #         pyautogui.mouseUp(x, y)
    #         pyautogui.click(x, y)
    # elif widget == "tree":
    #     pyautogui.click(x, y)
    #     x = random.randint(x_start, x_end)
    #     y = random.randint(y_start, y_end)
    #     pyautogui.moveTo(x, y)
    #
    #     if (random.random() < 0.5):
    #         pyautogui.doubleClick(x, y)
    #     else:
    #         pyautogui.rightClick(x, y)
    #
    #     x = random.randint(x_start, x_end)
    #     y = random.randint(y_start, y_end)
    #
    #     pyautogui.moveTo(x, y)
    #
    #     pyautogui.click(x, y)
    # elif widget == "text_field":
    #     if (random.random() < 0.5):
    #         pyautogui.click(x, y)
    #     else:
    #         pyautogui.rightClick(x, y)
    #     pyautogui.typewrite(input_string, interval=0.01)
    #     # if random.random() < 0.2:
    #     #     pyautogui.press('enter')
    # elif widget == "combo_box":
    #
    #     if (random.random() < 0.2): #press right button of cbox
    #         x = x_start + ((x_end-x_start)*0.85)
    #
    #     if (random.random() < 0.5):
    #         pyautogui.click(x, y)
    #     else:
    #         pyautogui.rightClick(x, y)
    #
    #     event = event + 1
    #     next_y = best_box[2]+random.random()*0.5
    #     x = int(max(app_x, min(app_x + app_w - 10, app_x + (best_box[1]*app_w))))
    #     y = int(max(app_y, min(app_y + app_h - 10, app_y + ((next_y)*app_h))))
    #
    #     pyautogui.click(x, y)
    #
    #     y_start = max(0, min(height, int(height*(next_y - best_box[4]/2))-10))
    #     y_end = max(0, min(height, int(height*(next_y+best_box[4]/2))+10))
    #
    #     x_start = max(0, min(width, int(width*(best_box[1]-best_box[3]/2))-10))
    #     x_end = max(0, min(width, int(width*(best_box[1]+best_box[3]/2))+10))
    #     image_clicked = raw_image[y_start:y_end,
    #                     x_start:x_end]
    #
    #     output_img = output_dir + "/images/" + str(event)
    #
    #     np.save(output_img, image_clicked)
    #
    #     cv2.imwrite(output_img + ".jpg", image_clicked)
    # else:
    #     print(widget, "unrecognised")
    #

    # pyautogui.mouseUp(x, y)

    random_interaction = random.random()

    if random_interaction < 0.888888888888: # just a normal click
        if random.random() < 0.5:
            pyautogui.doubleClick(x, y, interval=0.01)
        else:
            pyautogui.rightClick(x, y)
    else: # click and type 'Hello world!'
        pyautogui.doubleClick(x, y, interval=0.01)
        pyautogui.typewrite(generate_input_string(), interval=0.01)

def select_random_box(proc_boxes):
    prob_dist = proc_boxes[..., 5] / sum(proc_boxes[..., 5])

    rand_index = np.random.choice(proc_boxes.shape[0], 1, p=prob_dist)

    best_box = proc_boxes.tolist()[rand_index[0]]

    return best_box

def prepare_screenshot(raw_image):
    st = time.time()
    raw_image = data_loader.pad_image(raw_image)
    et = time.time()
    if debug:
        print("PADDING:", et - st)
    image = cv2.resize(raw_image, (cfg.width, cfg.height))
    #
    # x, y, w, h = convert_coords(0.3, 0.3, 0.4, 0.4, aspect)
    # cv2.rectangle(image,
    #               (int(x*cfg.width), int(y*cfg.height)),
    #               (int(x+w*cfg.width), int(y+h*cfg.height)),
    #               (1, 1, 0.3), -1, 8)
    #
    # cv2.imshow('image',image)
    # cv2.waitKey(0)
    # cv2.destroyAllWindows()

    images = np.reshape(image, [1, cfg.width, cfg.height, 1])

    imgs = (images/127.5)-1

    return imgs

def convert_boxes(boxes):
    return yolo.convert_net_to_bb(boxes, filter_top=False)[0]

if __name__ == '__main__':
    # Collect events until released
    with keyboard.Listener(on_release=on_release) as listener:
        if len(sys.argv) > 1:
            cfg.window_name = sys.argv[1]

        with tf.device(cfg.gpu):

            event = 0

            yolo = Yolo()

            yolo.create_network()

            saver = tf.train.Saver()

            model_file = os.getcwd() + "/" + cfg.weights_dir + "/model.ckpt"

            config = tf.ConfigProto(allow_soft_placement = True)

            states = []

            runtime = round(time.time())

            output_dir = cfg.output_dir + "/" + str(runtime)

            if not os.path.exists(output_dir):
                os.makedirs(output_dir)

            if not os.path.exists(output_dir + "/images"):
                os.makedirs(output_dir + "/images")

            test_file = output_dir + "/test.txt"

            with open(test_file, "w+") as t_f:
                t_f.write("")

            with tf.Session(config=config) as sess:

                init_op = tf.global_variables_initializer()
                model = sess.run(init_op)
                if os.path.isfile(os.getcwd() + "/" + cfg.weights_dir + "/checkpoint"):
                    saver.restore(sess, model_file)
                    print("Restored model")
                yolo.set_training(False)

                anchors = np.reshape(np.array(cfg.anchors), [-1, 2])

                start_time = time.time()

                last_image = None

                boxes = []

                interactions = []

                runtime = cfg.test_time #5 mins

                last_u_input = ""

                actions = 0

                while ((time.time() - start_time < runtime and not cfg.use_iterations) or
                       (actions < cfg.test_iterations and cfg.use_iterations)) and running:
                    iteration_time = time.time()

                    exec_time = time.time() - start_time

                    os.system('wmctrl -c "firefox"')

                    app_x, app_y, app_w, app_h = get_window_size(cfg.window_name)

                    while app_w == 0:
                        time.sleep(1)
                        app_x, app_y, app_w, app_h = get_window_size(cfg.window_name)
                        if time.time() - start_time > runtime:
                            print("Couldn't find application window!")
                            break

                    if time.time() - start_time > runtime:
                        break

                    image = pyautogui.screenshot(region=(app_x, app_y, app_w, app_h)).convert("L")

                    image = np.array(image)

                    # raw_image = image[app_y:app_y+app_h, app_x:app_x+app_w]

                    ih, iw = image.shape[:2]

                    aspect = iw/ih

                    imgs = prepare_screenshot(image)

                    gen_boxes = True

                    for l in states:
                        diff = np.sum(np.square(image-l[0]))/image.size
                        if diff < 2:
                            gen_boxes = False
                            proc_boxes = l[1]

                    last_image = image

                    if gen_boxes or len(proc_boxes) < 3:

                        #print("New state found!", len(states), "states found total.")

                        st = time.time()

                        boxes = sess.run(yolo.output, feed_dict={
                            yolo.x: imgs,
                            yolo.anchors: anchors,
                        })

                        et = time.time()
                        if debug:
                            print("ANN:", et - st)

                        st = time.time()
                        p_boxes = convert_boxes(boxes)
                        # pbi = 0
                        # while pbi < p_boxes.shape[0]:
                        #     pb = p_boxes[pbi]
                        #     if pb[5] < cfg.object_detection_threshold:
                        #         p_boxes = np.delete(p_boxes, pbi, axis=0)
                        #     else:
                        #         pbi += 1

                        et = time.time()
                        if debug:
                            print("CONVERT:", et - st)

                        total = np.sum(p_boxes[:,5])

                        p_boxes[:,5] = p_boxes[:,5]/total

                        proc_boxes = p_boxes#.tolist()

                        #states.append([image, proc_boxes])

                    for box_num in range(5):

                        if len(proc_boxes) < 1:
                            cfg.object_detection_threshold *= 0.9
                            continue

                        input_string = generate_input_string()

                        #highest_conf = proc_boxes[0][5]
                        #best_box = proc_boxes[0]

                        best_box = select_random_box(proc_boxes)

                        #best_box = random.sample(proc_boxes, 1)[0]

                        rand_num = random.random()

                        # for b in proc_boxes:
                        #     #if (b[5] > highest_conf):
                        #     rand_num -= b[5]
                        #     if rand_num <= 0:
                        #         #highest_conf = b[5]
                        #         best_box = b
                        #         break;

                        np.delete(proc_boxes, best_box)

                        height, width = image.shape[:2]

                        current_box = best_box

                        best_box[1:5] = convert_coords(best_box[1], best_box[2], best_box[3], best_box[4], aspect)

                        perform_interaction(best_box)

                        actions += 1

                        # proc_boxes.remove(current_box)

                    # if sub_window:
                    #     if random.random() < 0.05:
                    #         pyautogui.press('escape')

                    end_iteration_time = time.time()
                    if debug:
                        print("Iteration Time:", end_iteration_time - iteration_time)

                    # write test info
                    csv_file = "test.csv"

                    with open(csv_file, "a") as p_f:
                        p_f.write(str(exec_time) + "," + str(actions) + ",detection," + str(iteration_time) + "," + cfg.window_name + "\n")



                print("Writing concrete tests")

                # write python regression test
                python_file = output_dir + "/test.py"

                # write visual test
                html_file = output_dir + "/test.html"

                with open(python_file, "w+") as p_f:
                    # TODO: Write python functions for click, type, etc
                    p_f.write("")

                with open(html_file, "w+") as h_f:
                    h_f.write("<html><head><title>Test " + str(runtime) + "</title></head>\n"
                                "<body>")

                for i in interactions:
                    with open(python_file, "a+") as p_f:
                        # write python regression test
                        p_f.write("click(" + str(i[1]) + ")\n")
                        if i[0] == "text_field":
                            p_f.write("type(" + i[2] + ")\n")

                    with open(html_file, "a+") as h_f:
                        # write python regression test
                        output_img = output_dir + "/images/" + str(i[1]) + ".jpg"
                        h_f.write("<br />click( <img src='" + output_img + "' /> )<br />\n")
                        if i[0] == "text_field":
                            h_f.write("type(" + i[2] + ")<br />\n")


                with open(html_file, "a+") as h_f:
                    h_f.write("</body></html>")
