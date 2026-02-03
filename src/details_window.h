#pragma once

#include <QMainWindow>

class QWebEngineView;
class SddaiBridge;

class DetailsWindow : public QMainWindow {
    Q_OBJECT
public:
    explicit DetailsWindow(SddaiBridge* bridge, QWidget* parent = nullptr);
    ~DetailsWindow() override = default;

    void reloadPage();

protected:
    void showEvent(QShowEvent* event) override;

private:
    void setupWeb(SddaiBridge* bridge);

    QWebEngineView* view_{nullptr};
};
