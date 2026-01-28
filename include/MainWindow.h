// Main window: Qt Widgets shell around QWebEngine + QWebChannel bridge.
#pragma once

#include <QMainWindow>
#include <memory>

class SddaiBridge;

class Bridge;
class QFileSystemModel;
class QTreeView;
class QWebEngineView;
class QLabel;

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

private slots:
    void chooseProject();
    void handleToast(const QString &msg);

private:
    void createUi();
    void createMenu();
    void openProject(const QString &path);

    Bridge *bridge_{nullptr};           // core backend
    SddaiBridge *exposedBridge_{nullptr}; // wrapper exposed to WebChannel
    QFileSystemModel *fsModel_{nullptr};
    QTreeView *tree_{nullptr};
    QWebEngineView *webView_{nullptr};
    QLabel *projectLabel_{nullptr};
};
