// QWebChannel bridge exposing core APIs to the web front-end.
#pragma once

#include "GraphBuilder.h"
#include "GraphViewProjector.h"
#include "LayoutEngine.h"
#include "MetaStore.h"
#include "ProjectScanner.h"
#include "RunLoader.h"
#include "SchemaLoader.h"
#include "SpecExtractor.h"

#include <QObject>
#include <QJsonObject>
#include <QJSValue>

class Bridge : public QObject {
    Q_OBJECT
public:
    explicit Bridge(QObject *parent = nullptr);

    Q_INVOKABLE bool openProject(const QString &rootPath);
    // Default graph (legacy): returns JSON object
    Q_INVOKABLE QJsonObject requestGraph();
    // New signature for web v6: accepts view/focus and returns compact JSON string
    Q_INVOKABLE QString requestGraph(const QString &view, const QString &focus);
    // Async style for QtWebChannel callback: requestGraph(view, focus, cb(JSON string))
    Q_INVOKABLE void requestGraph(const QString &view, const QString &focus, const QJSValue &callback);
    Q_INVOKABLE QJsonObject requestMeta();
    Q_INVOKABLE QJsonObject requestNodeDetail(const QString &nodeId);
    Q_INVOKABLE bool editEdge(const QJsonObject &op);

signals:
    void graphChanged(const QJsonObject &graph);
    void runProgressChanged(const QJsonObject &progress);
    void toast(const QString &message);

private:
    bool rebuild();

    ProjectScanner scanner_;
    SpecExtractor specExtractor_;
    SchemaLoader schemaLoader_;
    MetaStore metaStore_;
    RunLoader runLoader_;
    GraphBuilder graphBuilder_;
    GraphViewProjector graphViewProjector_;
    LayoutEngine layoutEngine_;

    QString currentRoot_;
    ProjectLayout layout_;
    QList<ModuleSpec> moduleSpecs_;
    QList<ContractSchema> contractSchemas_;
    MetaGraph metaGraph_;
    RunState runState_;
    Graph graph_;
};
