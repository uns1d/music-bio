import QtQuick
import QtQuick.Controls

ScrollBar {
    id: control

    implicitWidth: 8
    policy: ScrollBar.AsNeeded

    contentItem: Rectangle {
        implicitWidth: 5
        radius: 3
        color: control.active ? "#565762" : "#34353D"
        opacity: control.size < 1 ? 0.85 : 0

        Behavior on color {
            ColorAnimation { duration: 120 }
        }
    }

    background: Item {}
}
