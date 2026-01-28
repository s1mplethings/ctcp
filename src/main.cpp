#include "MainWindow.h"
#include "Bridge.h"
#include "sddai_bridge.h"

#include <QApplication>
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
#include <QtWebEngine/QtWebEngine>
#endif

int main(int argc, char *argv[]) {
    QApplication app(argc, argv);
#if QT_VERSION < QT_VERSION_CHECK(6, 0, 0)
    QtWebEngine::initialize();
#endif
    MainWindow w;
    w.show();
    return app.exec();
}
