// GraphViewProjector: project full graph into view/focus-specific payload.
#pragma once

#include "GraphTypes.h"
#include "MetaStore.h"

#include <QJsonObject>
#include <QString>

class GraphViewProjector {
public:
    QJsonObject project(const Graph &graph, const MetaGraph &meta, const QString &view, const QString &focus) const;
};
