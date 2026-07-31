import QtQuick
import QtQuick.Layouts
import QtQuick.Window

Window {
    id: overlay

    property var prefs: backend.settings
    property string displayMode: prefs.overlay_mode || "card"
    property bool miniMode: displayMode === "orb"
    property bool clickThrough: Boolean(prefs.overlay_click_through)
    property bool keepOnTop: prefs.overlay_always_on_top === undefined
        ? true : Boolean(prefs.overlay_always_on_top)
    property bool geometryReady: false
    property int defaultWidth: miniMode ? 188 : (displayMode === "strip" ? 570 : 490)
    property int defaultHeight: miniMode ? 226 : (displayMode === "strip" ? 76 : 138)
    property int modeMinimumWidth: miniMode ? 160 : (displayMode === "strip" ? 360 : 360)
    property int modeMinimumHeight: miniMode ? 190 : (displayMode === "strip" ? 68 : 118)
    property int modeMaximumWidth: miniMode ? 420 : 900
    property int modeMaximumHeight: miniMode ? 520 : (displayMode === "strip" ? 220 : 420)

    visible: backend.overlayVisible
    transientParent: null
    width: defaultWidth
    height: defaultHeight
    minimumWidth: modeMinimumWidth
    maximumWidth: modeMaximumWidth
    minimumHeight: modeMinimumHeight
    maximumHeight: modeMaximumHeight
    color: "transparent"
    opacity: Number(prefs.overlay_opacity || 0.94)
    flags: Qt.Tool
        | Qt.FramelessWindowHint
        | (keepOnTop ? Qt.WindowStaysOnTopHint : 0)
        | (clickThrough ? Qt.WindowTransparentForInput : 0)

    function bounded(value, minimum, maximum) {
        return Math.max(minimum, Math.min(maximum, value))
    }

    function storedSize(suffix, fallback) {
        let value = Number(prefs["overlay_" + displayMode + "_" + suffix])
        return Number.isFinite(value) && value > 0 ? value : fallback
    }

    function keepInsideScreen() {
        let left = Number(Screen.virtualX)
        let top = Number(Screen.virtualY)
        let availableWidth = Number(Screen.desktopAvailableWidth)
        let availableHeight = Number(Screen.desktopAvailableHeight)
        if (availableWidth <= 0 || availableHeight <= 0)
            return

        let margin = 6
        width = Math.min(
            width,
            Math.max(modeMinimumWidth, availableWidth - margin * 2)
        )
        height = Math.min(
            height,
            Math.max(modeMinimumHeight, availableHeight - margin * 2)
        )
        x = bounded(x, left + margin, left + availableWidth - width - margin)
        y = bounded(y, top + margin, top + availableHeight - height - margin)
    }

    function restoreGeometry() {
        width = bounded(
            storedSize("width", defaultWidth),
            modeMinimumWidth,
            modeMaximumWidth
        )
        height = bounded(
            storedSize("height", defaultHeight),
            modeMinimumHeight,
            modeMaximumHeight
        )
        if (Number(prefs.overlay_x) >= 0)
            x = Number(prefs.overlay_x)
        if (Number(prefs.overlay_y) >= 0)
            y = Number(prefs.overlay_y)
        Qt.callLater(keepInsideScreen)
    }

    function saveGeometry() {
        backend.saveOverlayGeometry(
            displayMode,
            Math.round(x),
            Math.round(y),
            Math.round(width),
            Math.round(height)
        )
    }

    Component.onCompleted: {
        geometryReady = true
        restoreGeometry()
    }

    onDisplayModeChanged: {
        if (geometryReady)
            restoreGeometry()
    }

    onVisibleChanged: {
        if (visible) {
            keepInsideScreen()
            raise()
        }
    }

    GlassPanel {
        anchors {
            fill: parent
            margins: 2
        }
        radius: 18
        panelColor: "#14151A"
        panelOpacity: 0.96
        borderColor: backend.accentPrimary

        Rectangle {
            anchors.fill: parent
            radius: parent.radius
            opacity: 0.12
            gradient: Gradient {
                GradientStop { position: 0; color: backend.accentPrimary }
                GradientStop { position: 0.48; color: "transparent" }
                GradientStop { position: 1; color: backend.accentSecondary }
            }
        }

        DragHandler {
            id: windowDrag

            target: null
            enabled: !overlay.clickThrough
            acceptedButtons: Qt.LeftButton
            grabPermissions: PointerHandler.CanTakeOverFromAnything
            property point startPosition: Qt.point(0, 0)
            property bool nativeMove: false

            onActiveChanged: {
                if (active) {
                    startPosition = Qt.point(overlay.x, overlay.y)
                    nativeMove = overlay.startSystemMove()
                } else {
                    overlay.keepInsideScreen()
                    overlay.saveGeometry()
                }
            }

            onTranslationChanged: {
                if (active && !nativeMove) {
                    overlay.x = startPosition.x + translation.x
                    overlay.y = startPosition.y + translation.y
                }
            }
        }

        Item {
            anchors {
                fill: parent
                margins: 10
            }
            visible: overlay.miniMode

            ColumnLayout {
                anchors.fill: parent
                spacing: 8

                Rectangle {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    Layout.minimumHeight: 100
                    radius: 15
                    color: "#1B1C21"
                    border.width: 1
                    border.color: "#34353D"
                    clip: true

                    Image {
                        id: miniCover

                        anchors.fill: parent
                        source: backend.coverUrl
                        fillMode: Image.PreserveAspectCrop
                        asynchronous: true
                        visible: status === Image.Ready
                    }

                    Rectangle {
                        anchors.fill: parent
                        visible: !miniCover.visible
                        gradient: Gradient {
                            GradientStop {
                                position: 0
                                color: backend.accentPrimary
                            }
                            GradientStop {
                                position: 1
                                color: backend.accentTertiary
                            }
                        }
                        opacity: 0.82

                        Rectangle {
                            anchors.centerIn: parent
                            width: 64
                            height: 64
                            radius: 32
                            color: "#B414151A"
                            border.width: 1
                            border.color: "#6AFFFFFF"

                            Rectangle {
                                anchors.centerIn: parent
                                width: 18
                                height: 18
                                radius: 9
                                color: backend.accentSecondary
                            }
                        }
                    }

                    Rectangle {
                        anchors {
                            left: parent.left
                            right: parent.right
                            bottom: parent.bottom
                        }
                        height: 34
                        color: "#B8101115"

                        Row {
                            anchors.centerIn: parent
                            spacing: 4

                            Repeater {
                                model: 16

                                Rectangle {
                                    required property int index
                                    width: 3
                                    height: backend.playing
                                        ? 6 + ((index * 9) % 15) : 5
                                    radius: 2
                                    color: backend.accentSecondary

                                    SequentialAnimation on height {
                                        running: backend.playing
                                        loops: Animation.Infinite
                                        NumberAnimation {
                                            to: 5 + ((index * 7) % 18)
                                            duration: 360 + index * 15
                                        }
                                        NumberAnimation {
                                            to: 4 + ((index * 5) % 11)
                                            duration: 420 + index * 12
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Rectangle {
                        anchors {
                            left: parent.left
                            right: parent.right
                            bottom: parent.bottom
                        }
                        height: 3
                        color: "#303139"

                        Rectangle {
                            width: parent.width * backend.progress
                            height: parent.height
                            color: backend.accentSecondary

                            Behavior on width {
                                NumberAnimation {
                                    duration: 260
                                    easing.type: Easing.OutCubic
                                }
                            }
                        }
                    }
                }

                Text {
                    Layout.fillWidth: true
                    text: backend.title || "Яндекс Музыка"
                    color: "#F0EDF2"
                    font.pixelSize: 13
                    font.weight: Font.DemiBold
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: backend.artist || (backend.paused ? "Пауза" : "Ожидание трека")
                    color: backend.paused ? "#C39A62" : "#7F7E86"
                    font.pixelSize: 10
                    horizontalAlignment: Text.AlignHCenter
                    elide: Text.ElideRight
                }
            }
        }

        RowLayout {
            anchors {
                fill: parent
                margins: overlay.displayMode === "strip" ? 10 : 14
                rightMargin: 18
            }
            visible: !overlay.miniMode
            spacing: 14

            Rectangle {
                Layout.preferredWidth: overlay.displayMode === "strip" ? 54 : 108
                Layout.fillHeight: true
                radius: overlay.displayMode === "strip" ? 13 : 17
                color: "#1B1C21"
                clip: true

                Image {
                    id: overlayCover

                    anchors.fill: parent
                    source: backend.coverUrl
                    fillMode: Image.PreserveAspectCrop
                    asynchronous: true
                    visible: status === Image.Ready && source.toString().length > 0
                }

                Rectangle {
                    anchors.centerIn: parent
                    width: Math.min(parent.width, parent.height) * 0.58
                    height: width
                    radius: width / 2
                    color: backend.accentPrimary
                    opacity: 0.82
                    visible: overlayCover.status !== Image.Ready

                    RotationAnimator on rotation {
                        running: backend.playing
                        from: 0
                        to: 360
                        duration: 7000
                        loops: Animation.Infinite
                    }

                    Rectangle {
                        anchors.centerIn: parent
                        width: parent.width * 0.3
                        height: width
                        radius: width / 2
                        color: "#121317"
                    }
                }
            }

            ColumnLayout {
                Layout.fillWidth: true
                spacing: overlay.displayMode === "strip" ? 2 : 6

                Text {
                    Layout.fillWidth: true
                    text: backend.title || "Яндекс Музыка не играет"
                    color: "#F7F7FC"
                    font.pixelSize: overlay.displayMode === "strip" ? 14 : 17
                    font.weight: Font.DemiBold
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    text: backend.artist || backend.statusMessage
                    color: "#A09DA5"
                    font.pixelSize: overlay.displayMode === "strip" ? 11 : 13
                    elide: Text.ElideRight
                }

                Text {
                    Layout.fillWidth: true
                    visible: overlay.displayMode === "card" && backend.lyric.length > 0
                    text: backend.lyric
                    color: backend.accentSecondary
                    font.pixelSize: 12
                    elide: Text.ElideRight
                }

                Rectangle {
                    Layout.fillWidth: true
                    Layout.preferredHeight: 3
                    radius: 2
                    color: "#2B2C32"

                    Rectangle {
                        width: parent.width * backend.progress
                        height: parent.height
                        radius: parent.radius
                        color: backend.accentSecondary

                        Behavior on width {
                            NumberAnimation {
                                duration: 250
                                easing.type: Easing.OutCubic
                            }
                        }
                    }
                }
            }
        }

        Item {
            id: resizeHandle

            anchors {
                right: parent.right
                bottom: parent.bottom
                margins: 6
            }
            width: 24
            height: 24
            visible: !overlay.clickThrough
            z: 100

            Rectangle {
                anchors {
                    right: parent.right
                    bottom: parent.bottom
                    rightMargin: 3
                    bottomMargin: 4
                }
                width: 2
                height: 9
                radius: 1
                color: resizeHover.hovered ? backend.accentSecondary : "#686870"
            }

            Rectangle {
                anchors {
                    right: parent.right
                    bottom: parent.bottom
                    rightMargin: 4
                    bottomMargin: 3
                }
                width: 9
                height: 2
                radius: 1
                color: resizeHover.hovered ? backend.accentSecondary : "#686870"
            }

            HoverHandler {
                id: resizeHover
                cursorShape: Qt.SizeFDiagCursor
            }

            DragHandler {
                id: resizeDrag

                target: null
                acceptedButtons: Qt.LeftButton
                grabPermissions: PointerHandler.CanTakeOverFromAnything
                property size startSize: Qt.size(0, 0)
                property bool nativeResize: false

                onActiveChanged: {
                    if (active) {
                        startSize = Qt.size(overlay.width, overlay.height)
                        nativeResize = overlay.startSystemResize(
                            Qt.RightEdge | Qt.BottomEdge
                        )
                    } else {
                        overlay.keepInsideScreen()
                        overlay.saveGeometry()
                    }
                }

                onTranslationChanged: {
                    if (active && !nativeResize) {
                        overlay.width = overlay.bounded(
                            startSize.width + translation.x,
                            overlay.modeMinimumWidth,
                            overlay.modeMaximumWidth
                        )
                        overlay.height = overlay.bounded(
                            startSize.height + translation.y,
                            overlay.modeMinimumHeight,
                            overlay.modeMaximumHeight
                        )
                    }
                }
            }
        }
    }
}
