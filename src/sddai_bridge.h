#pragma once
#include <QObject>
#include <QString>

class Bridge;        // core backend (graph builder etc.)
class PreviewWindow; // Qt preview dialog

// Adapter exposed to QWebChannel as "bridge".
// Delegates graph requests to existing Bridge, but adds safe file read + native preview window.
class SddaiBridge : public QObject {
  Q_OBJECT
public:
  explicit SddaiBridge(Bridge* core, QObject* parent = nullptr);

  void setProjectRoot(const QString& projectRoot);

  // Return file text (UTF-8). Absolute or relative paths must stay inside project root.
  Q_INVOKABLE QString readTextFile(const QString& relativePath) const;

  // Delegate to core bridge (JSON string, compact).
  Q_INVOKABLE QString requestGraph(const QString& view, const QString& focus) const;

  // Open native preview window for Markdown; fall back to OS default for other types.
  Q_INVOKABLE void openPath(const QString& relativePath);

  // Return simple graph JSON {nodes:[...], links:[...]} for force-canvas view.
  Q_INVOKABLE QString getGraphJson() const;
  Q_INVOKABLE void openNode(const QString& nodeJson);

  // selection/command sync with details dock
  Q_INVOKABLE void setSelectedNode(const QString& nodeId);
  Q_INVOKABLE void sendCommand(const QString& cmd, const QString& arg);
  Q_INVOKABLE QString requestNodeDetailJson(const QString& nodeId) const;

signals:
  void graphChanged(const QJsonObject& graph);
  void toast(const QString& message);
  void selectedNodeChanged(const QString& nodeId);
  void commandRequested(const QString& cmd, const QString& arg);

private:
  QString resolveSafePath(const QString& relativePath) const;

  Bridge* core_{nullptr};
  QString projectRoot_;
  mutable PreviewWindow* preview_{nullptr};
  QString selectedNodeId_;
};
