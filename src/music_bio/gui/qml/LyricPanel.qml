import QtQuick
import QtQuick.Layouts

Item {
    id: control

    property string lyric: ""
    property string nextLyric: ""
    property color accent: backend.accentSecondary
    property string shownLyric: ""
    property string shownNextLyric: ""

    visible: lyric.length > 0 || nextLyric.length > 0
    implicitHeight: visible ? content.implicitHeight : 0

    function scheduleUpdate() {
        updateTimer.restart()
    }

    onLyricChanged: scheduleUpdate()
    onNextLyricChanged: scheduleUpdate()

    Component.onCompleted: {
        shownLyric = lyric
        shownNextLyric = nextLyric
    }

    ColumnLayout {
        id: content

        anchors {
            top: parent.top
            left: parent.left
            right: parent.right
        }
        spacing: 8

        Text {
            Layout.fillWidth: true
            text: "АКТИВНАЯ СТРОКА"
            visible: control.shownLyric.length > 0
            color: control.accent
            font.pixelSize: 9
            font.weight: Font.Bold
            font.letterSpacing: 1.5
        }

        Item {
            Layout.fillWidth: true
            Layout.preferredHeight: lyricLines.implicitHeight

            Column {
                id: lyricLines

                width: parent.width
                spacing: 8

                Text {
                    width: parent.width
                    visible: control.shownLyric.length > 0
                    text: control.shownLyric
                    color: "#E8E5EB"
                    font.pixelSize: 18
                    font.weight: Font.Medium
                    wrapMode: Text.WordWrap
                }

                Text {
                    width: parent.width
                    visible: control.shownNextLyric.length > 0
                    text: control.shownNextLyric
                    color: "#77767E"
                    opacity: 0.68
                    font.pixelSize: 15
                    font.weight: Font.Normal
                    wrapMode: Text.WordWrap
                }

                transform: Translate {
                    id: lineOffset
                }
            }
        }
    }

    Timer {
        id: updateTimer

        interval: 0
        repeat: false
        onTriggered: {
            if (control.shownLyric === control.lyric) {
                control.shownNextLyric = control.nextLyric
                return
            }
            lineTransition.restart()
        }
    }

    SequentialAnimation {
        id: lineTransition

        ParallelAnimation {
            NumberAnimation {
                target: lyricLines
                property: "opacity"
                to: 0
                duration: 120
                easing.type: Easing.InCubic
            }
            NumberAnimation {
                target: lineOffset
                property: "y"
                to: -6
                duration: 120
                easing.type: Easing.InCubic
            }
        }
        ScriptAction {
            script: {
                control.shownLyric = control.lyric
                control.shownNextLyric = control.nextLyric
                lineOffset.y = 8
            }
        }
        ParallelAnimation {
            NumberAnimation {
                target: lyricLines
                property: "opacity"
                to: 1
                duration: 220
                easing.type: Easing.OutCubic
            }
            NumberAnimation {
                target: lineOffset
                property: "y"
                to: 0
                duration: 220
                easing.type: Easing.OutCubic
            }
        }
    }
}
