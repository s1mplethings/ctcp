#pragma once
#include <QDialog>
#include <QString>

class QTextBrowser;

class PreviewWindow : public QDialog {
  Q_OBJECT
public:
  explicit PreviewWindow(QWidget* parent = nullptr);
  void loadFile(const QString& absPath, const QString& content);

private:
  void renderContent(const QString& absPath, const QString& content);

  QTextBrowser* m_view = nullptr;
  QString m_lastPath;
};
