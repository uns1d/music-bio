import QtQuick
import QtQuick.Controls

Slider {
    id: control

    implicitHeight: 32
    hoverEnabled: true

    background: Rectangle {
        x: control.leftPadding
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.availableWidth
        height: 4
        radius: 2
        color: "#2B2C32"

        Rectangle {
            width: control.visualPosition * parent.width
            height: parent.height
            radius: parent.radius
            color: backend.accentSecondary
        }
    }

    handle: Rectangle {
        x: control.leftPadding
            + control.visualPosition * (control.availableWidth - width)
        y: control.topPadding + control.availableHeight / 2 - height / 2
        width: control.hovered || control.pressed ? 18 : 16
        height: width
        radius: width / 2
        color: control.pressed ? "#D5D2D9" : "#BDBAC2"
        border.width: 3
        border.color: "#303139"

        Behavior on width {
            NumberAnimation { duration: 100 }
        }
    }
}
