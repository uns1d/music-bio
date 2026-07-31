import QtQuick
import QtQuick.Controls

Button {
    id: control

    property string symbol: ""
    property string label: ""
    property bool selected: false

    implicitWidth: 158
    implicitHeight: 46
    hoverEnabled: true

    contentItem: Row {
        leftPadding: 15
        spacing: 12

        Text {
            anchors.verticalCenter: parent.verticalCenter
            width: 22
            text: control.symbol
            color: control.selected
                ? backend.accentSecondary
                : (control.hovered ? "#B8B6C0" : "#77767E")
            font.pixelSize: 18
            font.weight: Font.DemiBold
            horizontalAlignment: Text.AlignHCenter
        }

        Text {
            anchors.verticalCenter: parent.verticalCenter
            text: control.label
            color: control.selected
                ? "#E4E1E7"
                : (control.hovered ? "#C2BFC7" : "#8B8992")
            font.pixelSize: 13
            font.weight: control.selected ? Font.DemiBold : Font.Medium
        }
    }

    background: Rectangle {
        radius: 12
        color: control.selected
            ? "#222329"
            : (control.hovered ? "#1D1E23" : "transparent")
        border.width: control.selected || control.hovered ? 1 : 0
        border.color: control.selected ? "#3A3B43" : "#2A2B31"

        Rectangle {
            anchors {
                left: parent.left
                leftMargin: 4
                verticalCenter: parent.verticalCenter
            }
            width: 3
            height: 20
            radius: 2
            color: backend.accentSecondary
            visible: control.selected
        }

        Behavior on color {
            ColorAnimation { duration: 160 }
        }
    }
}
