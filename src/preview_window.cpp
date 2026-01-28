#include "preview_window.h"

#include <QAction>
#include <QApplication>
#include <QClipboard>
#include <QDesktopServices>
#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QTextBrowser>
#include <QTextDocument>
#include <QToolBar>
#include <QUrl>
#include <QVBoxLayout>

PreviewWindow::PreviewWindow(QWidget* parent) : QDialog(parent) {
  setWindowTitle("Preview");
  resize(980, 720);
  setAttribute(Qt::WA_DeleteOnClose, false);

  auto* layout = new QVBoxLayout(this);
  layout->setContentsMargins(8, 8, 8, 8);
  layout->setSpacing(6);

  auto* toolbar = new QToolBar(this);
  toolbar->setMovable(false);
  layout->addWidget(toolbar);

  m_view = new QTextBrowser(this);
  m_view->setOpenExternalLinks(true);
  m_view->setLineWrapMode(QTextBrowser::WidgetWidth);
  layout->addWidget(m_view, 1);

  QAction* copyAct = toolbar->addAction(QStringLiteral("Copy Path"));
  connect(copyAct, &QAction::triggered, this, [this]() {
    if (m_lastPath.isEmpty()) return;
    QApplication::clipboard()->setText(m_lastPath);
  });

  QAction* openExternal = toolbar->addAction(QStringLiteral("Open External"));
  connect(openExternal, &QAction::triggered, this, [this]() {
    if (m_lastPath.isEmpty()) return;
    QDesktopServices::openUrl(QUrl::fromLocalFile(m_lastPath));
  });

  QAction* reloadAct = toolbar->addAction(QStringLiteral("Reload"));
  connect(reloadAct, &QAction::triggered, this, [this]() {
    if (m_lastPath.isEmpty()) return;
    QFile f(m_lastPath);
    if (!f.open(QIODevice::ReadOnly | QIODevice::Text)) return;
    const QString text = QString::fromUtf8(f.readAll());
    renderContent(m_lastPath, text);
  });
}

void PreviewWindow::renderContent(const QString& absPath, const QString& content) {
  const QFileInfo info(absPath);
  const QString baseDir = info.absolutePath() + QDir::separator();
  m_view->document()->setBaseUrl(QUrl::fromLocalFile(baseDir));

#if (QT_VERSION >= QT_VERSION_CHECK(5, 14, 0))
  const QString ext = info.suffix().toLower();
  if (ext == "md" || ext == "markdown" || ext == "mdown") {
    m_view->setMarkdown(content);
    return;
  }
#endif

  QString html = content.toHtmlEscaped();
  html = QStringLiteral("<pre style=\"white-space: pre-wrap; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 12px; line-height: 1.45;\">%1</pre>")
             .arg(html);
  m_view->setHtml(html);
}

void PreviewWindow::loadFile(const QString& absPath, const QString& content) {
  m_lastPath = absPath;
  setWindowTitle(QStringLiteral("Preview - %1").arg(QFileInfo(absPath).fileName()));
  renderContent(absPath, content);
}
