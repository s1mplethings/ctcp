// Lightweight graph models matching specs/contract_output/graph.schema.json
#pragma once

#include <QJsonArray>
#include <QJsonObject>
#include <QString>
#include <QStringList>
#include <QDateTime>
#include <QList>
#include <QPointF>
#include <cmath>
#include <limits>

struct GraphNode {
    QString id;
    QString type;   // Doc, Module, Contract, Gate, Run, Phase
    QString label;
    QString phase;
    QString path;
    QStringList statusFlags;
    QJsonObject meta;
    QString parent;      // phase compound node
    QString view;        // optional view name
    QString group;       // optional group/kind hint
    QString kind;
    QPointF position{std::numeric_limits<double>::quiet_NaN(), std::numeric_limits<double>::quiet_NaN()};
    QString tier;
    bool mutableFlag{false};
    bool pinned{false};
    bool collapsed{false};
    int childrenCount{0};
    QString category;

    QJsonObject toJson() const {
        QJsonObject obj;
        obj["id"] = id;
        obj["type"] = type;
        obj["label"] = label;
        if (!phase.isEmpty()) obj["phase"] = phase;
        if (!path.isEmpty()) obj["path"] = path;
        if (!statusFlags.isEmpty()) {
            QJsonArray arr;
            for (const auto &f : statusFlags) arr.append(f);
            obj["statusFlags"] = arr;
        }
        if (!meta.isEmpty()) obj["meta"] = meta;
        if (!parent.isEmpty()) obj["parent"] = parent;
        if (!view.isEmpty()) obj["view"] = view;
        if (!group.isEmpty()) obj["group"] = group;
        if (!kind.isEmpty()) obj["kind"] = kind;
        if (!std::isnan(position.x()) && !std::isnan(position.y())) {
            QJsonObject p;
            p["x"] = position.x();
            p["y"] = position.y();
            obj["position"] = p;
        }
        if (!tier.isEmpty()) obj["tier"] = tier;
        if (mutableFlag) obj["mutable"] = true;
        if (pinned) obj["pinned"] = true;
        if (collapsed) obj["collapsed"] = true;
        if (childrenCount > 0) obj["childrenCount"] = childrenCount;
        if (!category.isEmpty()) obj["category"] = category;
        return obj;
    }
};

struct GraphEdge {
    QString id;
    QString source;
    QString target;
    QString type;   // docs_link, produces, consumes, verifies, phase_contains, run_touches
    QString label;
    QString confidence; // manual, auto, low
    QJsonObject meta;
    QString view;
    bool aggregate{false};
    int weight{0};

    QJsonObject toJson() const {
        QJsonObject obj;
        obj["id"] = id;
        obj["source"] = source;
        obj["target"] = target;
        obj["type"] = type;
        if (!label.isEmpty()) obj["label"] = label;
        if (!confidence.isEmpty()) obj["confidence"] = confidence;
        if (!meta.isEmpty()) obj["meta"] = meta;
        if (!view.isEmpty()) obj["view"] = view;
        if (aggregate) obj["aggregate"] = true;
        if (weight != 0) obj["weight"] = weight;
        return obj;
    }
};

struct Graph {
    QString schemaVersion{"1.0.0"};
    QString generatedAt{QDateTime::currentDateTimeUtc().toString(Qt::ISODate)};
    QList<GraphNode> nodes;
    QList<GraphEdge> edges;

    QJsonObject toJson() const {
        QJsonObject obj;
        obj["schema_version"] = schemaVersion;
        obj["generated_at"] = generatedAt;
        QJsonArray nodeArr;
        for (const auto &n : nodes) nodeArr.append(n.toJson());
        obj["nodes"] = nodeArr;
        QJsonArray edgeArr;
        for (const auto &e : edges) edgeArr.append(e.toJson());
        obj["edges"] = edgeArr;
        return obj;
    }
};
