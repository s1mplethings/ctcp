#include "MainWindow.h"
#include "Bridge.h"

#include <QApplication>
#include <QFile>
#include <QTextStream>
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
#include <QtWebEngine/QtWebEngine>
#endif

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    QtWebEngine::initialize();
#endif
    QFile styleFile(QStringLiteral(":/qt_style.qss"));
    if (styleFile.open(QIODevice::ReadOnly | QIODevice::Text)) {
        app.setStyleSheet(QString::fromUtf8(styleFile.readAll()));
    }

    MainWindow w;
    w.show();
    return app.exec();
}
