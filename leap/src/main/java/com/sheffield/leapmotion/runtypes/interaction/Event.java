package com.sheffield.leapmotion.runtypes.interaction;

import com.sheffield.leapmotion.sampler.MouseEvent;

import java.awt.*;
import java.io.Serializable;

/**
 * Created by thoma on 21/06/2017.
 */
public class Event implements Serializable {

    public static Rectangle bounds;

    static {
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

    public static Event NONE = new Event(MouseEvent.NONE, 0, 0, 0, -1);

    private long timestamp;
    private MouseEvent event;
    private int mouseX;
    private int mouseY;
    private int eventIndex = 0;

    public void moveMouse(int x, int y){
        mouseX += x;
        mouseY += y;
    }

    public Event(MouseEvent me, int x, int y, long time, int index) {
        event = me;
        mouseX = x;
        mouseY = y;
        timestamp = time;
        eventIndex = index;
    }

    public MouseEvent getEvent() {
        return event;
    }

    public int getMouseX() {
        return mouseX;
    }

    public int getMouseY() {
        return mouseY;
    }

    public long getTimestamp() {
        return timestamp;
    }

    public void reduceTimestamp(long x) {
        timestamp = timestamp - x;
    }

    public int getEventIndex() {
        return eventIndex;
    }

    public void setEventIndex(int eventIndex) {
        this.eventIndex = eventIndex;
    }

    public String toCsv(float lastMouseX, float lastMouseY) {
        return ((mouseX - lastMouseX)/bounds.getWidth()) + "," + ((mouseY - lastMouseY)/bounds.getHeight()) + "," + leftClickToFloat() + "," +
                rightClickToFloat();
    }

    public String toString() {
        return "(" + mouseX + " " + mouseY + " " + leftClickToFloat() + " " +
                rightClickToFloat() + ")";
    }

    private float leftClickToFloat() {
        return (1 + eventToFloat(MouseEvent.LEFT_DOWN) -
                eventToFloat(MouseEvent.LEFT_UP))/2;
    }

    private float rightClickToFloat() {
        return (1 + eventToFloat(MouseEvent.RIGHT_DOWN) -
                eventToFloat(MouseEvent.RIGHT_UP))/2;
    }

    private float eventToFloat(MouseEvent event) {
        if (event.equals(this.event)) {
            return 1;
        }
        return 0;
    }
}
