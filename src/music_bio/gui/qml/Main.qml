import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Window

ApplicationWindow {
    id: root

    width: 1180
    height: 760
    minimumWidth: 1020
    minimumHeight: 680
    visible: true
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint
    title: "Music Bio 2.0"

    property int pageIndex: 0
    property bool closingForReal: false

    function sourceIndex(value) {
        if (value === "desktop")
            return 0
        if (value === "browser")
            return 1
        return 2
    }

    function sourceValue(index) {
        if (index === 0)
            return "desktop"
        if (index === 1)
            return "browser"
        return "auto"
    }

    function usesBrowserBridge() {
        let mode = String(backend.settings.source_mode || "browser")
        return mode === "browser" || mode === "auto"
    }

    function overlayIndex(value) {
        if (value === "strip")
            return 1
        if (value === "orb")
            return 2
        return 0
    }

    function overlayValue(index) {
        if (index === 1)
            return "strip"
        if (index === 2)
            return "orb"
        return "card"
    }

    function loadSettings() {
        let current = backend.settings
        apiIdField.text = String(current.api_id || "")
        phoneField.text = String(current.telegram_phone || "")
        apiHashField.text = String(current.api_hash || "")
        yandexTokenField.text = String(current.yandex_token || "")
        sourceCombo.currentIndex = sourceIndex(String(current.source_mode || "browser"))
        bridgePort.value = Number(current.bridge_port || 8765)
        bridgeTokenField.text = String(current.bridge_token || "")
        proxyEnabled.checked = Boolean(current.proxy_enabled)
        proxyHostField.text = String(current.proxy_host || "")
        proxyPort.value = Number(current.proxy_port || 443)
        proxySecretField.text = String(current.proxy_secret || "")
        lyricsEnabled.checked = Boolean(current.lyrics_enabled)
        restoreBio.checked = Boolean(current.restore_bio)
        templateField.text = String(current.template || "🎧 {artist} — {title} | {lyric}")
        checkInterval.value = Number(current.check_interval || 3)
        minBioInterval.value = Number(current.min_bio_interval || 12)
        overlayMode.currentIndex = overlayIndex(String(current.overlay_mode || "card"))
        overlayOpacity.value = Math.round(Number(current.overlay_opacity || 0.94) * 100)
        overlayTop.checked = Boolean(current.overlay_always_on_top)
        overlayClick.checked = Boolean(current.overlay_click_through)
        animationLevel.currentIndex = Math.max(
            0,
            Math.min(2, Number(current.animation_level || 2))
        )
        startMinimized.checked = Boolean(current.start_minimized)
    }

    function saveConnections() {
        backend.saveConnections({
            "api_id": Number(apiIdField.text || 0),
            "phone": phoneField.text,
            "api_hash": apiHashField.text,
            "yandex_token": yandexTokenField.text,
            "source_mode": sourceValue(sourceCombo.currentIndex),
            "proxy_enabled": proxyEnabled.checked,
            "proxy_host": proxyHostField.text,
            "proxy_port": proxyPort.value,
            "proxy_secret": proxySecretField.text,
            "bridge_port": bridgePort.value,
            "bridge_token": bridgeTokenField.text
        })
    }

    function saveAppearance() {
        backend.saveAppearance({
            "lyrics_enabled": lyricsEnabled.checked,
            "restore_bio": restoreBio.checked,
            "template": templateField.text,
            "check_interval": checkInterval.value,
            "min_bio_interval": minBioInterval.value,
            "overlay_mode": overlayValue(overlayMode.currentIndex),
            "overlay_opacity": overlayOpacity.value / 100,
            "overlay_always_on_top": overlayTop.checked,
            "overlay_click_through": overlayClick.checked,
            "animation_level": animationLevel.currentIndex,
            "start_minimized": startMinimized.checked
        })
    }

    Component.onCompleted: {
        loadSettings()
        if (Boolean(backend.settings.start_minimized))
            hide()
    }

    onClosing: function(close) {
        if (!closingForReal) {
            close.accepted = false
            hide()
            toast.showMessage("Music Bio продолжает работать в трее", false)
        }
    }

    Connections {
        target: backend

        function onSettingsChanged() {
            root.loadSettings()
        }

        function onAuthRequested(kind, message) {
            authDialog.authKind = kind
            authDialog.title = kind === "password"
                ? "Двухэтапная защита"
                : "Подтверждение Telegram"
            authDialog.message = message
            authValue.text = ""
            authDialog.open()
            authValue.forceActiveFocus()
        }

        function onDeviceAuthReady(url, code) {
            deviceDialog.deviceUrl = url
            deviceDialog.deviceCode = code
            deviceDialog.open()
        }

        function onToastRequested(message, isError) {
            toast.showMessage(message, isError)
        }
    }

    OverlayWindow {
        id: overlayWindow
    }

    Rectangle {
        id: shell
        anchors.fill: parent
        radius: 18
        color: "#101115"
        border.width: 1
        border.color: "#2A2B31"
        clip: true

        Rectangle {
            anchors.fill: parent
            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop { position: 0; color: "#111216" }
                GradientStop { position: 0.58; color: "#15161B" }
                GradientStop { position: 1; color: "#101216" }
            }
        }

        Item {
            anchors.fill: parent
            opacity: 0.34

            Repeater {
                model: Math.ceil(root.width / 96)
                Rectangle {
                    required property int index
                    x: index * 96
                    width: 1
                    height: root.height
                    color: "#17181D"
                }
            }

            Repeater {
                model: Math.ceil(root.height / 96)
                Rectangle {
                    required property int index
                    y: index * 96
                    width: root.width
                    height: 1
                    color: "#17181D"
                }
            }
        }

        Item {
            width: 460
            height: 460
            anchors {
                right: parent.right
                bottom: parent.bottom
                rightMargin: -190
                bottomMargin: -220
            }
            opacity: Number(backend.settings.animation_level || 2) === 0 ? 0.12 : 0.24

            Repeater {
                model: 4
                Rectangle {
                    required property int index
                    anchors.centerIn: parent
                    width: 220 + index * 70
                    height: width
                    radius: width / 2
                    color: "transparent"
                    border.width: 1
                    border.color: index % 2 === 0
                        ? backend.accentPrimary : backend.accentSecondary
                }
            }

            RotationAnimator on rotation {
                running: Number(backend.settings.animation_level || 2) > 0
                from: 0
                to: 360
                duration: 48000
                loops: Animation.Infinite
            }
        }

        Rectangle {
            id: accentSweep
            y: 0
            width: 220
            height: 2
            radius: 1
            color: backend.accentSecondary
            opacity: Number(backend.settings.animation_level || 2) === 0 ? 0.34 : 0.65

            SequentialAnimation on x {
                running: Number(backend.settings.animation_level || 2) > 0
                loops: Animation.Infinite
                NumberAnimation {
                    from: -accentSweep.width
                    to: root.width
                    duration: 8500
                    easing.type: Easing.InOutSine
                }
                PauseAnimation { duration: 2400 }
            }
        }

        ColumnLayout {
            anchors.fill: parent
            spacing: 0

            Item {
                id: titleBar
                Layout.fillWidth: true
                Layout.preferredHeight: 66

                MouseArea {
                    anchors.fill: parent
                    acceptedButtons: Qt.LeftButton
                    onPressed: root.startSystemMove()
                }

                RowLayout {
                    anchors {
                        fill: parent
                        leftMargin: 22
                        rightMargin: 16
                    }
                    spacing: 12

                    Rectangle {
                        Layout.preferredWidth: 34
                        Layout.preferredHeight: 34
                        radius: 10
                        color: "#1C1D23"
                        border.width: 1
                        border.color: "#34353D"

                        Text {
                            anchors.centerIn: parent
                            text: "♫"
                            color: backend.accentSecondary
                            font.pixelSize: 18
                            font.weight: Font.Bold
                        }
                    }

                    Column {
                        Layout.fillWidth: true
                        spacing: 1

                        Text {
                            text: "MUSIC BIO"
                            color: "#E8E6EC"
                            font.pixelSize: 14
                            font.weight: Font.Bold
                            font.letterSpacing: 1.8
                        }

                        Text {
                            text: "TELEGRAM MUSIC STATUS  ·  2.0"
                            color: "#75747D"
                            font.pixelSize: 9
                            font.letterSpacing: 1.2
                        }
                    }

                    Rectangle {
                        Layout.preferredWidth: statusText.implicitWidth + 30
                        Layout.preferredHeight: 30
                        radius: 15
                        color: backend.running ? "#172722" : "#1C1D22"
                        border.width: 1
                        border.color: backend.running ? "#357D6A" : "#34353C"

                        Row {
                            anchors.centerIn: parent
                            spacing: 8

                            Rectangle {
                                width: 7
                                height: 7
                                radius: 4
                                color: backend.running ? "#62C7A7" : "#77777F"

                                SequentialAnimation on opacity {
                                    running: backend.running
                                    loops: Animation.Infinite
                                    NumberAnimation { to: 0.3; duration: 650 }
                                    NumberAnimation { to: 1; duration: 650 }
                                }
                            }

                            Text {
                                id: statusText
                                text: backend.running ? "РАБОТАЕТ" : "ОСТАНОВЛЕНО"
                                color: backend.running ? "#A0DCC9" : "#98979F"
                                font.pixelSize: 10
                                font.weight: Font.Bold
                                font.letterSpacing: 0.8
                            }
                        }
                    }

                    Button {
                        id: minimizeButton
                        implicitWidth: 42
                        implicitHeight: 38
                        text: "—"
                        onClicked: root.hide()
                        contentItem: Text {
                            text: minimizeButton.text
                            color: "#A8AABC"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 16
                        }
                        background: Rectangle {
                            radius: 10
                            color: minimizeButton.hovered ? "#222329" : "transparent"
                            border.width: minimizeButton.hovered ? 1 : 0
                            border.color: "#34353D"
                        }
                    }

                    Button {
                        id: hideButton
                        implicitWidth: 42
                        implicitHeight: 38
                        text: "×"
                        onClicked: root.hide()
                        contentItem: Text {
                            text: hideButton.text
                            color: "#A8AABC"
                            horizontalAlignment: Text.AlignHCenter
                            verticalAlignment: Text.AlignVCenter
                            font.pixelSize: 20
                        }
                        background: Rectangle {
                            radius: 10
                            color: hideButton.hovered ? "#3A242B" : "transparent"
                            border.width: hideButton.hovered ? 1 : 0
                            border.color: "#60404A"
                        }
                    }
                }
            }

            RowLayout {
                Layout.fillWidth: true
                Layout.fillHeight: true
                Layout.margins: 12
                Layout.topMargin: 0
                spacing: 12

                GlassPanel {
                    Layout.preferredWidth: 190
                    Layout.fillHeight: true
                    radius: 18
                    panelColor: "#111217"
                    panelOpacity: 0.98
                    borderColor: "#292A30"

                    Column {
                        anchors {
                            top: parent.top
                            horizontalCenter: parent.horizontalCenter
                            topMargin: 18
                        }
                        spacing: 7

                        NavButton {
                            symbol: "⌂"
                            label: "Обзор"
                            selected: root.pageIndex === 0
                            ToolTip.visible: hovered
                            ToolTip.text: "Главная"
                            onClicked: root.pageIndex = 0
                        }

                        NavButton {
                            symbol: "⌁"
                            label: "Подключения"
                            selected: root.pageIndex === 1
                            ToolTip.visible: hovered
                            ToolTip.text: "Подключения"
                            onClicked: root.pageIndex = 1
                        }

                    }

                    Column {
                        id: engineButton
                        anchors {
                            bottom: parent.bottom
                            horizontalCenter: parent.horizontalCenter
                            bottomMargin: 18
                        }
                        width: 158
                        spacing: 8

                        Rectangle {
                            width: parent.width
                            height: 1
                            color: "#292A30"
                        }

                        NavButton {
                            symbol: "⚙"
                            label: "Оформление"
                            selected: root.pageIndex === 2
                            onClicked: root.pageIndex = 2
                        }

                        GlowButton {
                            width: parent.width
                            implicitHeight: 44
                            text: backend.running ? "Остановить" : "Запустить"
                            danger: backend.running
                            onClicked: backend.running
                                ? backend.stopEngine()
                                : backend.startEngine()
                        }
                    }
                }

                StackLayout {
                    Layout.fillWidth: true
                    Layout.fillHeight: true
                    currentIndex: root.pageIndex

                    Item {
                        id: dashboardPage

                        ColumnLayout {
                            anchors {
                                fill: parent
                                margins: 12
                            }
                            spacing: 16

                            RowLayout {
                                Layout.fillWidth: true

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 4

                                    Text {
                                        text: "Музыка в профиле — без лишнего шума"
                                        color: "#EAE8ED"
                                        font.pixelSize: 27
                                        font.weight: Font.DemiBold
                                    }

                                    Text {
                                        text: "Только Яндекс Музыка. Только тот трек, который играет сейчас."
                                        color: "#85848D"
                                        font.pixelSize: 13
                                    }
                                }

                                GlowButton {
                                    text: backend.running ? "Остановить" : "Запустить"
                                    danger: backend.running
                                    accent: backend.accentPrimary
                                    onClicked: backend.running
                                        ? backend.stopEngine()
                                        : backend.startEngine()
                                }

                                GlowButton {
                                    text: backend.overlayVisible ? "Скрыть оверлей" : "Оверлей"
                                    subtle: true
                                    implicitWidth: 132
                                    onClicked: backend.toggleOverlay()
                                }
                            }

                            GridLayout {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                columns: 2
                                columnSpacing: 16
                                rowSpacing: 16

                                GlassPanel {
                                    Layout.fillWidth: true
                                    Layout.fillHeight: true
                                    Layout.minimumWidth: 520

                                    Rectangle {
                                        width: 360
                                        height: 360
                                        radius: 180
                                        x: -170
                                        y: parent.height - 190
                                        color: backend.accentPrimary
                                        opacity: 0.055
                                    }

                                    Rectangle {
                                        width: 300
                                        height: 300
                                        radius: 150
                                        x: parent.width - 130
                                        y: -170
                                        color: backend.accentSecondary
                                        opacity: 0.045
                                    }

                                    RowLayout {
                                        anchors {
                                            fill: parent
                                            margins: 28
                                        }
                                        spacing: 28

                                        Rectangle {
                                            Layout.preferredWidth: 228
                                            Layout.preferredHeight: 228
                                            Layout.alignment: Qt.AlignVCenter
                                            radius: 22
                                            color: "#1A1B20"
                                            border.width: 1
                                            border.color: "#303138"
                                            clip: true

                                            Rectangle {
                                                anchors.fill: parent
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
                                                opacity: 0.18
                                            }

                                            Image {
                                                id: coverImage
                                                anchors.fill: parent
                                                source: backend.coverUrl
                                                fillMode: Image.PreserveAspectCrop
                                                asynchronous: true
                                                visible: status === Image.Ready
                                            }

                                            Rectangle {
                                                anchors.centerIn: parent
                                                width: 118
                                                height: 118
                                                radius: 59
                                                color: "#CE15161B"
                                                border.width: 1
                                                border.color: "#4C4D56"
                                                visible: !coverImage.visible

                                                RotationAnimator on rotation {
                                                    running: backend.yandexConnected
                                                    from: 0
                                                    to: 360
                                                    duration: 9000
                                                    loops: Animation.Infinite
                                                }

                                                Repeater {
                                                    model: 3
                                                    Rectangle {
                                                        required property int index
                                                        anchors.centerIn: parent
                                                        width: 98 - index * 22
                                                        height: width
                                                        radius: width / 2
                                                        color: "transparent"
                                                        border.width: 1
                                                        border.color: "#383941"
                                                    }
                                                }

                                                Rectangle {
                                                    anchors.centerIn: parent
                                                    width: 28
                                                    height: 28
                                                    radius: 14
                                                    color: backend.yandexConnected
                                                        ? backend.accentSecondary : "#55565F"
                                                }
                                            }

                                            Rectangle {
                                                anchors {
                                                    left: parent.left
                                                    right: parent.right
                                                    bottom: parent.bottom
                                                }
                                                height: 54
                                                color: "#D3111216"

                                                Row {
                                                    anchors.centerIn: parent
                                                    spacing: 5

                                                    Repeater {
                                                        model: 18
                                                        Rectangle {
                                                            required property int index
                                                            width: 3
                                                            radius: 2
                                                            color: backend.accentSecondary
                                                            height: backend.playing
                                                                ? 8 + ((index * 13) % 22)
                                                                : 5

                                                            SequentialAnimation on height {
                                                                running: backend.playing
                                                                loops: Animation.Infinite
                                                                NumberAnimation {
                                                                    to: 7 + ((index * 7) % 27)
                                                                    duration: 360 + index * 17
                                                                }
                                                                NumberAnimation {
                                                                    to: 5 + ((index * 11) % 15)
                                                                    duration: 410 + index * 13
                                                                }
                                                            }
                                                        }
                                                    }
                                                }
                                            }
                                        }

                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            Layout.alignment: Qt.AlignVCenter
                                            spacing: 11

                                            Text {
                                                text: "СЕЙЧАС В BIO"
                                                color: backend.accentSecondary
                                                font.pixelSize: 10
                                                font.weight: Font.Bold
                                                font.letterSpacing: 1.7
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: backend.title || (
                                                    !backend.running
                                                        ? "Запусти Music Bio"
                                                        : (root.usesBrowserBridge()
                                                            ? (backend.browserConnected
                                                                ? "Включи трек в Яндекс Музыке"
                                                                : "Подключи расширение")
                                                            : "Включи приложение Яндекс Музыки")
                                                )
                                                color: "#ECEAEF"
                                                font.pixelSize: 24
                                                font.weight: Font.DemiBold
                                                wrapMode: Text.WordWrap
                                                maximumLineCount: 2
                                                elide: Text.ElideRight
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: backend.artist || (
                                                    !backend.running
                                                        ? "Настройки сохранятся между запусками"
                                                        : (root.usesBrowserBridge()
                                                            ? backend.browserStatus
                                                            : "Ожидаю официальное приложение")
                                                )
                                                color: "#98979F"
                                                font.pixelSize: 14
                                                elide: Text.ElideRight
                                            }

                                            LyricPanel {
                                                Layout.fillWidth: true
                                                visible: backend.title.length > 0
                                                    && (backend.lyric.length > 0
                                                        || backend.nextLyric.length > 0)
                                                lyric: backend.lyric
                                                nextLyric: backend.nextLyric
                                                accent: backend.accentSecondary
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                visible: backend.title.length > 0
                                                spacing: 10

                                                Rectangle {
                                                    Layout.preferredWidth: playbackState.width + 28
                                                    Layout.preferredHeight: 28
                                                    radius: 14
                                                    color: backend.paused
                                                        ? "#242127" : "#192622"
                                                    border.width: 1
                                                    border.color: backend.paused
                                                        ? "#514651"
                                                        : "#315B4F"

                                                    Row {
                                                        anchors.centerIn: parent
                                                        spacing: 7

                                                        Rectangle {
                                                            anchors.verticalCenter: parent.verticalCenter
                                                            width: 7
                                                            height: 7
                                                            radius: 4
                                                            color: backend.paused
                                                                ? "#C39A62" : "#59BE9C"
                                                        }

                                                        Text {
                                                            id: playbackState
                                                            text: backend.paused
                                                                ? "ПАУЗА" : "ВОСПРОИЗВЕДЕНИЕ"
                                                            color: backend.paused
                                                                ? "#CBAA7C" : "#79CDB1"
                                                            font.pixelSize: 9
                                                            font.weight: Font.Bold
                                                            font.letterSpacing: 0.8
                                                        }
                                                    }
                                                }

                                                Item { Layout.fillWidth: true }

                                                Text {
                                                    text: Math.round(backend.progress * 100) + "%"
                                                    color: "#686870"
                                                    font.pixelSize: 11
                                                    font.weight: Font.Medium
                                                }
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 48
                                                visible: backend.running
                                                    && !backend.title
                                                    && root.usesBrowserBridge()
                                                    && !backend.browserConnected
                                                radius: 12
                                                color: "#1D1E23"
                                                border.width: 1
                                                border.color: "#35363E"

                                                RowLayout {
                                                    anchors {
                                                        fill: parent
                                                        leftMargin: 13
                                                        rightMargin: 13
                                                    }
                                                    spacing: 10

                                                    Rectangle {
                                                        Layout.preferredWidth: 8
                                                        Layout.preferredHeight: 8
                                                        radius: 4
                                                        color: "#C59458"
                                                    }

                                                    Text {
                                                        Layout.fillWidth: true
                                                        text: "Открой настройки источника и свяжи расширение с приложением"
                                                        color: "#B8B5BC"
                                                        font.pixelSize: 11
                                                        wrapMode: Text.WordWrap
                                                    }
                                                }
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 5
                                                radius: 3
                                                color: "#292A30"

                                                Rectangle {
                                                    width: parent.width * backend.progress
                                                    height: parent.height
                                                    radius: parent.radius
                                                    gradient: Gradient {
                                                        orientation: Gradient.Horizontal
                                                        GradientStop {
                                                            position: 0
                                                            color: backend.accentPrimary
                                                        }
                                                        GradientStop {
                                                            position: 1
                                                            color: backend.accentSecondary
                                                        }
                                                    }

                                                    Behavior on width {
                                                        NumberAnimation { duration: 280 }
                                                    }
                                                }
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true

                                                Text {
                                                    text: backend.formattedPosition
                                                    color: "#75747C"
                                                    font.pixelSize: 11
                                                }
                                                Item { Layout.fillWidth: true }
                                                Text {
                                                    text: backend.sourceName || "Строгий режим"
                                                    color: "#75747C"
                                                    font.pixelSize: 11
                                                }
                                                Item { Layout.fillWidth: true }
                                                Text {
                                                    text: backend.formattedDuration
                                                    color: "#75747C"
                                                    font.pixelSize: 11
                                                }
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 54
                                                radius: 15
                                                color: "#191A1F"
                                                border.width: 1
                                                border.color: "#2D2E35"

                                                Text {
                                                    anchors {
                                                        fill: parent
                                                        margins: 14
                                                    }
                                                    text: backend.bioPreview
                                                        || "Предпросмотр Telegram Bio"
                                                    color: backend.bioPreview
                                                        ? "#CAC7CE"
                                                        : "#68676F"
                                                    font.pixelSize: 12
                                                    verticalAlignment: Text.AlignVCenter
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }
                                    }
                                }

                                ColumnLayout {
                                    Layout.preferredWidth: 310
                                    Layout.fillHeight: true
                                    spacing: 16

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 290

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 20
                                            }
                                            spacing: 12

                                            Text {
                                                text: "ПОДКЛЮЧЕНИЯ"
                                                color: "#8A8DA2"
                                                font.pixelSize: 10
                                                font.weight: Font.Bold
                                                font.letterSpacing: 1.5
                                            }

                                            Repeater {
                                                model: [
                                                    {
                                                        "name": "Telegram",
                                                        "ok": backend.telegramConnected,
                                                        "hint": backend.telegramConnected
                                                            ? "Профиль подключён"
                                                            : "Ожидает запуска"
                                                    },
                                                    {
                                                        "name": "Воспроизведение",
                                                        "ok": backend.yandexConnected,
                                                        "hint": backend.yandexConnected
                                                            ? "Трек Яндекс Музыки найден"
                                                            : "Активный трек не найден"
                                                    },
                                                    {
                                                        "name": "Браузерный мост",
                                                        "ok": backend.browserConnected,
                                                        "hint": root.usesBrowserBridge()
                                                            ? backend.browserStatus
                                                            : "Не выбран в настройках"
                                                    },
                                                    {
                                                        "name": "Тексты песен",
                                                        "ok": backend.lyricsConnected,
                                                        "hint": backend.lyricsConnected
                                                            ? "Синхронизация доступна"
                                                            : "Ожидает первого трека"
                                                    },
                                                    {
                                                        "name": "MTProxy",
                                                        "ok": backend.proxyConnected,
                                                        "hint": backend.settings.proxy_enabled
                                                            ? (backend.proxyConnected
                                                                ? "Соединение доступно"
                                                                : "Будет проверен при запуске")
                                                            : "Не используется"
                                                    }
                                                ]

                                                RowLayout {
                                                    required property var modelData
                                                    Layout.fillWidth: true
                                                    spacing: 11

                                                    Rectangle {
                                                        Layout.preferredWidth: 10
                                                        Layout.preferredHeight: 10
                                                        radius: 5
                                                        color: modelData.ok ? "#59BE9C" : "#55565E"
                                                    }

                                                    Column {
                                                        Layout.fillWidth: true
                                                        spacing: 2
                                                        Text {
                                                            text: modelData.name
                                                            color: "#DCD9E0"
                                                            font.pixelSize: 13
                                                            font.weight: Font.Medium
                                                        }
                                                        Text {
                                                            text: modelData.hint
                                                            color: "#77767E"
                                                            font.pixelSize: 10
                                                        }
                                                    }
                                                }
                                            }

                                            Item { Layout.fillHeight: true }
                                        }
                                    }

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.fillHeight: true

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 20
                                            }
                                            spacing: 9

                                            Text {
                                                text: "ПОСЛЕДНИЕ СОБЫТИЯ"
                                                color: "#8A8DA2"
                                                font.pixelSize: 10
                                                font.weight: Font.Bold
                                                font.letterSpacing: 1.5
                                            }

                                            ListView {
                                                Layout.fillWidth: true
                                                Layout.fillHeight: true
                                                model: backend.activity
                                                clip: true
                                                spacing: 7

                                                delegate: Text {
                                                    required property string modelData
                                                    required property int index
                                                    width: ListView.view.width
                                                    text: modelData
                                                    color: index === 0 ? "#D8D9E5" : "#73768C"
                                                    font.pixelSize: 11
                                                    wrapMode: Text.WordWrap
                                                    maximumLineCount: 2
                                                    elide: Text.ElideRight
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        id: connectionsPage

                        ColumnLayout {
                            anchors {
                                fill: parent
                                margins: 12
                            }
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true

                                Column {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text {
                                        text: "Подключения"
                                        color: "#F6F6FB"
                                        font.pixelSize: 27
                                        font.weight: Font.DemiBold
                                    }
                                    Text {
                                        text: "Секреты хранятся в диспетчере учётных данных Windows."
                                        color: "#85889E"
                                        font.pixelSize: 13
                                    }
                                }

                                GlowButton {
                                    text: "Сохранить"
                                    onClicked: root.saveConnections()
                                }
                            }

                            Flickable {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                contentHeight: connectionGrid.implicitHeight + 8
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: SoftScrollBar {}

                                GridLayout {
                                    id: connectionGrid
                                    width: Math.min(connectionsPage.width - 54, 860)
                                    x: Math.max(0, (connectionsPage.width - width) / 2 - 12)
                                    columns: 1
                                    columnSpacing: 0
                                    rowSpacing: 12

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 324

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 12

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text {
                                                    text: "Telegram"
                                                    color: "#F3F3F8"
                                                    font.pixelSize: 18
                                                    font.weight: Font.DemiBold
                                                }
                                                Item { Layout.fillWidth: true }
                                                Rectangle {
                                                    Layout.preferredWidth: 9
                                                    Layout.preferredHeight: 9
                                                    radius: 5
                                                    color: backend.telegramConnected
                                                        ? "#42DCAA" : "#4B4E62"
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "API ID и Hash берутся на my.telegram.org. Номер нужен только для первого входа."
                                                color: "#777A91"
                                                font.pixelSize: 11
                                                wrapMode: Text.WordWrap
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 12
                                                ConnectionField {
                                                    id: apiIdField
                                                    Layout.fillWidth: true
                                                    title: "API ID"
                                                    placeholderText: "1234567"
                                                    validator: IntValidator { bottom: 1 }
                                                }
                                                ConnectionField {
                                                    id: phoneField
                                                    Layout.fillWidth: true
                                                    title: "Телефон"
                                                    placeholderText: "+7..."
                                                }
                                            }

                                            ConnectionField {
                                                id: apiHashField
                                                Layout.fillWidth: true
                                                title: "API Hash"
                                                placeholderText: "Скрытый ключ приложения"
                                                echoMode: TextInput.Password
                                            }

                                            Text {
                                                text: "Вход откроется внутри Music Bio после нажатия «Запустить»."
                                                color: "#686B81"
                                                font.pixelSize: 10
                                            }
                                        }
                                    }

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 324

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 12

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text {
                                                    text: "Яндекс Музыка"
                                                    color: "#F3F3F8"
                                                    font.pixelSize: 18
                                                    font.weight: Font.DemiBold
                                                }
                                                Item { Layout.fillWidth: true }
                                                Rectangle {
                                                    Layout.preferredWidth: 9
                                                    Layout.preferredHeight: 9
                                                    radius: 5
                                                    color: backend.lyricsConnected
                                                        ? "#42DCAA" : "#4B4E62"
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "Токен используется только для поиска синхронизированных текстов."
                                                color: "#777A91"
                                                font.pixelSize: 11
                                                wrapMode: Text.WordWrap
                                            }

                                            ConnectionField {
                                                id: yandexTokenField
                                                Layout.fillWidth: true
                                                title: "OAuth-токен"
                                                placeholderText: "y0_..."
                                                echoMode: TextInput.Password
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                GlowButton {
                                                    Layout.fillWidth: true
                                                    text: "Получить токен"
                                                    subtle: true
                                                    onClicked: backend.requestYandexToken()
                                                }
                                                GlowButton {
                                                    Layout.fillWidth: true
                                                    text: "Проверить"
                                                    subtle: true
                                                    onClicked: {
                                                        root.saveConnections()
                                                        backend.testYandex()
                                                    }
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "Без токена приложение продолжит показывать исполнителя и название трека."
                                                color: "#686B81"
                                                font.pixelSize: 10
                                                wrapMode: Text.WordWrap
                                            }
                                        }
                                    }

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 414

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 12

                                            Text {
                                                text: "Источник музыки"
                                                color: "#F3F3F8"
                                                font.pixelSize: 18
                                                font.weight: Font.DemiBold
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "Чужие сайты и обычные вкладки браузера всегда игнорируются."
                                                color: "#777A91"
                                                font.pixelSize: 11
                                                wrapMode: Text.WordWrap
                                            }

                                            SoftComboBox {
                                                id: sourceCombo
                                                Layout.fillWidth: true
                                                implicitHeight: 44
                                                model: [
                                                    "Приложение Яндекс Музыки",
                                                    "Браузерное расширение",
                                                    "Автоматически"
                                                ]
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 48
                                                radius: 12
                                                color: "#191A1F"
                                                border.width: 1
                                                border.color: backend.browserConnected
                                                    ? "#365F55" : "#33343B"

                                                RowLayout {
                                                    anchors {
                                                        fill: parent
                                                        leftMargin: 13
                                                        rightMargin: 13
                                                    }
                                                    spacing: 10

                                                    Rectangle {
                                                        Layout.preferredWidth: 8
                                                        Layout.preferredHeight: 8
                                                        radius: 4
                                                        color: backend.browserConnected
                                                            ? "#59BE9C" : "#C59458"
                                                    }

                                                    Text {
                                                        Layout.fillWidth: true
                                                        text: backend.browserStatus
                                                        color: "#B8B5BD"
                                                        font.pixelSize: 11
                                                        wrapMode: Text.WordWrap
                                                    }
                                                }
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                ConnectionField {
                                                    id: bridgeTokenField
                                                    Layout.fillWidth: true
                                                    title: "Ключ моста"
                                                    echoMode: TextInput.Password
                                                }
                                                ColumnLayout {
                                                    Layout.preferredWidth: 116
                                                    spacing: 7
                                                    Label {
                                                        text: "Порт"
                                                        color: "#D9DAE7"
                                                        font.pixelSize: 13
                                                    }
                                                    SoftSpinBox {
                                                        id: bridgePort
                                                        Layout.fillWidth: true
                                                        from: 1024
                                                        to: 65535
                                                        value: 8765
                                                    }
                                                }
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                GlowButton {
                                                    Layout.fillWidth: true
                                                    text: "Копировать ключ"
                                                    subtle: true
                                                    onClicked: backend.copyText(bridgeTokenField.text)
                                                }
                                                GlowButton {
                                                    Layout.fillWidth: true
                                                    text: "Папка расширения"
                                                    subtle: true
                                                    onClicked: backend.openExtensionFolder()
                                                }
                                            }
                                        }
                                    }

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 354

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 12

                                            ToggleRow {
                                                id: proxyEnabled
                                                Layout.fillWidth: true
                                                title: "Telegram MTProxy"
                                                description: "Использовать прокси для подключения к Telegram."
                                            }

                                            ConnectionField {
                                                id: proxyLinkField
                                                Layout.fillWidth: true
                                                title: "Ссылка для быстрого заполнения"
                                                placeholderText: "tg://proxy?server=...&port=...&secret=..."
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                spacing: 12
                                                ConnectionField {
                                                    id: proxyHostField
                                                    Layout.fillWidth: true
                                                    title: "Сервер"
                                                    placeholderText: "proxy.example.com"
                                                }
                                                ColumnLayout {
                                                    Layout.preferredWidth: 116
                                                    spacing: 7
                                                    Label {
                                                        text: "Порт"
                                                        color: "#D9DAE7"
                                                        font.pixelSize: 13
                                                    }
                                                    SoftSpinBox {
                                                        id: proxyPort
                                                        Layout.fillWidth: true
                                                        from: 1
                                                        to: 65535
                                                        value: 443
                                                    }
                                                }
                                            }

                                            ConnectionField {
                                                id: proxySecretField
                                                Layout.fillWidth: true
                                                title: "Secret"
                                                echoMode: TextInput.Password
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                GlowButton {
                                                    Layout.fillWidth: true
                                                    text: "Разобрать ссылку"
                                                    subtle: true
                                                    onClicked: {
                                                        let result = backend.parseProxyLink(
                                                            proxyLinkField.text
                                                        )
                                                        if (result.ok) {
                                                            proxyHostField.text = result.host
                                                            proxyPort.value = result.port
                                                            proxySecretField.text = result.secret
                                                            proxyEnabled.checked = true
                                                            toast.showMessage("MTProxy заполнен", false)
                                                        } else {
                                                            toast.showMessage(result.error, true)
                                                        }
                                                    }
                                                }
                                                GlowButton {
                                                    Layout.fillWidth: true
                                                    text: "Проверить"
                                                    subtle: true
                                                    onClicked: {
                                                        root.saveConnections()
                                                        backend.testProxy()
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }

                    Item {
                        id: appearancePage

                        ColumnLayout {
                            anchors {
                                fill: parent
                                margins: 12
                            }
                            spacing: 14

                            RowLayout {
                                Layout.fillWidth: true
                                Column {
                                    Layout.fillWidth: true
                                    spacing: 4
                                    Text {
                                        text: "Оформление и поведение"
                                        color: "#F6F6FB"
                                        font.pixelSize: 27
                                        font.weight: Font.DemiBold
                                    }
                                    Text {
                                        text: "Настрой Bio, динамику интерфейса и мини-оверлей."
                                        color: "#85889E"
                                        font.pixelSize: 13
                                    }
                                }
                                GlowButton {
                                    text: "Сохранить"
                                    onClicked: root.saveAppearance()
                                }
                            }

                            Flickable {
                                Layout.fillWidth: true
                                Layout.fillHeight: true
                                contentHeight: appearanceGrid.implicitHeight + 8
                                clip: true
                                boundsBehavior: Flickable.StopAtBounds
                                ScrollBar.vertical: SoftScrollBar {}

                                GridLayout {
                                    id: appearanceGrid
                                    width: Math.min(appearancePage.width - 54, 860)
                                    x: Math.max(0, (appearancePage.width - width) / 2 - 12)
                                    columns: 1
                                    columnSpacing: 0
                                    rowSpacing: 12

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 350

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 14

                                            Text {
                                                text: "Telegram Bio"
                                                color: "#F3F3F8"
                                                font.pixelSize: 18
                                                font.weight: Font.DemiBold
                                            }

                                            ConnectionField {
                                                id: templateField
                                                Layout.fillWidth: true
                                                title: "Шаблон"
                                                helperText: "Доступны {artist}, {title} и {lyric}."
                                            }

                                            ToggleRow {
                                                id: lyricsEnabled
                                                Layout.fillWidth: true
                                                title: "Синхронизированные тексты"
                                                description: "Добавлять текущую строку песни, когда она доступна."
                                            }

                                            ToggleRow {
                                                id: restoreBio
                                                Layout.fillWidth: true
                                                title: "Восстанавливать исходное Bio"
                                                description: "Вернуть прежний текст после остановки приложения."
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    Label {
                                                        text: "Проверка трека, сек."
                                                        color: "#D9DAE7"
                                                        font.pixelSize: 12
                                                    }
                                                    SoftSpinBox {
                                                        id: checkInterval
                                                        Layout.fillWidth: true
                                                        from: 1
                                                        to: 30
                                                        value: 3
                                                    }
                                                }
                                                ColumnLayout {
                                                    Layout.fillWidth: true
                                                    Label {
                                                        text: "Обновление Bio, сек."
                                                        color: "#D9DAE7"
                                                        font.pixelSize: 12
                                                    }
                                                    SoftSpinBox {
                                                        id: minBioInterval
                                                        Layout.fillWidth: true
                                                        from: 5
                                                        to: 120
                                                        value: 12
                                                    }
                                                }
                                            }
                                        }
                                    }

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 350

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 13

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Text {
                                                    text: "Мини-оверлей"
                                                    color: "#F3F3F8"
                                                    font.pixelSize: 18
                                                    font.weight: Font.DemiBold
                                                }
                                                Item { Layout.fillWidth: true }
                                                GlowButton {
                                                    text: backend.overlayVisible
                                                        ? "Скрыть" : "Показать"
                                                    subtle: true
                                                    implicitWidth: 100
                                                    implicitHeight: 36
                                                    onClicked: backend.toggleOverlay()
                                                }
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "Перетаскивается за любую свободную область. Режим «Мини-плеер» показывает обложку и название."
                                                color: "#777A91"
                                                font.pixelSize: 11
                                                wrapMode: Text.WordWrap
                                            }

                                            SoftComboBox {
                                                id: overlayMode
                                                Layout.fillWidth: true
                                                model: ["Карточка", "Полоса", "Мини-плеер"]
                                            }

                                            RowLayout {
                                                Layout.fillWidth: true
                                                Label {
                                                    text: "Прозрачность"
                                                    color: "#D9DAE7"
                                                    font.pixelSize: 13
                                                }
                                                SoftSlider {
                                                    id: overlayOpacity
                                                    Layout.fillWidth: true
                                                    from: 45
                                                    to: 100
                                                    value: 94
                                                    stepSize: 1
                                                }
                                                Label {
                                                    text: Math.round(overlayOpacity.value) + "%"
                                                    color: "#9699AD"
                                                    font.pixelSize: 12
                                                }
                                            }

                                            ToggleRow {
                                                id: overlayTop
                                                Layout.fillWidth: true
                                                title: "Поверх окон"
                                            }
                                            ToggleRow {
                                                id: overlayClick
                                                Layout.fillWidth: true
                                                title: "Пропускать клики"
                                                description: "При включении перетаскивание недоступно. Отключить можно здесь."
                                            }
                                        }
                                    }

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 270

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 14

                                            Text {
                                                text: "Интерфейс"
                                                color: "#F3F3F8"
                                                font.pixelSize: 18
                                                font.weight: Font.DemiBold
                                            }

                                            Text {
                                                text: "Интенсивность живых эффектов"
                                                color: "#D9DAE7"
                                                font.pixelSize: 13
                                            }

                                            SoftComboBox {
                                                id: animationLevel
                                                Layout.fillWidth: true
                                                model: [
                                                    "Спокойный",
                                                    "Сбалансированный",
                                                    "Живой"
                                                ]
                                            }

                                            ToggleRow {
                                                id: startMinimized
                                                Layout.fillWidth: true
                                                title: "Запускать свёрнутым"
                                                description: "Главное окно останется в системном трее."
                                            }
                                        }
                                    }

                                    GlassPanel {
                                        Layout.fillWidth: true
                                        Layout.preferredHeight: 270

                                        ColumnLayout {
                                            anchors {
                                                fill: parent
                                                margins: 22
                                            }
                                            spacing: 12

                                            Text {
                                                text: "Строгий режим"
                                                color: "#F3F3F8"
                                                font.pixelSize: 18
                                                font.weight: Font.DemiBold
                                            }

                                            Text {
                                                Layout.fillWidth: true
                                                text: "Music Bio никогда не определяет Яндекс Музыку по заголовку вкладки. Официальное приложение проверяется по App ID, а браузерная версия — по адресу страницы и секретному ключу локального моста."
                                                color: "#9A9DAE"
                                                font.pixelSize: 12
                                                lineHeight: 1.35
                                                wrapMode: Text.WordWrap
                                            }

                                            Rectangle {
                                                Layout.fillWidth: true
                                                Layout.preferredHeight: 54
                                                radius: 14
                                                color: "#182722"
                                                border.width: 1
                                                border.color: "#365F55"

                                                Row {
                                                    anchors.centerIn: parent
                                                    spacing: 10
                                                    Text {
                                                        text: "✓"
                                                        color: "#68C4A6"
                                                        font.pixelSize: 16
                                                        font.weight: Font.Bold
                                                    }
                                                    Text {
                                                        text: "Чужие сайты не попадут в Telegram Bio"
                                                        color: "#B0D8CB"
                                                        font.pixelSize: 12
                                                        font.weight: Font.Medium
                                                    }
                                                }
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    Dialog {
        id: authDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        width: 410
        padding: 24

        property string authKind: "code"
        property string message: ""

        background: Rectangle {
            radius: 20
            color: "#17181D"
            border.width: 1
            border.color: "#393A42"
        }

        contentItem: ColumnLayout {
            spacing: 14
            Text {
                Layout.fillWidth: true
                text: authDialog.title
                color: "#F5F5FA"
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }
            Text {
                Layout.fillWidth: true
                text: authDialog.message
                color: "#9295AA"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
            TextField {
                id: authValue
                Layout.fillWidth: true
                implicitHeight: 46
                color: "#E3E0E6"
                echoMode: authDialog.authKind === "password"
                    ? TextInput.Password : TextInput.Normal
                placeholderText: authDialog.authKind === "password"
                    ? "Пароль" : "Код из Telegram"
                background: Rectangle {
                    radius: 12
                    color: "#1B1C21"
                    border.width: 1
                    border.color: authValue.activeFocus
                        ? backend.accentSecondary : "#34353C"
                }
                onAccepted: {
                    backend.submitAuth(authDialog.authKind, text)
                    authDialog.close()
                }
            }
            RowLayout {
                Layout.fillWidth: true
                GlowButton {
                    Layout.fillWidth: true
                    text: "Отмена"
                    subtle: true
                    onClicked: {
                        backend.stopEngine()
                        authDialog.close()
                    }
                }
                GlowButton {
                    Layout.fillWidth: true
                    text: "Продолжить"
                    onClicked: {
                        backend.submitAuth(authDialog.authKind, authValue.text)
                        authDialog.close()
                    }
                }
            }
        }
    }

    Dialog {
        id: deviceDialog
        parent: Overlay.overlay
        anchors.centerIn: parent
        modal: true
        width: 440
        padding: 24

        property string deviceUrl: ""
        property string deviceCode: ""

        background: Rectangle {
            radius: 20
            color: "#17181D"
            border.width: 1
            border.color: "#393A42"
        }

        contentItem: ColumnLayout {
            spacing: 14
            Text {
                text: "Подключение Яндекс Музыки"
                color: "#F5F5FA"
                font.pixelSize: 20
                font.weight: Font.DemiBold
            }
            Text {
                Layout.fillWidth: true
                text: "Браузер уже открыл страницу. Введи этот код и подтверди доступ:"
                color: "#9295AA"
                font.pixelSize: 12
                wrapMode: Text.WordWrap
            }
            Rectangle {
                Layout.fillWidth: true
                Layout.preferredHeight: 72
                radius: 16
                color: "#1B1C21"
                border.width: 1
                border.color: "#34353C"
                Text {
                    anchors.centerIn: parent
                    text: deviceDialog.deviceCode
                    color: backend.accentSecondary
                    font.pixelSize: 26
                    font.weight: Font.Bold
                    font.letterSpacing: 4
                }
            }
            RowLayout {
                Layout.fillWidth: true
                GlowButton {
                    Layout.fillWidth: true
                    text: "Копировать код"
                    subtle: true
                    onClicked: backend.copyText(deviceDialog.deviceCode)
                }
                GlowButton {
                    Layout.fillWidth: true
                    text: "Готово"
                    onClicked: deviceDialog.close()
                }
            }
        }
    }

    Rectangle {
        id: toast
        z: 100
        anchors {
            horizontalCenter: parent.horizontalCenter
            bottom: parent.bottom
            bottomMargin: visible ? 28 : -height
        }
        width: Math.min(520, toastText.implicitWidth + 56)
        height: 48
        radius: 15
        color: propertyIsError ? "#9B304A" : "#253A37"
        border.width: 1
        border.color: propertyIsError ? "#E3637E" : "#3B7B6C"
        opacity: visible ? 1 : 0
        visible: false

        property bool propertyIsError: false

        function showMessage(message, isError) {
            toastText.text = message
            propertyIsError = isError
            visible = true
            hideTimer.restart()
        }

        Text {
            id: toastText
            anchors.centerIn: parent
            color: "#FFFFFF"
            font.pixelSize: 12
            font.weight: Font.Medium
            elide: Text.ElideRight
        }

        Timer {
            id: hideTimer
            interval: 3400
            onTriggered: toast.visible = false
        }

        Behavior on anchors.bottomMargin {
            NumberAnimation { duration: 230; easing.type: Easing.OutCubic }
        }
        Behavior on opacity {
            NumberAnimation { duration: 180 }
        }
    }
}
