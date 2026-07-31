import QtQuick
import QtQuick.Controls

ComboBox {
    id: control

    implicitHeight: 44
    leftPadding: 14
    rightPadding: 42
    hoverEnabled: true

    delegate: ItemDelegate {
        id: option

        required property var modelData
        required property int index

        width: control.width - 8
        height: 40
        leftPadding: 12
        rightPadding: 12
        highlighted: control.highlightedIndex === index

        contentItem: Text {
            text: option.modelData
            color: option.highlighted ? "#E8E5EE" : "#A6A5AD"
            font.pixelSize: 13
            verticalAlignment: Text.AlignVCenter
            elide: Text.ElideRight
        }

        background: Rectangle {
            radius: 10
            color: option.highlighted || option.hovered ? "#25262D" : "transparent"
        }
    }

    indicator: Item {
        x: control.width - width - 12
        y: (control.height - height) / 2
        width: 18
        height: 18

        Text {
            anchors.centerIn: parent
            text: "⌄"
            color: control.hovered || control.popup.visible ? "#B9B6C2" : "#74747E"
            font.pixelSize: 17
        }
    }

    contentItem: Text {
        text: control.displayText
        color: "#D8D6DE"
        font.pixelSize: 13
        verticalAlignment: Text.AlignVCenter
        elide: Text.ElideRight
    }

    background: Rectangle {
        radius: 12
        color: control.popup.visible
            ? "#202127"
            : (control.hovered ? "#1D1E24" : "#18191E")
        border.width: 1
        border.color: control.popup.visible
            ? backend.accentPrimary
            : (control.hovered ? "#3C3D47" : "#2C2D35")

        Behavior on color {
            ColorAnimation { duration: 120 }
        }
        Behavior on border.color {
            ColorAnimation { duration: 120 }
        }
    }

    popup: Popup {
        y: control.height + 6
        width: control.width
        implicitHeight: Math.min(contentItem.implicitHeight + 8, 230)
        padding: 4

        contentItem: ListView {
            clip: true
            implicitHeight: contentHeight
            model: control.popup.visible ? control.delegateModel : null
            currentIndex: control.highlightedIndex
            spacing: 2

            ScrollIndicator.vertical: ScrollIndicator {}
        }

        background: Rectangle {
            radius: 14
            color: "#15161B"
            border.width: 1
            border.color: "#32333C"
        }
    }
}
