// Reads and writes meta/pipeline_graph.json (authority for manual edges)
#pragma once

#include <QHash>
#include <QJsonObject>
#include <QList>
#include <QPointF>
#include <QString>

struct MetaPhase {
    QString id;
    QString label;
    int order{0};
};

struct MetaModule {
    QString id;
    QString label;
    QString path;
    QString phase;
    QString tier;
    bool mutableFlag{false};
    bool pinned{false};
    QString category;
};

struct MetaContract {
    QString id;
    QString label;
    QString schemaPath;
    QString tier;
    bool mutableFlag{false};
    bool pinned{false};
    QString category;
};

struct MetaEdge {
    QString id;
    QString source;
    QString target;
    QString type; // produces/consumes/verifies
    QString label;
};

struct MetaGraph {
    QString schemaVersion{"1.0.0"};
    QList<MetaPhase> phases;
    QList<MetaModule> modules;
    QList<MetaContract> contracts;
    QList<MetaEdge> edges;
    QHash<QString, QPointF> positions;
    QJsonObject ui; // ui layout config passthrough
};

class MetaStore {
public:
    MetaGraph load(const QString &projectRoot);
    bool save(const QString &projectRoot, const MetaGraph &graph) const;

    // Apply edit op: {action: add|remove|update, source, target, type, label, id?}
    bool applyEdgeOp(MetaGraph &graph, const QJsonObject &op) const;

private:
    QString metaPathFor(const QString &projectRoot) const;
};
