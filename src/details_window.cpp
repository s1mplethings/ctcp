#include "details_window.h"

#include "sddai_bridge.h"

#include <QWebChannel>
#include <QWebEngineView>

DetailsWindow::DetailsWindow(SddaiBridge* bridge, QWidget* parent)
    : QMainWindow(parent) {
    setWindowTitle(tr("Details"));
    resize(480, 640);
    setupWeb(bridge);
}

void DetailsWindow::setupWeb(SddaiBridge* bridge) {
    view_ = new QWebEngineView(this);
    auto channel = new QWebChannel(view_);
    channel->registerObject(QStringLiteral("bridge"), bridge);
    view_->page()->setWebChannel(channel);
    view_->setUrl(QUrl(QStringLiteral("qrc:/web/graph_spider/details.html")));
    setCentralWidget(view_);
}

void DetailsWindow::reloadPage() {
    if (view_) view_->reload();
}

void DetailsWindow::showEvent(QShowEvent* event) {
    QMainWindow::showEvent(event);
    reloadPage(); // defensive refresh to avoid stale/blank when reopened
}
