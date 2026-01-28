#include "Bridge.h"

#include "LayoutEngine.h"
#include "DocPreviewer.h"

#include <QJsonDocument>
#include <QJsonArray>
#include <QtMath>

#include <QDesktopServices>
#include <QJsonArray>
#include <QUrl>

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

    auto toJson = [&](const QList<GraphNode> &nodes, const QList<GraphEdge> &edges) {
        QJsonObject obj;
        obj.insert(QStringLiteral("schema_version"), graph_.schemaVersion);
        obj.insert(QStringLiteral("generated_at"), graph_.generatedAt);
        QJsonArray nArr;
        for (const auto &n : nodes) nArr.append(n.toJson());
        QJsonArray eArr;
        for (const auto &e : edges) eArr.append(e.toJson());
        obj.insert(QStringLiteral("nodes"), nArr);
        obj.insert(QStringLiteral("edges"), eArr);
        return obj;
    };

    auto buildSummary = [&]() {
        const auto summary = metaGraph_.ui.value(QStringLiteral("summary")).toObject();
        QStringList categories;
        for (const auto &v : summary.value(QStringLiteral("categories")).toArray()) categories << v.toString();
        if (categories.isEmpty()) categories = {"Docs","Modules","Contracts","Meta","Runs","Gates"};

        const auto grid = summary.value(QStringLiteral("grid")).toObject();
        const double gapX = grid.value(QStringLiteral("gap_x")).toDouble(520.0);
        const double gapY = grid.value(QStringLiteral("gap_y")).toDouble(320.0);
        const auto origin = grid.value(QStringLiteral("origin")).toObject();
        const double ox = origin.value(QStringLiteral("x")).toDouble(0.0);
        const double oy = origin.value(QStringLiteral("y")).toDouble(0.0);

        QList<GraphNode> nodes;
        QList<GraphEdge> edges; // keep empty or minimal

        // category nodes on 3-column grid
        for (int i = 0; i < categories.size(); ++i) {
            GraphNode n;
            n.id = QStringLiteral("category.%1").arg(categories[i]);
            n.type = QStringLiteral("Category");
            n.kind = QStringLiteral("Category");
            n.label = categories[i];
            n.view = QStringLiteral("Summary");
            n.tier = QStringLiteral("core");
            n.mutableFlag = true;
            n.pinned = true;
            n.category = categories[i];
            const int col = i % 3;
            const int row = i / 3;
            n.position = QPointF(ox + col * gapX, oy + row * gapY);
            nodes << n;
        }

        // pinned real nodes (<=12)
        QStringList pinnedList;
        for (const auto &v : summary.value(QStringLiteral("pinned")).toArray()) pinnedList << v.toString();
        if (pinnedList.isEmpty()) pinnedList << "module.graph_builder" << "module.project_scanner";

        QHash<QString, int> pinnedCountPerCat;
        const double radius = 110.0;
        for (const auto &n : graph_.nodes) {
            if (!n.pinned && !pinnedList.contains(n.id)) continue;
            GraphNode copy = n;
            copy.view = QStringLiteral("Summary");
            // place near its category
            QString cat = !n.category.isEmpty() ? n.category : QStringLiteral("Modules");
            const auto catId = QStringLiteral("category.%1").arg(cat);
            auto catNode = std::find_if(nodes.begin(), nodes.end(), [&](const GraphNode &cn){return cn.id == catId;});
            QPointF base = catNode != nodes.end() ? catNode->position : QPointF(ox, oy);
            int idx = pinnedCountPerCat.value(cat, 0);
            pinnedCountPerCat[cat] = idx + 1;
            double angle = (idx % 6) * (M_PI / 3.0);
            copy.position = QPointF(base.x() + radius * qCos(angle), base.y() + radius * qSin(angle));
            nodes << copy;
            if (nodes.size() >= 12) break;
        }

        return toJson(nodes, edges);
    };

    auto filterView = [&](const QString &v, const QString &focusId) {
        QList<GraphNode> nodes;

        auto addNode = [&](const GraphNode &n) {
            // label 精简：硬截断到 18 字符
            GraphNode copy = n;
            if (copy.label.size() > 18) copy.label = copy.label.left(18) + "…";
            nodes << copy;
        };

        for (const auto &n : graph_.nodes) {
            bool keep = n.view.isEmpty() || n.view.compare(v, Qt::CaseInsensitive) == 0;
            if (v == QStringLiteral("Pipeline") && (n.type == "Phase" || n.type == "Module" || n.type == "Contract" || n.type == "Gate" || n.type == "Run")) keep = true;
            if (v == QStringLiteral("Docs") && n.type == "Doc") keep = true;
            if (v == QStringLiteral("Contracts") && (n.type == "Contract" || n.category == "Contracts")) keep = true;
            if (keep && !focusId.isEmpty()) {
                if (!n.category.isEmpty() && !n.category.contains(focusId, Qt::CaseInsensitive)) keep = false;
            }
            if (keep) addNode(n);
        }

        // Edge裁剪
        QSet<QString> nodeIds;
        for (const auto &n : nodes) nodeIds.insert(n.id);

        QList<GraphEdge> edges;
        for (const auto &e : graph_.edges) {
            bool keep = (e.view.isEmpty() || e.view.compare(v, Qt::CaseInsensitive) == 0);
            if (!keep) continue;
            if (!nodeIds.contains(e.source) || !nodeIds.contains(e.target)) continue;

            if (v == QStringLiteral("Summary")) {
                if (!e.aggregate) continue; // Summary 只留 aggregate
                if (edges.size() >= 12) break;
            }
            if (v == QStringLiteral("Docs")) {
                if (e.type != QStringLiteral("docs_link")) continue;
            }
            edges << e;
            if (edges.size() >= 800 && v != QStringLiteral("Summary")) break; // 总边数上限
        }

        return toJson(nodes, edges);
    };

    QJsonObject obj;
    const QString v = view.isEmpty() ? metaGraph_.ui.value("default_view").toString("Pipeline") : view;
    // Performance: avoid building huge payloads
    if (v.compare(QStringLiteral("Summary"), Qt::CaseInsensitive) == 0) {
        obj = buildSummary();
    } else {
        obj = filterView(v, focus);
        // Cap nodes/edges for safety
        QJsonArray nodes = obj.value("nodes").toArray();
        QJsonArray edges = obj.value("edges").toArray();
        if (nodes.size() > 800) {
            QJsonArray trimmed;
            for (int i = 0; i < 800; ++i) trimmed.append(nodes.at(i));
            obj[QStringLiteral("nodes")] = trimmed;
        }
        if (edges.size() > 900) {
            QJsonArray trimmed;
            for (int i = 0; i < 900; ++i) trimmed.append(edges.at(i));
            obj[QStringLiteral("edges")] = trimmed;
        }
    }

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

bool Bridge::openFile(const QString &path) {
    return QDesktopServices::openUrl(QUrl::fromLocalFile(path));
}

QString Bridge::previewFile(const QString &path) {
    return docPreviewer_.readFile(path);
}

bool Bridge::openPath(const QString &path) {
    return openFile(path);
}

bool Bridge::openNode(const QString &nodeId) {
    for (const auto &n : graph_.nodes) {
        if (n.id == nodeId && !n.path.isEmpty()) {
            return openFile(n.path);
        }
    }
    return false;
}

void Bridge::readTextFile(const QString &path, const QJSValue &callback) {
    const QString text = docPreviewer_.readFile(path);
    if (callback.isCallable()) {
        QJSValue cb = callback;
        cb.call(QList<QJSValue>() << QJSValue(text));
    }
}
