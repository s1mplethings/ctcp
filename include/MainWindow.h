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
class QDockWidget;
class DetailsWindow;

class MainWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

private slots:
    void chooseProject();
    void handleToast(const QString &msg);
    void openDetailsWindow();

private:
    void createUi();
    void createMenu();
    void openProject(const QString &path);

    Bridge *bridge_{nullptr};           // core backend
    SddaiBridge *exposedBridge_{nullptr}; // wrapper exposed to WebChannel
    QFileSystemModel *fsModel_{nullptr};
    QTreeView *tree_{nullptr};
    QWebEngineView *webView_{nullptr};
    QDockWidget *detailsDock_{nullptr};
    QWebEngineView *detailsView_{nullptr};
    DetailsWindow *detailsWindow_{nullptr};
    QLabel *projectLabel_{nullptr};
};
