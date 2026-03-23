#include "GraphViewProjector.h"

#include <QHash>
#include <QJsonArray>
#include <QSet>
#include <QtMath>

#include <algorithm>

namespace {
QJsonObject toJson(const Graph &graph, const QList<GraphNode> &nodes, const QList<GraphEdge> &edges) {
    QJsonObject obj;
    obj.insert(QStringLiteral("schema_version"), graph.schemaVersion);
    obj.insert(QStringLiteral("generated_at"), graph.generatedAt);
    QJsonArray nArr;
    for (const auto &n : nodes) nArr.append(n.toJson());
    QJsonArray eArr;
    for (const auto &e : edges) eArr.append(e.toJson());
    obj.insert(QStringLiteral("nodes"), nArr);
    obj.insert(QStringLiteral("edges"), eArr);
    return obj;
}

QJsonObject buildSummary(const Graph &graph, const MetaGraph &meta) {
    const auto summary = meta.ui.value(QStringLiteral("summary")).toObject();
    QStringList categories;
    for (const auto &v : summary.value(QStringLiteral("categories")).toArray()) categories << v.toString();
    if (categories.isEmpty()) categories = {"Docs", "Modules", "Contracts", "Meta", "Runs", "Gates"};

    const auto grid = summary.value(QStringLiteral("grid")).toObject();
    const double gapX = grid.value(QStringLiteral("gap_x")).toDouble(520.0);
    const double gapY = grid.value(QStringLiteral("gap_y")).toDouble(320.0);
    const auto origin = grid.value(QStringLiteral("origin")).toObject();
    const double ox = origin.value(QStringLiteral("x")).toDouble(0.0);
    const double oy = origin.value(QStringLiteral("y")).toDouble(0.0);

    QList<GraphNode> nodes;
    QList<GraphEdge> edges;

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

    QStringList pinnedList;
    for (const auto &v : summary.value(QStringLiteral("pinned")).toArray()) pinnedList << v.toString();
    if (pinnedList.isEmpty()) pinnedList << "module.graph_builder" << "module.project_scanner";

    QHash<QString, int> pinnedCountPerCat;
    const double radius = 110.0;
    for (const auto &n : graph.nodes) {
        if (!n.pinned && !pinnedList.contains(n.id)) continue;
        GraphNode copy = n;
        copy.view = QStringLiteral("Summary");
        QString cat = !n.category.isEmpty() ? n.category : QStringLiteral("Modules");
        const auto catId = QStringLiteral("category.%1").arg(cat);
        auto catNode = std::find_if(nodes.begin(), nodes.end(), [&](const GraphNode &cn) { return cn.id == catId; });
        QPointF base = catNode != nodes.end() ? catNode->position : QPointF(ox, oy);
        int idx = pinnedCountPerCat.value(cat, 0);
        pinnedCountPerCat[cat] = idx + 1;
        double angle = (idx % 6) * (M_PI / 3.0);
        copy.position = QPointF(base.x() + radius * qCos(angle), base.y() + radius * qSin(angle));
        nodes << copy;
        if (nodes.size() >= 12) break;
    }

    return toJson(graph, nodes, edges);
}

QJsonObject filterView(const Graph &graph, const QString &view, const QString &focusId) {
    QList<GraphNode> nodes;

    auto addNode = [&](const GraphNode &node) {
        GraphNode copy = node;
        if (copy.label.size() > 18) copy.label = copy.label.left(18) + "...";
        nodes << copy;
    };

    for (const auto &n : graph.nodes) {
        bool keep = n.view.isEmpty() || n.view.compare(view, Qt::CaseInsensitive) == 0;
        if (view == QStringLiteral("Pipeline") &&
            (n.type == "Phase" || n.type == "Module" || n.type == "Contract" || n.type == "Gate" || n.type == "Run")) {
            keep = true;
        }
        if (view == QStringLiteral("Docs") && n.type == "Doc") keep = true;
        if (view == QStringLiteral("Contracts") && (n.type == "Contract" || n.category == "Contracts")) keep = true;
        if (keep && !focusId.isEmpty()) {
            if (!n.category.isEmpty() && !n.category.contains(focusId, Qt::CaseInsensitive)) keep = false;
        }
        if (keep) addNode(n);
    }

    QSet<QString> nodeIds;
    for (const auto &n : nodes) nodeIds.insert(n.id);

    QList<GraphEdge> edges;
    for (const auto &e : graph.edges) {
        bool keep = e.view.isEmpty() || e.view.compare(view, Qt::CaseInsensitive) == 0;
        if (!keep) continue;
        if (!nodeIds.contains(e.source) || !nodeIds.contains(e.target)) continue;

        if (view == QStringLiteral("Summary")) {
            if (!e.aggregate) continue;
            if (edges.size() >= 12) break;
        }
        if (view == QStringLiteral("Docs")) {
            if (e.type != QStringLiteral("docs_link")) continue;
        }
        edges << e;
        if (edges.size() >= 800 && view != QStringLiteral("Summary")) break;
    }

    return toJson(graph, nodes, edges);
}
} // namespace

QJsonObject GraphViewProjector::project(const Graph &graph, const MetaGraph &meta, const QString &view, const QString &focus) const {
    const QString effectiveView = view.isEmpty() ? meta.ui.value(QStringLiteral("default_view")).toString(QStringLiteral("Pipeline")) : view;

    QJsonObject obj;
    if (effectiveView.compare(QStringLiteral("Summary"), Qt::CaseInsensitive) == 0) {
        obj = buildSummary(graph, meta);
    } else {
        obj = filterView(graph, effectiveView, focus);

        QJsonArray nodes = obj.value(QStringLiteral("nodes")).toArray();
        QJsonArray edges = obj.value(QStringLiteral("edges")).toArray();
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

    return obj;
}
