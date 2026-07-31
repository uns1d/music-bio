import QtQuick
import QtQuick.Controls

Button {
    id: control

    property color accent: backend.accentPrimary
    property bool subtle: false
    property bool danger: false

    implicitWidth: 144
    implicitHeight: 46
    hoverEnabled: true

    contentItem: Text {
        text: control.text
        color: control.enabled ? "#E6E4EA" : "#666771"
        font.pixelSize: 14
        font.weight: Font.DemiBold
        horizontalAlignment: Text.AlignHCenter
        verticalAlignment: Text.AlignVCenter
    }

    background: Rectangle {
        radius: 14
        color: {
            if (!control.enabled)
                return "#17181D"
            if (control.subtle)
                return control.hovered ? "#24252C" : "#1A1B21"
            if (control.danger)
                return control.hovered ? "#A73C54" : "#96344A"
            if (control.down)
                return Qt.darker(control.accent, 1.18)
            return control.hovered ? Qt.darker(control.accent, 1.05) : control.accent
        }
        border.width: 1
        border.color: control.hovered
            ? (control.subtle ? "#4A4C57" : Qt.lighter(control.accent, 1.08))
            : (control.subtle ? "#30313A" : Qt.darker(control.accent, 1.12))
        scale: control.down ? 0.97 : 1

        Behavior on color {
            ColorAnimation { duration: 150 }
        }
        Behavior on scale {
            NumberAnimation { duration: 100; easing.type: Easing.OutCubic }
        }

    }
}
