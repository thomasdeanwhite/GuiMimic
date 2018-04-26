package com.thomasdeanwhite.gui.runtypes;

import com.thomasdeanwhite.gui.App;
import com.thomasdeanwhite.gui.Properties;
import com.thomasdeanwhite.gui.output.StateComparator;
import com.thomasdeanwhite.gui.runtypes.interaction.*;
import com.thomasdeanwhite.gui.runtypes.interaction.Event;
import com.thomasdeanwhite.gui.sampler.MouseEvent;
import com.thomasdeanwhite.gui.util.FileHandler;
import javafx.scene.input.KeyCode;
import org.jnativehook.GlobalScreen;
import org.jnativehook.NativeHookException;
import org.jnativehook.keyboard.NativeKeyEvent;
import org.jnativehook.keyboard.NativeKeyListener;

import java.awt.*;

import java.awt.event.InputEvent;
import java.awt.image.BufferedImage;
import java.awt.image.DataBufferInt;
import java.io.File;
import java.io.IOException;
import java.util.logging.Level;
import java.util.logging.Logger;


/**
 * Created by thoma on 20/06/2017.
 */
public class ApplicationTestingRunType implements RunType, NativeKeyListener {

    private Rectangle bounds;
    private boolean running = true;
    private ApplicationThread appThread;
    private boolean paused = false;

    public boolean isRunning() {
        return running;
    }

    @Override
    public int run() {

        try {
            GlobalScreen.registerNativeHook();
        } catch (NativeHookException e) {
            e.printStackTrace();
        }

        // Get the logger for "org.jnativehook" and set the level to warning.
        Logger logger = Logger.getLogger(GlobalScreen.class.getPackage().getName());
        logger.setLevel(Level.WARNING);
        logger.setUseParentHandlers(false);

        GlobalScreen.addNativeKeyListener(this);


        Interaction interaction;

        switch (Properties.INTERACTION) {
            case DEEP_LEARNING:
                interaction = new DeepLearningInteraction();
                break;
            case EXPLORATION_DEEP_LEARNING:
                interaction = new ExplorationDeepLearningInteraction();
                break;
            case MONKEY:
                interaction = new MonkeyInteraction();
                break;
            case USER:
            default:
                interaction = new UserInteraction();
        }


        appThread = new ApplicationThread();

        App.out.println("- Using exec: " + Properties.EXEC);

        if (!appThread.isAppRunning()) {
            appThread.run();
        }

        try {
            interaction.load();
        } catch (IOException e) {
            e.printStackTrace(App.out);
            return -1;
        }

        long startTime = System.currentTimeMillis();

        long finishTime = startTime + Properties.RUNTIME;

        long currentTime;


        Robot r;
        try {
            r = new Robot();
        } catch (AWTException e) {
            e.printStackTrace(App.out);
            return -2;
        }

        do {

            if (!appThread.isAppRunning()) {
                appThread.run();

            }
            currentTime = System.currentTimeMillis();
            long timePassed = currentTime - startTime;

            if (paused){
                try {
                    Thread.sleep(100);
                } catch (InterruptedException e) {
                    e.printStackTrace();
                }

                continue;
            }

            Event e = interaction.interact(timePassed);

            if (bounds == null) {
                Window activeWindow = javax.swing.FocusManager.getCurrentManager().getActiveWindow();

                bounds = new Rectangle(Toolkit.getDefaultToolkit()
                        .getScreenSize());

                if (activeWindow != null) {
                    bounds = new Rectangle(
                            (int) activeWindow.getBounds().getX(),
                            (int) activeWindow.getBounds().getY(),
                            (int) activeWindow.getBounds().getWidth(),
                            (int) activeWindow.getBounds().getHeight());
                }
            }

            int mouseX = (int) (bounds.getX() + e.getMouseX());
            int mouseY = (int) (bounds.getY() + e.getMouseY());

            r.mouseMove(mouseX, mouseY);
            try {
            Thread.sleep(10);
            } catch (InterruptedException ie){
                //done goofed
            }
            if (e.getEvent().equals(MouseEvent.LEFT_CLICK)) {
                click(r, InputEvent.BUTTON1_MASK);
            } else if (e.getEvent().equals(MouseEvent.RIGHT_CLICK)) {
                click(r, InputEvent.BUTTON2_MASK);
            } else if (e.getEvent().equals(MouseEvent.LEFT_DOWN)) {
                mouseDown(r, InputEvent.BUTTON1_MASK);
                //click(r, InputEvent.BUTTON1_MASK);
            } else if (e.getEvent().equals(MouseEvent.RIGHT_DOWN)) {
                mouseDown(r, InputEvent.BUTTON2_MASK);
                //click(r, InputEvent.BUTTON2_MASK);
            } else if (e.getEvent().equals(MouseEvent.LEFT_UP)) {
                mouseUp(r, InputEvent.BUTTON1_MASK);
            } else if (e.getEvent().equals(MouseEvent.RIGHT_UP)) {
                mouseUp(r, InputEvent.BUTTON2_MASK);
            } else if (e.getEvent().equals(MouseEvent.KEYBOARD_INPUT)) {
                keyTyped(r);
            } else if (e.getEvent().equals(MouseEvent.SHORTCUT_INPUT)) {
                shortcutPressed(r);
            }

            interaction.postInteraction(e);

            try {
                Thread.sleep(10);
            } catch (InterruptedException ie){
                //done goofed
            }

        } while (currentTime < finishTime && running);

        try {
            //screnshot app if doesn't exist
            File screenshot = new File(Properties.TESTING_OUTPUT + "/screenshot.csv");

            if (!screenshot.exists()) {

                screenshot.createNewFile();


                BufferedImage screen = StateComparator.screenshot();
                int[] data = ((DataBufferInt) screen.getRaster().getDataBuffer()).getData();

                StringBuilder sb = new StringBuilder();
                int width = screen.getWidth();
                sb.append("x,y,pixel\n");

                for (int i = 0; i < screen.getWidth(); i++) {
                    for (int j = 0; j < screen.getHeight(); j++) {
                        int blackAndWhite = data[(j * width) + i];
                        blackAndWhite = (int) ((0.333 * ((blackAndWhite >> 16) &
                                0x0FF) +
                                0.333 * ((blackAndWhite >> 8) & 0x0FF) +
                                0.333 * (blackAndWhite & 0x0FF)));
                        sb.append(i + "," + j + "," + blackAndWhite + "\n");
                    }
                }

                FileHandler.writeToFile(screenshot, sb.toString());
            }
        } catch (IOException e) {
            e.printStackTrace();
        }

        appThread.kill();

        return 0;
    }


    public void click(Robot r, int button) {
        r.mousePress(button);

        try {
            Thread.sleep(10);
        } catch (InterruptedException exc) {
        }

        r.mouseRelease(button);
    }

    public void mouseDown(Robot r, int button) {
        r.mousePress(button);
    }

    public void mouseUp(Robot r, int button) {
        r.mouseRelease(button);
    }

    public void keyTyped(Robot r) {
        int keycode = 48 + (int)(Math.random()*42);
        r.keyPress(keycode);
        r.keyRelease(keycode);
    }

    public void shortcutPressed(Robot r) {
        r.keyPress(KeyCode.ENTER.ordinal());
    }


    private int keyPressedToExit = 0;


    @Override
    public void nativeKeyPressed(NativeKeyEvent nativeKeyEvent) {
        if (nativeKeyEvent.getKeyCode() == NativeKeyEvent.VC_ESCAPE) {
            keyPressedToExit++;
        } else {
            keyPressedToExit = 0;
        }

        if (nativeKeyEvent.getKeyCode() == NativeKeyEvent.VC_PAUSE) {
            paused = !paused;
        }

        if (keyPressedToExit >= 3) {
            running = false;
            App.out.println("!!! User Initiated Exit !!!");
            appThread.kill();
            App.getApp().end();
            System.exit(0);
        }
    }

    @Override
    public void nativeKeyReleased(NativeKeyEvent nativeKeyEvent) {

    }

    @Override
    public void nativeKeyTyped(NativeKeyEvent nativeKeyEvent) {

    }
}