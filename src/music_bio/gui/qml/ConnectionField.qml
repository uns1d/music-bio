import QtQuick
import QtQuick.Controls
import QtQuick.Layouts

ColumnLayout {
    id: field

    property alias title: titleLabel.text
    property alias text: input.text
    property alias placeholderText: input.placeholderText
    property alias echoMode: input.echoMode
    property alias validator: input.validator
    property string helperText: ""

    signal editingFinished

    spacing: 7

    Label {
        id: titleLabel
        color: "#CBC8D0"
        font.pixelSize: 13
        font.weight: Font.Medium
    }

    TextField {
        id: input
        Layout.fillWidth: true
        implicitHeight: 44
        color: "#DCD9E0"
        selectionColor: backend.accentPrimary
        selectedTextColor: "#F0EDF2"
        placeholderTextColor: "#6E6D75"
        font.pixelSize: 14
        leftPadding: 14
        rightPadding: 14
        onEditingFinished: field.editingFinished()

        background: Rectangle {
            radius: 12
            color: input.activeFocus ? "#1D1E23" : "#18191E"
            border.width: 1
            border.color: input.activeFocus ? backend.accentSecondary : "#2E2F36"

            Behavior on border.color {
                ColorAnimation { duration: 150 }
            }
        }
    }

    Label {
        visible: field.helperText.length > 0
        text: field.helperText
        color: "#77767E"
        font.pixelSize: 11
        wrapMode: Text.WordWrap
        Layout.fillWidth: true
    }
}
