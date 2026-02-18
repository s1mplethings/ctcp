#include "MainWindow.h"
#include "Bridge.h"
#include "sddai_bridge.h"

#include <QApplication>
#include <QCoreApplication>
#include <QFile>
#include <QTimer>
#include <QTextStream>
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
#include <QtWebEngine/QtWebEngine>
#endif
#include <cstdio>
#include <cstring>
#include <exception>

static bool hasSmokeFlag(int argc, char *argv[]) {
    for (int i = 1; i < argc; ++i) {
        if (std::strcmp(argv[i], "--smoke") == 0) {
            return true;
        }
    }
    return false;
}

static int runApp(int argc, char *argv[]) {
    const bool smoke = hasSmokeFlag(argc, argv);

    QApplication app(argc, argv);
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    QtWebEngine::initialize();
#endif
    QFile styleFile(QStringLiteral(":/qt_style.qss"));
    if (styleFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        app.setStyleSheet(QString::fromUtf8(styleFile.readAll()));
    }

    MainWindow w;
    if (smoke) {
        // Smoke mode: validate startup/init path and short event-loop stability.
        w.show();
        QTimer::singleShot(120, &app, &QCoreApplication::quit);
        return app.exec();
    }

    w.show();
    return app.exec();
}

int main(int argc, char *argv[]) {
    try {
        return runApp(argc, argv);
    } catch (const std::exception &ex) {
        std::fprintf(stderr, "[ctcp][fatal] %s\n", ex.what());
        return 2;
    } catch (...) {
        std::fprintf(stderr, "[ctcp][fatal] unknown exception\n");
        return 3;
    }
}

// simlab-s02
