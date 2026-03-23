#include "Bridge.h"

#include <QJsonDocument>
#include <QJsonArray>

Bridge::Bridge(QObject *parent) : QObject(parent) {}

bool Bridge::openProject(const QString &rootPath) {
    currentRoot_ = rootPath;
    layout_ = scanner_.scan(rootPath);
    if (!layout_.recognized) {
        emit toast(QStringLiteral("Project detection failed. ") + layout_.warnings.join("; "));
        return false;
    }
    moduleSpecs_ = specExtractor_.load(layout_.specsRoot);
    contractSchemas_ = schemaLoader_.load(layout_.specsRoot);
    metaGraph_ = metaStore_.load(rootPath);
    runState_ = runLoader_.load(layout_.runsRoot);
    const bool ok = rebuild();
    if (!layout_.warnings.isEmpty()) {
        emit toast(layout_.warnings.join("; "));
    }
    return ok;
}

bool Bridge::rebuild() {
    graph_ = graphBuilder_.build(layout_, moduleSpecs_, contractSchemas_, metaGraph_, runState_);
    layoutEngine_.apply(graph_, metaGraph_);
    emit graphChanged(graph_.toJson());
    return !graph_.nodes.isEmpty();
}

QJsonObject Bridge::requestGraph() {
    if (graph_.nodes.isEmpty()) rebuild();
    return graph_.toJson();
}

QString Bridge::requestGraph(const QString &view, const QString &focus) {
    if (graph_.nodes.isEmpty()) rebuild();
    const QJsonObject obj = graphViewProjector_.project(graph_, metaGraph_, view, focus);
    QJsonDocument doc(obj);
    return QString::fromUtf8(doc.toJson(QJsonDocument::Compact));
}

void Bridge::requestGraph(const QString &view, const QString &focus, const QJSValue &callback) {
    const QString json = requestGraph(view, focus);
    if (callback.isCallable()) {
        QJSValue cb = callback;
        cb.call(QList<QJSValue>() << QJSValue(json));
    }
}

// Provide full meta (including ui/layout) for front-end layout engine
QJsonObject Bridge::requestMeta() {
    QJsonObject obj;
    obj["schema_version"] = metaGraph_.schemaVersion;

    QJsonArray phases;
    for (const auto &ph : metaGraph_.phases) {
        QJsonObject o;
        o["id"] = ph.id;
        o["label"] = ph.label;
        o["order"] = ph.order;
        phases.append(o);
    }
    obj["phases"] = phases;

    QJsonObject positions;
    for (auto it = metaGraph_.positions.begin(); it != metaGraph_.positions.end(); ++it) {
        QJsonObject p;
        p["x"] = it.value().x();
        p["y"] = it.value().y();
        positions[it.key()] = p;
    }
    obj["positions"] = positions;

    if (!metaGraph_.ui.isEmpty()) obj["ui"] = metaGraph_.ui;
    return obj;
}

QJsonObject Bridge::requestNodeDetail(const QString &nodeId) {
    QJsonObject detail;
    for (const auto &n : graph_.nodes) {
        if (n.id == nodeId) {
            detail = n.toJson();
            break;
        }
    }
    // Enrich with spec/contract content
    for (const auto &m : moduleSpecs_) {
        if (m.id == nodeId) {
            detail["inputs"] = QJsonArray::fromStringList(m.inputs);
            detail["outputs"] = QJsonArray::fromStringList(m.outputs);
            detail["verifies"] = QJsonArray::fromStringList(m.verifies);
            detail["trace_links"] = QJsonArray::fromStringList(m.traceLinks);
            break;
        }
    }
    for (const auto &c : contractSchemas_) {
        if (c.id == nodeId) {
            detail["schema_path"] = c.schemaPath;
            break;
        }
    }
    return detail;
}

bool Bridge::editEdge(const QJsonObject &op) {
    if (!metaStore_.applyEdgeOp(metaGraph_, op)) return false;
    metaStore_.save(currentRoot_, metaGraph_);
    return rebuild();
}
