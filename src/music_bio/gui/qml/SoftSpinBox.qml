import QtQuick
import QtQuick.Controls

SpinBox {
    id: control

    implicitHeight: 44
    hoverEnabled: true
    editable: false

    contentItem: TextInput {
        z: 2
        text: control.textFromValue(control.value, control.locale)
        color: "#D8D6DE"
        selectionColor: backend.accentPrimary
        selectedTextColor: "#F1EFF5"
        horizontalAlignment: Text.AlignLeft
        verticalAlignment: Text.AlignVCenter
        leftPadding: 13
        rightPadding: 38
        readOnly: true
        font.pixelSize: 13
    }

    up.indicator: Rectangle {
        x: control.width - width
        y: 0
        width: 34
        height: control.height / 2
        radius: 8
        color: control.up.pressed
            ? "#30313A"
            : (control.up.hovered ? "#25262D" : "transparent")

        Text {
            anchors.centerIn: parent
            text: "+"
            color: control.up.hovered ? "#C6C3CD" : "#777781"
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
    }

    down.indicator: Rectangle {
        x: control.width - width
        y: control.height / 2
        width: 34
        height: control.height / 2
        radius: 8
        color: control.down.pressed
            ? "#30313A"
            : (control.down.hovered ? "#25262D" : "transparent")

        Text {
            anchors.centerIn: parent
            text: "−"
            color: control.down.hovered ? "#C6C3CD" : "#777781"
            font.pixelSize: 14
            font.weight: Font.DemiBold
        }
    }

    background: Rectangle {
        radius: 12
        color: control.hovered ? "#1D1E24" : "#18191E"
        border.width: 1
        border.color: control.hovered ? "#3C3D47" : "#2C2D35"

        Rectangle {
            anchors {
                top: parent.top
                bottom: parent.bottom
                right: parent.right
                rightMargin: 34
            }
            width: 1
            color: "#292A31"
        }
    }
}
