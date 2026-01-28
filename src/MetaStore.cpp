#include "MetaStore.h"

#include <QDir>
#include <QFile>
#include <QFileInfo>
#include <QJsonArray>
#include <QJsonDocument>
#include <QJsonObject>
#include <algorithm>

namespace {
MetaGraph defaultMeta() {
    MetaGraph mg;
    const QStringList defaultPhases = {
        "Ingest", "Preprocess", "Transcribe", "Slice", "Render", "Export"
    };
    int order = 10;
    for (const auto &p : defaultPhases) {
        MetaPhase ph;
        ph.id = p;
        ph.label = p;
        ph.order = order;
        order += 10;
        mg.phases << ph;
    }
    return mg;
}

template <typename T, typename F>
T parseArray(const QJsonArray &arr, F parser) {
    T out;
    for (const auto &v : arr) {
        out << parser(v.toObject());
    }
    return out;
}
} // namespace

QString MetaStore::metaPathFor(const QString &projectRoot) const {
    QDir root(projectRoot);
    return root.filePath(QStringLiteral("meta/pipeline_graph.json"));
}

MetaGraph MetaStore::load(const QString &projectRoot) {
    QFile f(metaPathFor(projectRoot));
    if (!f.exists()) {
        return defaultMeta();
    }
    if (!f.open(QIODevice::ReadOnly)) {
        return defaultMeta();
    }
    const auto doc = QJsonDocument::fromJson(f.readAll());
    if (!doc.isObject()) {
        return defaultMeta();
    }
    const auto obj = doc.object();
    MetaGraph mg;
    mg.schemaVersion = obj.value(QStringLiteral("schema_version")).toString(QStringLiteral("1.0.0"));
    mg.phases = parseArray<QList<MetaPhase>>(obj.value(QStringLiteral("phases")).toArray(), [](const QJsonObject &o) {
        MetaPhase ph;
        ph.id = o.value("id").toString();
        ph.label = o.value("label").toString(ph.id);
        ph.order = o.value("order").toInt();
        return ph;
    });
    mg.modules = parseArray<QList<MetaModule>>(obj.value(QStringLiteral("modules")).toArray(), [](const QJsonObject &o) {
        MetaModule m;
        m.id = o.value("id").toString();
        m.label = o.value("label").toString(m.id);
        m.path = o.value("path").toString();
        m.phase = o.value("phase").toString();
        m.tier = o.value("tier").toString();
        m.mutableFlag = o.value("mutable").toBool();
        m.pinned = o.value("pinned").toBool();
        m.category = o.value("category").toString();
        return m;
    });
    mg.contracts = parseArray<QList<MetaContract>>(obj.value(QStringLiteral("contracts")).toArray(), [](const QJsonObject &o) {
        MetaContract c;
        c.id = o.value("id").toString();
        c.label = o.value("label").toString(c.id);
        c.schemaPath = o.value("schema_path").toString();
        c.tier = o.value("tier").toString();
        c.mutableFlag = o.value("mutable").toBool();
        c.pinned = o.value("pinned").toBool();
        c.category = o.value("category").toString();
        return c;
    });
    mg.edges = parseArray<QList<MetaEdge>>(obj.value(QStringLiteral("edges")).toArray(), [](const QJsonObject &o) {
        MetaEdge e;
        e.id = o.value("id").toString();
        e.source = o.value("source").toString();
        e.target = o.value("target").toString();
        e.type = o.value("type").toString();
        e.label = o.value("label").toString();
        return e;
    });
    const auto posObj = obj.value(QStringLiteral("positions")).toObject();
    for (auto it = posObj.begin(); it != posObj.end(); ++it) {
        const auto p = it.value().toObject();
        mg.positions.insert(it.key(), QPointF(p.value("x").toDouble(), p.value("y").toDouble()));
    }
    mg.ui = obj.value(QStringLiteral("ui")).toObject();
    return mg;
}

bool MetaStore::save(const QString &projectRoot, const MetaGraph &graph) const {
    QJsonObject obj;
    obj["schema_version"] = graph.schemaVersion;

    QJsonArray phases;
    for (const auto &ph : graph.phases) {
        QJsonObject o;
        o["id"] = ph.id;
        o["label"] = ph.label;
        o["order"] = ph.order;
        phases.append(o);
    }
    obj["phases"] = phases;

    QJsonArray modules;
    for (const auto &m : graph.modules) {
        QJsonObject o;
        o["id"] = m.id;
        o["label"] = m.label;
        o["path"] = m.path;
        if (!m.phase.isEmpty()) o["phase"] = m.phase;
        if (!m.tier.isEmpty()) o["tier"] = m.tier;
        if (m.mutableFlag) o["mutable"] = true;
        if (m.pinned) o["pinned"] = true;
        if (!m.category.isEmpty()) o["category"] = m.category;
        modules.append(o);
    }
    obj["modules"] = modules;

    QJsonArray contracts;
    for (const auto &c : graph.contracts) {
        QJsonObject o;
        o["id"] = c.id;
        o["label"] = c.label;
        o["schema_path"] = c.schemaPath;
        if (!c.tier.isEmpty()) o["tier"] = c.tier;
        if (c.mutableFlag) o["mutable"] = true;
        if (c.pinned) o["pinned"] = true;
        if (!c.category.isEmpty()) o["category"] = c.category;
        contracts.append(o);
    }
    obj["contracts"] = contracts;

    QJsonArray edges;
    for (const auto &e : graph.edges) {
        QJsonObject o;
        if (!e.id.isEmpty()) o["id"] = e.id;
        o["source"] = e.source;
        o["target"] = e.target;
        o["type"] = e.type;
        if (!e.label.isEmpty()) o["label"] = e.label;
        edges.append(o);
    }
    obj["edges"] = edges;

    QJsonObject positions;
    for (auto it = graph.positions.begin(); it != graph.positions.end(); ++it) {
        QJsonObject p;
        p["x"] = it.value().x();
        p["y"] = it.value().y();
        positions[it.key()] = p;
    }
    obj["positions"] = positions;

    if (!graph.ui.isEmpty()) obj["ui"] = graph.ui;

    const QString path = metaPathFor(projectRoot);
    QDir().mkpath(QFileInfo(path).absolutePath());
    QFile f(path + ".tmp");
    if (!f.open(QIODevice::WriteOnly | QIODevice::Truncate)) return false;
    f.write(QJsonDocument(obj).toJson(QJsonDocument::Indented));
    f.close();
    QFile::remove(path);
    return QFile::rename(f.fileName(), path);
}

bool MetaStore::applyEdgeOp(MetaGraph &graph, const QJsonObject &op) const {
    const QString action = op.value(QStringLiteral("action")).toString();
    const QString source = op.value(QStringLiteral("source")).toString();
    const QString target = op.value(QStringLiteral("target")).toString();
    const QString type = op.value(QStringLiteral("type")).toString();
    const QString label = op.value(QStringLiteral("label")).toString();
    QString id = op.value(QStringLiteral("id")).toString();

    if (action.isEmpty() || source.isEmpty() || target.isEmpty() || type.isEmpty()) {
        return false;
    }

    if (action == QStringLiteral("add")) {
        MetaEdge e;
        e.id = id.isEmpty() ? QString("%1-%2-%3").arg(source, type, target) : id;
        e.source = source;
        e.target = target;
        e.type = type;
        e.label = label;
        graph.edges.append(e);
        return true;
    }

    if (action == QStringLiteral("remove")) {
        const QString matchId = !id.isEmpty() ? id : QString("%1-%2-%3").arg(source, type, target);
        auto it = std::remove_if(graph.edges.begin(), graph.edges.end(), [&](const MetaEdge &e) {
            return e.id == matchId;
        });
        if (it != graph.edges.end()) {
            graph.edges.erase(it, graph.edges.end());
            return true;
        }
        return false;
    }

    if (action == QStringLiteral("update")) {
        const QString matchId = !id.isEmpty() ? id : QString("%1-%2-%3").arg(source, type, target);
        for (auto &e : graph.edges) {
            if (e.id == matchId) {
                if (!label.isEmpty()) e.label = label;
                e.source = source;
                e.target = target;
                e.type = type;
                return true;
            }
        }
    }
    return false;
}
