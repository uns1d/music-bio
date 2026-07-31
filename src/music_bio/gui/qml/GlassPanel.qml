import QtQuick

Rectangle {
    id: panel

    default property alias contentData: content.data
    property color panelColor: "#14151B"
    property color borderColor: "#292B33"
    property real panelOpacity: 0.96

    radius: 18
    color: Qt.rgba(
        panelColor.r,
        panelColor.g,
        panelColor.b,
        panelOpacity
    )
    border.width: 1
    border.color: borderColor
    clip: true

    Rectangle {
        anchors {
            left: parent.left
            right: parent.right
            top: parent.top
            margins: 1
        }
        height: 1
        color: "#16FFFFFF"
    }

    Item {
        id: content
        anchors.fill: parent
    }
}
