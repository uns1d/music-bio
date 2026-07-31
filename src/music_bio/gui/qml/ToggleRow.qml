import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

RowLayout {
    id: row

    property alias title: titleLabel.text
    property string description: ""
    property alias checked: toggle.checked

    spacing: 16

    ColumnLayout {
        Layout.fillWidth: true
        spacing: 3

        Label {
            id: titleLabel
            color: "#DCD9E0"
            font.pixelSize: 14
            font.weight: Font.Medium
        }

        Label {
            visible: row.description.length > 0
            Layout.fillWidth: true
            text: row.description
            color: "#77767E"
            font.pixelSize: 11
            wrapMode: Text.WordWrap
        }
    }

    Switch {
        id: toggle
        implicitWidth: 48
        implicitHeight: 27

        indicator: Rectangle {
            implicitWidth: 46
            implicitHeight: 26
            x: toggle.leftPadding
            y: parent.height / 2 - height / 2
            radius: height / 2
            color: toggle.checked ? backend.accentPrimary : "#282930"
            border.width: 1
            border.color: toggle.checked ? backend.accentSecondary : "#414249"

            Rectangle {
                x: toggle.checked ? parent.width - width - 4 : 4
                anchors.verticalCenter: parent.verticalCenter
                width: 18
                height: 18
                radius: 9
                color: "#E5E2E8"

                Behavior on x {
                    NumberAnimation { duration: 170; easing.type: Easing.OutCubic }
                }
            }

            Behavior on color {
                ColorAnimation { duration: 170 }
            }
        }
    }
}
